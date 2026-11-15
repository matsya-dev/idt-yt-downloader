from __future__ import annotations

import json
import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, __version__
from .engine import Engine
from .model import BVKS_PATH, CHANNELS, QUALITY_OPTIONS, Collection, Entry, Paused, TREE_HOME, UserError, audio_quality, format_size, tree_path, tree_url, youtube_url
from .selection import Selection
from .sources import DesireTree, YouTube
from .state import State, data_directory
from .tools import Tools, application_directory
from .updater import update_youtube
from .shortcuts import Shortcuts
from .theme import THEME_OPTIONS, apply_theme, system_is_dark, theme_choice

BG = "#ffffff"
SOFT = "#f7f7f5"
LINE = "#e2e5de"
TEXT = "#252925"
MUTED = "#60665f"
WARM = "#8e4b30"
SELECTED = "#f7ede5"
GLYPHS = {"checked": "☑", "unchecked": "☐", "partial": "▣", "loading": "◌"}


class HintEntry(ttk.Entry):
    def __init__(self, parent, hint="", **kw):
        super().__init__(parent, **kw)
        self.hint = hint
        self.placeholder = False
        self.bind("<FocusIn>", self._focus)
        self.bind("<FocusOut>", self._blur)
        self._blur()

    def _focus(self, event=None):
        if self.placeholder:
            self.delete(0, "end")
            self.placeholder = False
            self.configure(foreground=getattr(self.winfo_toplevel(), 'vedaboat_colors', {'text':TEXT})['text'])

    def _blur(self, event=None):
        if not super().get():
            self.placeholder = True
            self.insert(0, self.hint)
            self.configure(foreground=getattr(self.winfo_toplevel(), 'vedaboat_colors', {'muted':MUTED})['muted'])

    def value(self):
        return "" if self.placeholder else self.get().strip()

    def set(self, value="", hint=None):
        if hint:
            self.hint = hint
        self.delete(0, "end")
        self.placeholder = False
        self.configure(foreground=getattr(self.winfo_toplevel(), 'vedaboat_colors', {'text':TEXT})['text'])
        if value:
            self.insert(0, value)
        else:
            self._blur()


class App:
    def __init__(self, root: tk.Tk, state: State):
        self.root, self.state = root, state
        self.events: queue.Queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="VedaBoat-browser")
        self.tools = Tools(state.directory)
        self.tree_source, self.yt_source = DesireTree(), YouTube(self.tools)
        self.engine = Engine(state, self.tools, lambda kind, data: self.events.put(("engine", kind, data)))
        self.source = state.get("source", "tree")
        self.selections = {"tree": Selection(), "youtube": Selection()}
        self.collection: Collection | None = None
        self.cache: dict[str, Collection] = {}
        self.history = {"tree": [], "youtube": []}
        self.mode = tk.StringVar(value=state.get("youtube_mode", "videos"))
        self.quality = tk.IntVar(value=audio_quality(state.get("youtube_quality",128)))
        self.theme_mode = tk.StringVar(value=theme_choice(state.get('theme_mode','System')))
        self.dark = tk.BooleanVar(value=False)
        self.theme_timer = None
        self.repeat = tk.BooleanVar(value=state.get('repeat_downloads', False))
        self.concurrency = tk.IntVar(value=max(1,min(10,int(state.get('concurrency',1)))))
        self.shortcuts = Shortcuts(state)
        self.discovery_counts = {}
        self.root_key = None
        self.list_message = ''
        self.last_channel = state.get("last_channel", CHANNELS[0][1])
        self.load_id = 0
        self.load_cancel = threading.Event()
        self.selection_tasks: dict[str, threading.Event] = {}
        self.size_pending = {}
        self.size_inflight = set()
        self.size_timer = None
        self.size_active = False
        self.size_cancel = threading.Event()
        self.loading = False
        self.updating = False
        self.update_cancel = threading.Event()
        self.closing = False
        self.selected_only = False
        self.last_error = ""
        self.last_details = ""
        self.visible: list[Entry] = []
        self.download_position = 0
        self.progress = 0.0
        self.progress_by_job = {}
        self.destination = tk.StringVar(value=state.get("destination", ""))
        self.search = tk.StringVar()
        self.select_all_var = tk.BooleanVar()
        self.status = tk.StringVar(value="Choose a folder or open a collection link.")
        self._style()
        self._layout()
        self.set_theme()
        self.theme_timer=self.root.after(1500,self.poll_system_theme)
        self.search.trace_add("write", lambda *_: self.render_files())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.poll)
        self.root.after(150, lambda: self.switch_source(self.source, initial=True))
        self.refresh_download()

    def _style(self):
        self.root.title(APP_NAME)
        width = min(1040, self.root.winfo_screenwidth() - 40)
        height = min(740, self.root.winfo_screenheight() - 80)
        # A small fixed inset also works on mixed-DPI multi-monitor desktops,
        # whose virtual screen width need not match the primary work area.
        self.root.geometry(f"{width}x{height}+20+20")
        self.root.minsize(min(780, width), min(610, height))
        saved=self.state.get("window_geometry")
        if saved:
            import re
            match=re.fullmatch(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)",saved)
            if match:
                w,h,x,y=map(int,match.groups())
                w=max(780,min(w,self.root.winfo_screenwidth()-40));h=max(610,min(h,self.root.winfo_screenheight()-80))
                x=max(0,min(x,self.root.winfo_screenwidth()-w));y=max(0,min(y,self.root.winfo_screenheight()-h-40))
                self.root.geometry(f"{w}x{h}+{x}+{y}")
        if self.state.get("window_maximized",False):
            self.root.after_idle(lambda:self.root.state("zoomed"))
        self.root.configure(bg=BG)
        self.root.option_add("*Font", "{Segoe UI} 10")
        icon = application_directory() / "assets" / "app-icon.ico"
        if icon.exists():
            self.root.iconbitmap(str(icon))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", padding=(12, 7), background=BG, bordercolor=LINE, foreground=TEXT, focuscolor=WARM)
        style.map("TButton", background=[("active", SOFT)], foreground=[("disabled", "#999e98")])
        style.configure("Quiet.TButton", borderwidth=0, padding=(5, 3), foreground=MUTED, font=("Segoe UI",9))
        style.configure("Icon.TButton",padding=5,borderwidth=0,background=BG)
        style.configure("Primary.Icon.TButton",padding=(12,5),borderwidth=0,background=WARM,foreground="white")
        style.map("Primary.Icon.TButton",background=[("disabled","#cab3a8"),("active","#9b4d2e")])
        style.configure("Primary.TButton", background=WARM, foreground="white", borderwidth=0, padding=(20, 11), font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("disabled", "#cab3a8"), ("active", "#9b4d2e")], foreground=[("disabled", "white")])
        style.configure("Tab.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 6), background=SOFT, borderwidth=0)
        style.configure("Active.Tab.TButton", background=BG, foreground="#713a25", borderwidth=0)
        style.configure("TEntry", padding=5, bordercolor=LINE, fieldbackground=BG, foreground=TEXT)
        style.configure("TCheckbutton", background=BG, foreground=TEXT, padding=3)
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TRadiobutton", background=BG, foreground=TEXT)
        style.map("TRadiobutton", background=[("active", BG)])
        style.configure("Treeview", background=BG, fieldbackground=BG, foreground=TEXT, rowheight=28, indent=20, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=SOFT, foreground=MUTED, borderwidth=0, padding=(5, 8), font=("Segoe UI", 9))
        style.map("Treeview", background=[("selected", SELECTED)], foreground=[("selected", TEXT)])
        style.configure("Horizontal.TProgressbar", background=WARM, troughcolor=SOFT, borderwidth=0, thickness=5)

    def label(self, parent, text, muted=False, **kw):
        return ttk.Label(parent, text=text, style="Muted.TLabel" if muted else "TLabel", **kw)

    def set_theme(self):
        mode=theme_choice(self.theme_mode.get())
        self.theme_mode.set(mode)
        self.dark.set(mode=='Dark' or mode=='System' and system_is_dark())
        self.colors=apply_theme(self.root,self.dark.get())
        if self.state.get('theme_mode')!=mode:
            self.state.put('theme_mode',mode)
        for button,name in getattr(self,'icon_widgets',[]):
            if button.winfo_exists() and not name.endswith('-white'):
                button.configure(image=self.icons.get(name+'-dark' if self.dark.get() else name,''))
        if hasattr(self,'files'):
            self.files.tag_configure('checked',background=self.colors['selected'])
            self.files.tag_configure('unavailable',foreground=self.colors['muted'])
            self.browser.paint_focus()

    def poll_system_theme(self):
        self.theme_timer=None
        if self.closing:
            return
        if self.theme_mode.get()=='System' and self.dark.get()!=system_is_dark():
            self.set_theme()
        self.theme_timer=self.root.after(1500,self.poll_system_theme)

    def _layout(self):
        from .layout import build_layout
        build_layout(self)

    def submit(self, fn, done, fail=None):
        future = self.executor.submit(fn)

        def complete(f):
            try:
                value = f.result()
            except BaseException as error:
                self.events.put(("call", lambda e=error: (fail or self.error)(e)))
            else:
                self.events.put(("call", lambda v=value: done(v)))

        future.add_done_callback(complete)

    def selected(self) -> Selection:
        return self.selections[self.source]

    def unfinished(self) -> bool:
        return any(r["status"] in ("pending", "downloading", "converting", "waiting_conversion") for r in self.state.queue())

    def locked(self) -> bool:
        return self.engine.running or self.unfinished() or self.updating

    def current_url(self):
        return self.collection.url if self.collection else TREE_HOME if self.source == "tree" else self.last_channel

    def sidebar_render(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        self.label(self.sidebar, 'Channel shortcuts' if self.source=='youtube' else 'Desire Tree audio',muted=True).pack(anchor='w',padx=6,pady=(3,8))
        scroll=ttk.Frame(self.sidebar);scroll.pack(fill='both',expand=True)
        canvas=tk.Canvas(scroll,highlightthickness=0,bg=self.colors['bg'],width=155)
        bar=ttk.Scrollbar(scroll,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        inner=ttk.Frame(canvas);wid=canvas.create_window(0,0,window=inner,anchor='nw')
        self.shortcuts_inner=inner
        self.shortcut_buttons=[]
        inner.bind('<Configure>',lambda _:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(wid,width=e.width))
        def wheel(event):
            canvas.yview_scroll(int(-event.delta/120),'units');return 'break'
        canvas.bind('<MouseWheel>',wheel)
        from .widgets import Tooltip
        for item in self.shortcuts.items:
            if item['source'] != self.source:
                continue
            button=ttk.Button(inner,text=item['name'],style='Quiet.TButton',width=18,command=lambda i=item:self.open_shortcut(i))
            button.pack(fill='x',pady=2)
            self.shortcut_buttons.append(button)
            button.bind('<Button-3>',lambda event,i=item:self.shortcut_menu(event,i))
            button.bind('<MouseWheel>',wheel)
            Tooltip(button, item['name']+'\nRight-click to edit or remove')
        self.add_shortcut_button=ttk.Button(inner,text='+ Add shortcut…',style='Quiet.TButton',command=self.shortcut_dialog)
        self.add_shortcut_button.pack(fill='x',pady=(12,4))
        self.add_shortcut_button.bind('<MouseWheel>',wheel)
        self.set_theme()

    def open_shortcut(self, item):
        self.mode.set(item.get('mode','videos'))
        if self.source != item['source']:
            self.source = item['source']
            self.state.put('source',self.source)
            self.sidebar_render()
        self.state.put('youtube_mode', self.mode.get())
        for key,button in self.tab_buttons.items():
            button.configure(style='Active.Tab.TButton' if key==self.source else 'Tab.TButton')
        if self.source=='youtube':self.youtube_modes.pack(side='right',padx=5)
        else:self.youtube_modes.pack_forget()
        self.load(item['url'])

    def shortcut_menu(self,event,item):
        menu=tk.Menu(self.root,tearoff=False,bg=self.colors['soft'],fg=self.colors['text'])
        menu.add_command(label='Edit…',command=lambda:self.shortcut_dialog(item))
        menu.add_command(label='Remove',command=lambda:(self.shortcuts.remove(item['id']),self.sidebar_render()))
        menu.tk_popup(event.x_root,event.y_root)

    def shortcut_dialog(self,item=None):
        window,outer=self.dialog('Edit shortcut' if item else 'Add shortcut',580)
        window.geometry('580x370');window.minsize(470,340)
        name=tk.StringVar(value=item['name'] if item else self.collection.title if self.collection else '')
        link=tk.StringVar(value=item['url'] if item else self.current_url())
        self.label(outer,'Name').pack(anchor='w')
        entry=ttk.Entry(outer,textvariable=name);entry.pack(fill='x',pady=(3,12))
        self.label(outer,'Link').pack(anchor='w')
        ttk.Entry(outer,textvariable=link).pack(fill='x',pady=3)
        message=self.label(outer,'Desire Tree folder/MP3 or YouTube channel/playlist/video.',muted=True,wraplength=490)
        message.pack(anchor='w',pady=10)
        def save():
            try:
                self.shortcuts.put(name.get(),link.get(),item['id'] if item else None,self.mode.get())
            except (UserError,ValueError) as error:
                message.configure(text=str(error),foreground=self.colors['error']);return
            self.sidebar_render();window.destroy()
        ttk.Button(outer,text='Save',command=save).pack(side='right',pady=12)
        ttk.Button(outer,text='Cancel',command=window.destroy).pack(side='right',padx=8,pady=12)
        window.bind('<Return>',lambda _:save());entry.focus_set();self.set_theme()

    def switch_source(self, source, initial=False):
        if source == self.source and not initial:
            return
        self.source = source
        self.state.put("source", source)
        self.selected_only = False
        self.search_box.set()
        self.collection = None
        for key, button in self.tab_buttons.items():
            button.configure(style="Active.Tab.TButton" if key == source else "Tab.TButton")
        self.sidebar_render()
        self.link.set(hint="Paste any YouTube video, playlist, or channel link…" if source == "youtube" else "Paste a Desire Tree folder or MP3 link…")
        if source == "youtube":
            self.youtube_modes.pack(side="right",padx=5)
        else:
            self.youtube_modes.pack_forget()
        self.update_footer()
        url = self.state.get(source + "_url", TREE_HOME if source == "tree" else self.last_channel)
        self.load(url, history=False)

    def fetch(self, url, source, mode, cancelled=None, force=False):
        if source == "tree":
            canonical = tree_url(tree_path(url)) if not tree_path(url).lower().endswith(".mp3") else url
        else:
            canonical = youtube_url(url, mode)[0]
        if not force and canonical in self.cache:
            return self.cache[canonical]
        result = self.tree_source.browse(url, cancelled) if source == "tree" else self.yt_source.browse(url, mode, cancelled)
        self.cache[canonical] = result
        return result

    def load(self, url, force=False, history=True):
        if self.updating or self.closing:
            return
        if self.source=='youtube':
            from urllib.parse import unquote,urlsplit
            view=unquote(urlsplit(url).path).rstrip('/').rsplit('/',1)[-1]
            if view in ('videos','playlists'):
                self.mode.set(view)
                self.state.put('youtube_mode',view)
        if history and self.collection:
            self.history[self.source].append(self.collection.url)
        self.browser.cancel()
        if force:
            self.browser.children.clear()
            self.browser.expanded.clear()
            self.browser.errors.clear()
        self.load_cancel.set()
        self.load_cancel = threading.Event()
        token, source, mode = self.load_cancel, self.source, self.mode.get()
        self.load_id += 1
        load_id = self.load_id
        self.loading = True
        self.list_message = ''
        self.selected_only = False
        self.search_box.set()
        self.location.configure(text="Loading collection…")
        self.notice.configure(text="", foreground=self.colors['muted'])
        self.breadcrumbs.render()
        self.render_files()

        def done(collection):
            if load_id != self.load_id:
                return
            self.loading = False
            self.collection = collection
            self.state.put(source + "_url", collection.url)
            if source == "youtube":
                try:
                    if youtube_url(url, mode)[1] == "channel":
                        self.last_channel = url
                        self.state.put("last_channel", url)
                except UserError:
                    pass
            self.location.configure(text=collection.title[:100] + ("…" if len(collection.title) > 100 else ""))
            self.link.set(collection.url)
            self.notice.configure(text=collection.notice)
            self.breadcrumbs.render()
            self.render_files()
            if not collection.entries:
                self.list_message=collection.notice or 'No recordings or collections are available here.'
                self.render_files()

        def failed(error):
            if load_id != self.load_id:
                return
            self.loading = False
            self.collection = None
            self.list_message=str(error) if isinstance(error,UserError) else 'Could not load this collection. Check your connection and try Refresh.'
            self.location.configure(text="Collection could not be opened")
            self.render_files()
            self.breadcrumbs.render()
            self.error(error)

        self.submit(lambda: self.fetch(url, source, mode, token, force), done, failed)

    def open_link(self):
        value = self.link.value()
        if value:
            self.load(value)

    def change_mode(self):
        self.state.put("youtube_mode", self.mode.get())
        self.load(youtube_url(self.last_channel,self.mode.get())[0])

    def choose_mode(self,value):
        self.mode.set(value)
        self.change_mode()

    def home(self):
        self.load(TREE_HOME if self.source == "tree" else youtube_url(self.last_channel,self.mode.get())[0])

    def up(self):
        if self.collection and self.collection.parent_url:
            self.load(self.collection.parent_url)
        elif self.source == "youtube":
            self.load(self.last_channel)

    def back(self):
        if self.history[self.source]:
            self.load(self.history[self.source].pop(), history=False)

    def show_selected(self):
        self.selected_only = not self.selected_only
        self.render_files()

    def render_files(self):
        if not hasattr(self, "files"):
            return
        selection = self.selected()
        query = self.search_box.value().casefold()
        rows = list(selection.entries.values()) if self.selected_only else self.collection.entries if self.collection and not self.loading else []
        self.root_key = None
        if self.collection and not self.loading and not self.selected_only:
            try:
                if '://' not in self.collection.url:
                    raise UserError('No canonical collection URL')
                if self.source=='tree':
                    path=tree_path(self.collection.url)
                    root=None if path.lower().endswith('.mp3') else Entry('tree:'+path,'tree','folder',self.collection.title,self.collection.url,path=path)
                else:
                    url,kind=youtube_url(self.collection.url,self.mode.get())
                    root=None if kind=='video' else Entry(('playlist:' if kind=='playlist' else 'channel:')+url,'youtube','playlist' if kind=='playlist' else 'folder',self.collection.title,url)
                    if kind=='playlist':
                        from urllib.parse import parse_qs,urlsplit
                        root.key='playlist:'+parse_qs(urlsplit(url).query)['list'][0]
                if root:
                    self.root_key=root.key
                    node=self.browser.iid(self.collection.url,root)
                    if node not in self.browser.children:
                        self.browser.expanded.add(node)
                    self.browser.children[node]=rows
                    rows=[root]
            except UserError:
                pass
        self.visible = self.browser.render(rows, query, self.selected_only)
        if self.loading:
            self.browser.message('Loading recordings…')
        elif not self.visible:
            self.browser.message(self.list_message or ('No selected recordings.' if self.selected_only else 'No matching recordings.' if query else 'No recordings in this collection.'))
        for value,button in self.mode_buttons.items():
            button.configure(style='Active.Tab.TButton' if self.mode.get()==value else 'Tab.TButton')
        if self.loading:
            self.count.configure(text="Loading…")
        else:
            self.count.configure(text=f"{len(self.visible):,} shown")
        shown=[self.browser.rows[n] for n in self.browser.shown_selection()]
        checked = sum(selection.state(e) == "checked" for e in shown)
        self.select_all_var.set(bool(shown) and checked == len(shown))
        mixed=any(selection.state(e) in ('checked','partial','loading') for e in shown) and not self.select_all_var.get()
        self.select_all_check.configure(state="disabled" if self.locked() or self.loading else "normal")
        self.select_all_check.state(["alternate"] if mixed else ["!alternate"])
        self.clear_button.configure(state="disabled" if self.locked() or not (selection.entries or selection.loading or selection.intents) else "normal")
        self.selected_button.configure(text="Show collection" if self.selected_only else "Show selected")
        count = len(selection.entries)
        self.selection_label.configure(text=f"{count:,} selected")
        self.refresh_download()

    def toggle(self, entry, desired=None, render=True):
        if self.locked():
            return
        selection = self.selected()
        desired = selection.state(entry) not in ("checked", "loading") if desired is None else desired
        if not desired:
            token = self.selection_tasks.pop(entry.key, None)
            if token:
                token.set()
            selection.deselect(entry)
            if entry.container:
                prefix = entry.key.rstrip("/") + "/"
                for key, child_token in list(self.selection_tasks.items()):
                    if key.startswith(prefix) or entry.key in selection.parents.get(key,set()):
                        child_token.set()
                        self.selection_tasks.pop(key, None)
                        selection.loading.discard(key)
                        selection.intents.discard(key)
        elif not entry.container:
            selection.excluded.discard(entry.key)
            selection.entries[entry.key] = entry
            if entry.source == "tree" and entry.size is None:
                self.enrich_size(entry)
        elif entry.key not in selection.loading:
            selection.excluded.difference_update(selection.children(entry))
            selection.excluded={k for k in selection.excluded if entry.key not in selection.parents.get(k,set()) and not (entry.source=='tree' and k.startswith(entry.key.rstrip('/')+'/'))}
            selection.excluded_groups.discard(entry.key)
            selection.excluded_groups={g for g in selection.excluded_groups if entry.key not in selection.parents.get(g,set())}
            if entry.source=='tree':
                selection.excluded_groups={g for g in selection.excluded_groups if not g.startswith(entry.key.rstrip('/')+'/')}
            selection.intents.add(entry.key)
            source, mode = self.source, self.mode.get()
            generation = selection.generation
            token = threading.Event()
            self.selection_tasks[entry.key] = token
            selection.loading.add(entry.key)

            def discover():
                visited, groups, recordings = set(), {}, {}

                def walk(container):
                    if token.is_set():
                        raise Paused()
                    if container.key in visited:
                        return set()
                    visited.add(container.key)
                    collection = self.fetch(container.url, source, mode, token)
                    members = set()
                    for child in collection.entries:
                        if token.is_set():
                            raise Paused()
                        if child.container:
                            members |= walk(child)
                        else:
                            recordings[child.key] = child
                            members.add(child.key)
                            if len(recordings)%10==0:
                                found=len(recordings)
                                self.events.put(('call',lambda n=found:self.discovery_progress(entry.key,n,token,selection,generation)))
                    groups[container.key] = members
                    return members

                walk(entry)
                return list(recordings.values()), groups

            def done(result):
                if token.is_set() or selection.generation != generation:
                    return
                recordings, groups = result
                selection.members.update(groups)
                selection.accept_collection(entry, recordings)
                self.selection_tasks.pop(entry.key, None)
                if not recordings:
                    self.list_message='This collection has no downloadable recordings.'
                self.render_files()
                # Selected sizes are discovered gradually; no launch-time site scan.
                if source == "tree":
                    self.submit(lambda: self.size_collection(recordings, token), lambda _: self.render_files(), lambda _: None)

            def failed(error):
                if selection.generation != generation or token.is_set():
                    return
                selection.loading.discard(entry.key)
                self.selection_tasks.pop(entry.key, None)
                self.render_files()
                self.error(error)

            self.submit(discover, done, failed)
        if render:
            self.render_files()

    def discovery_progress(self,key,count,token,selection,generation):
        if not token.is_set() and selection.generation==generation and not self.closing:
            self.discovery_counts[key]=count
            self.render_files()

    def size_collection(self, entries, token):
        for i, entry in enumerate(entries):
            if token.is_set() or self.closing:
                return
            try:
                if entry.size is None:
                    self.tree_source.size(entry)
                if i % 8 == 0:
                    self.events.put(("call", self.refresh_download))
            except Exception:
                pass

    def enrich_size(self, entry):
        if entry.key in self.size_inflight or entry.size is not None:
            return
        self.size_pending[entry.key]=entry
        if not self.size_active and self.size_timer is None:
            self.size_timer=self.root.after(200,self.flush_sizes)

    def flush_sizes(self):
        self.size_timer=None
        if self.closing or not self.size_pending:
            return
        entries=list(self.size_pending.values());self.size_pending.clear()
        self.size_inflight={e.key for e in entries};self.size_active=True
        def done(_=None):
            self.size_inflight.clear();self.size_active=False
            if self.closing:
                return
            self.render_files()
            if self.size_pending:
                self.flush_sizes()
        self.submit(lambda:self.size_collection(entries,self.size_cancel),done,done)

    def select_all(self):
        if self.locked():
            return
        desired = self.select_all_var.get()
        for node in self.browser.minimal(self.browser.shown_selection()):
            self.toggle(self.browser.rows[node], desired, render=False)
        self.render_files()

    def clear_selection(self):
        if self.locked():
            return
        selection = self.selected()
        for key in list(selection.loading):
            token = self.selection_tasks.pop(key, None)
            if token:
                token.set()
        selection.clear()
        self.files.selection_set(())
        self.render_files()

    def choose_folder(self):
        if self.locked():
            return
        path = filedialog.askdirectory(title="Choose download folder", initialdir=self.destination.get() or str(Path.home() / "Music"), mustexist=False)
        if path:
            self.destination.set(path)
            self.state.put("destination", path)
            self.refresh_download()

    def refresh_download(self):
        if not hasattr(self, "main_button"):
            return
        rows = self.state.queue()
        self.update_footer()
        pending = sum(r["status"] in ("pending", "downloading", "converting", "waiting_conversion") for r in rows)
        completed = sum(r["status"] == "done" for r in rows)
        skipped = sum(r["status"] == "skipped" for r in rows)
        failed = sum(r["status"] == "failed" for r in rows)
        self.destination_label.configure(text=self.destination.get() or "No folder chosen")
        self.folder_button.configure(text="Change folder…" if self.destination.get() else "Choose folder…", state="disabled" if self.locked() else "normal")
        for button in (self.open_folder_button, self.retry_button, self.details_button):
            button.pack_forget()
        if rows:
            self.open_folder_button.pack(side="left")
        if failed and not self.engine.running and not pending:
            self.retry_button.pack(side="left", padx=(6, 0))
        if self.last_error or failed:
            self.details_button.pack(side="right")
        total = len(rows)
        if self.engine.running:
            label = "Pausing…" if self.engine.pause.is_set() else "Pause"
            self.main_button.configure(text=label,image=self.icons.get("pause-white",""), state="disabled" if self.engine.pause.is_set() else "normal")
            active=sum(r['status']=='downloading' for r in rows)
            converting=sum(r['status']=='converting' for r in rows)
            self.summary.configure(text=f"{completed + skipped + failed:,}/{total:,} processed · {active} downloading" + (' · converting' if converting else '') + (f' · {failed} failed' if failed else ''))
            running_positions={r['position'] for r in rows if r['status']=='downloading'}
            progress=sum(v for p,v in self.progress_by_job.items() if p in running_positions)
            pct = ((completed + skipped + failed) + progress) / total * 100 if total else 0
            self.bar.configure(value=min(100, pct))
        elif pending:
            self.main_button.configure(text="Resume", image=self.icons.get("resume-white",""),state="disabled" if self.updating else "normal")
            self.summary.configure(text=f"Progress saved · {pending:,} remaining · {completed + skipped:,} completed · {failed:,} failed")
            self.status.set("Resume when you are ready. Completed recordings will be verified and skipped.")
            self.bar.configure(value=(total - pending) / total * 100 if total else 0)
        else:
            selection = self.selected()
            selected = list(selection.entries.values())
            known_size = sum(e.size_for(self.quality.get()) or 0 for e in selected)
            unknown = sum(e.size_for(self.quality.get()) is None for e in selected)
            ready = bool(selected and self.destination.get() and not selection.loading and not self.updating)
            self.main_button.configure(text="Download",image=self.icons.get("download-white",""), state="normal" if ready else "disabled")
            if rows and not selected:
                self.summary.configure(text=f"Finished · {completed:,} downloaded · {skipped:,} already present · {failed:,} failed")
                self.status.set("Choose more recordings, or retry failed downloads." if failed else "Your recordings are ready.")
                self.bar.configure(value=100)
            else:
                size = ("about " if self.source == "youtube" else "") + format_size(known_size) if known_size else "size being determined" if unknown else "0 MB"
                if unknown and known_size:
                    size += f" + {unknown:,} with size unknown"
                self.summary.configure(text=f"{len(selected):,} recordings · {size}" if selected else "Choose recordings to begin")
                self.bar.configure(value=0)
                self.status.set("Finding recordings…" if selection.loading else "Choose a download folder in step 2." if selected and not self.destination.get() else ("Ready. Existing recordings will be saved as numbered copies." if self.repeat.get() else "Ready. Completed recordings will be skipped.") if selected else "Select a folder, playlist, or individual recordings above.")

    def download(self):
        if self.engine.running:
            self.engine.request_pause()
        elif self.unfinished():
            self.progress = 0
            self.progress_by_job.clear()
            self.engine.start()
            self.status.set("Resuming downloads…")
        else:
            entries = list(self.selected().entries.values())
            if not entries or not self.destination.get() or self.selected().loading or self.updating:
                return
            try:
                self.state.make_queue([replace(e,quality=audio_quality(self.quality.get())) if e.source=="youtube" else e for e in entries], Path(self.destination.get()))
            except Exception as error:
                self.error(error)
                return
            self.progress = 0
            self.progress_by_job.clear()
            self.last_error = ""
            self.engine.start()
            self.status.set("Starting downloads…")
        self.render_files()

    def retry_failed(self):
        if self.engine.running or self.updating:
            return
        self.state.retry_failed()
        self.engine.start()
        self.progress = 0
        self.render_files()

    def open_folder(self):
        rows = self.state.queue()
        value = rows[0]["destination"] if rows else self.destination.get()
        if value and Path(value).is_dir():
            os.startfile(value)

    def error(self, error):
        if isinstance(error, Paused) or self.closing:
            return
        self.last_error = str(error)
        import traceback
        self.last_details = "".join(traceback.format_exception(type(error), error, error.__traceback__)) + "\n\n" + self.yt_source.last_details
        self.engine.log(self.last_details)
        message = str(error) if isinstance(error, UserError) else "The collection could not be loaded. Check your connection, then try Refresh."
        if not self.collection:
            self.list_message=message
            self.render_files()
        else:
            self.notice.configure(text=message, foreground=self.colors['error'])
        self.refresh_download()

    def poll(self):
        try:
            for _ in range(150):
                item = self.events.get_nowait()
                if item[0] == "call":
                    item[1]()
                else:
                    self.engine_event(item[1], item[2])
        except queue.Empty:
            pass
        finally:
            if not self.closing:
                self.root.after(100, self.poll)

    def engine_event(self, kind, data):
        if kind == "current":
            self.progress = 0
            self.download_position = data["position"]
            self.status.set("Downloading · " + data["title"][:95])
        elif kind == "progress":
            if data.get("total"):
                self.progress = min(.98, data["bytes"] / data["total"])
                self.progress_by_job[data.get('position',0)]=self.progress
            self.status.set(f"Downloading · {format_size(data['bytes'])}" + (f" of {format_size(data['total'])}" if data.get("total") else ""))
        elif kind == "converting":
            self.status.set("Converting to MP3 · " + data["title"][:90])
        elif kind == "pausing":
            self.status.set("Finishing the active conversion before pausing…" if data["converting"] else "Pausing downloads… partial files are being saved.")
        elif kind in ("failed", "error"):
            self.last_error = data["message"]
            self.notice.configure(text=data["message"], foreground=self.colors['error'])
        elif kind == "completed":
            self.progress = 0
        elif kind == "stopped":
            # The worker has queued this event from its finally block. Recheck once
            # the thread has returned so Resume is not accidentally shown as Pause.
            if self.engine.running:
                self.root.after(150, lambda: self.engine_event("stopped", {}))
                return
            if not self.unfinished():
                for selection in self.selections.values():
                    selection.clear()
            self.render_files()
        self.refresh_download()

    def dialog(self, title, width=560):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg=BG)
        window.transient(self.root)
        window.geometry(f"{width}x420")
        window.minsize(width, 360)
        outer = ttk.Frame(window, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=title, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 18))
        self.set_theme()
        return window, outer

    def settings(self):
        window, outer = self.dialog("Settings")
        window.geometry("590x590")
        window.minsize(550,560)
        row=ttk.Frame(outer);row.pack(fill='x',pady=(0,10))
        self.label(row,'Color theme').pack(side='left')
        theme=ttk.Combobox(row,textvariable=self.theme_mode,values=THEME_OPTIONS,state='readonly',width=14)
        theme.pack(side='right');theme.bind('<<ComboboxSelected>>',lambda _:self.set_theme())
        row=ttk.Frame(outer);row.pack(fill="x",pady=6)
        self.label(row,"YouTube MP3 quality").pack(side="left")
        choice=tk.StringVar(value=f"{self.quality.get()} kbps")
        combo=ttk.Combobox(row,textvariable=choice,values=[f"{q} kbps" for q in QUALITY_OPTIONS],state="readonly",width=14)
        combo.pack(side="right")
        combo.bind("<<ComboboxSelected>>",lambda _:self.set_quality(choice.get().split()[0]))
        self.label(outer,"128 kbps is the default. Applies to new runs; unfinished runs keep their quality.\nHigher bitrates make larger files and cannot restore missing source detail.",muted=True,wraplength=500).pack(anchor="w",pady=(3,8))
        def save_download_options(_=None):
            self.state.put('concurrency',int(self.concurrency.get()))
            self.state.put('repeat_downloads',self.repeat.get())
            self.refresh_download()
        ttk.Checkbutton(outer,text='Download existing recordings again',variable=self.repeat,command=save_download_options).pack(anchor='w',pady=(8,2))
        self.label(outer,'Keeps originals and saves numbered copies. Off: verify and skip.',muted=True,wraplength=500).pack(anchor='w')
        row=ttk.Frame(outer);row.pack(fill='x',pady=(14,4))
        self.label(row,'Downloads at the same time').pack(side='left')
        concurrent=ttk.Combobox(row,textvariable=self.concurrency,values=list(range(1,11)),state='readonly',width=5)
        concurrent.pack(side='right');concurrent.bind('<<ComboboxSelected>>',save_download_options)
        self.label(outer,'Default: 1. MP3 conversion runs one at a time. Changes apply to new runs.',muted=True,wraplength=500).pack(anchor='w')
        ttk.Button(outer,text='Restore default shortcuts',command=lambda:(self.shortcuts.restore(),self.sidebar_render())).pack(anchor='w',pady=(14,0))
        message = self.label(outer, "Update YouTube support if YouTube links stop working.", muted=True, wraplength=500)
        message.pack(anchor="w", pady=(20, 8))
        button = ttk.Button(outer, text="Update YouTube support", command=lambda: update())
        button.pack(anchor="w")
        button.configure(state="disabled" if self.engine.running or self.loading or self.browser.pending or any(s.loading for s in self.selections.values()) or self.updating else "normal")

        def set_message(value):
            if window.winfo_exists():
                message.configure(text=value)

        def update():
            self.updating = True
            button.configure(state="disabled")
            self.refresh_download()

            def done(value):
                self.updating = False
                set_message(value)
                if window.winfo_exists():
                    button.configure(state="normal")
                self.refresh_download()

            def failed(error):
                self.engine.log(str(error))
                done(str(error) if isinstance(error, UserError) else "The update could not finish. Check your connection and try again. Current support is unchanged.")

            self.submit(lambda: update_youtube(self.tools, lambda text: self.events.put(("call", lambda t=text: set_message(t))), self.update_cancel), done, failed)

        self.label(outer, "Preferences and unfinished downloads survive app updates.", muted=True, wraplength=500).pack(anchor="w", pady=(20, 0))
        self.label(outer, f"{APP_NAME} {__version__}", muted=True).pack(side="left", anchor="s", pady=(14, 0))
        ttk.Button(outer, text="Close", command=window.destroy).pack(side="right", anchor="s", pady=(14, 0))
        self.set_theme()

    def set_quality(self,value):
        self.quality.set(audio_quality(value))
        self.state.put("youtube_quality",self.quality.get())
        self.update_footer()
        self.render_files()

    def update_footer(self):
        if self.source=="youtube":
            rows=self.state.queue()
            current=next((json.loads(r["entry"]).get("quality",128) for r in rows if r["status"] in ("pending","downloading","converting","waiting_conversion")),None)
            suffix=f" · current run {current} kbps" if current and current!=self.quality.get() else ""
            self.footer.configure(text=f"YouTube downloads · MP3 · {self.quality.get()} kbps"+suffix)
        else:
            self.footer.configure(text="Desire Tree Downloads · devotee folders · original MP3 filenames")

    def help(self):
        window, outer = self.dialog("Help", 650)
        window.geometry("650x620")
        text = (
            "1. Choose recordings\n"
            "Browse folders or paste a link. YouTube has Videos and Playlists tabs. "
            "Select folders to include all subfolders. Search keeps your selections.\n\n"
            "2. Choose download folder\n"
            "Desire Tree Downloads → devotee → subfolders\n"
            "YouTube downloads → channel → playlist\n\n"
            "3. Download recordings\n"
            "Use Download, Pause, and Resume. Closing saves unfinished work. "
            "An active MP3 conversion finishes before pausing. Retry failed appears when needed.\n\n"
            "QUICK CONTROLS\n"
            "↑ / ↓                 Move focus; keep download ticks\n"
            "← / →                 Collapse / expand the focused folder\n"
            "Ctrl+click           Add or remove one item\n"
            "Shift+click / ↑ ↓   Select and tick a range\n"
            "Home / End          Focus the first / last row\n"
            "Space                 Tick / untick the focused row\n"
            "Ctrl+A                Select all shown\n"
            "Enter                 Open a folder or playlist\n\n"
            "Click a selected item again to deselect it. Click an arrow to expand without "
            "selecting. Path branches navigate; Collapse all keeps checks. "
            "Right-click a shortcut to edit or remove it. Selected totals include hidden items. "
            "Settings → Color theme offers System (default), Light, and Dark.\n\n"
            "Trouble with YouTube? Settings → Update YouTube support. "
            "Use Details… for error information. Keep the whole unzipped app folder together."
        )
        box = tk.Text(outer, wrap="word", bg=BG, fg=TEXT, relief="flat", font=("Segoe UI", 10), padx=0, pady=0)
        box.insert("1.0", text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)
        ttk.Button(outer, text="Close", command=window.destroy).pack(anchor="e", pady=(12, 0))
        self.set_theme()

    def details(self):
        window, outer = self.dialog("Download details", 800)
        window.geometry("800x560")
        failures = [r for r in self.state.queue() if r["status"] == "failed"]
        text = "\n\n".join(Entry.from_dict(json.loads(r["entry"])).title + "\n" + r["error"] for r in failures)
        text += "\n\n" + self.last_details + "\n\n" + "\n".join(self.engine.details[-100:])
        box = tk.Text(outer, wrap="word", bg=SOFT, fg=TEXT, relief="flat", font=("Consolas", 9))
        box.insert("1.0", text.strip() or "No errors reported.")
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)
        ttk.Button(outer, text="Close", command=window.destroy).pack(anchor="e", pady=(12, 0))
        self.set_theme()

    def close(self):
        if self.closing:
            return
        self.closing = True
        if self.theme_timer:
            self.root.after_cancel(self.theme_timer)
            self.theme_timer=None
        self.state.put("window_maximized",self.root.state()=="zoomed")
        if self.root.state()=="normal":
            self.state.put("window_geometry",self.root.geometry())
        self.state.put("column_widths",{"title":self.files.column("#0","width"),"size":self.files.column("size","width")})
        self.state.put("sidebar_width",self.panes.sashpos(0))
        self.browser.cancel()
        self.size_cancel.set()
        self.update_cancel.set()
        self.load_cancel.set()
        for token in self.selection_tasks.values():
            token.set()
        if self.engine.running:
            self.engine.request_pause()
            self.status.set("Finishing conversion and saving progress…" if self.engine.converting else "Saving progress…")
            self.main_button.configure(state="disabled")
        self.root.after(150, self.finish_close)

    def finish_close(self):
        if self.engine.running:
            self.root.after(150, self.finish_close)
            return
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()


def main():
    if os.name == "nt":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("IDTYTDownloader.AudioDownloader.2")
        except Exception:
            pass
    root = tk.Tk()
    state = None
    mutex = None
    try:
        if os.name == "nt":
            import ctypes
            import hashlib
            mutex_name = "Local\\VedaBoat-" + hashlib.sha256(str(data_directory().resolve()).encode()).hexdigest()[:24]
            ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
            if ctypes.windll.kernel32.GetLastError() == 183:
                messagebox.showinfo(APP_NAME, "The downloader is already open. Close its existing window before opening this version.")
                root.destroy()
                return
        state = State()
        App(root, state)
        root.mainloop()
    except Exception as error:
        messagebox.showerror(APP_NAME, "The downloader could not start. Your saved downloads have been kept.\n\n" + str(error))
        if root.winfo_exists():
            root.destroy()
    finally:
        # Background browsing threads may finish after the window closes. Leave
        # SQLite open until process teardown so their error logs remain safe.
        if mutex:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))
