from __future__ import annotations

import hashlib
import tkinter as tk
from tkinter import ttk

from .model import UserError, format_size
from .widgets import Tooltip

MARKS = {"checked": "☑", "unchecked": "☐", "partial": "▣", "loading": "◌"}


class RecordingBrowser:
    """Lazy native hierarchy, persistent checkboxes, and Explorer-style row selection."""

    def __init__(self, parent, owner):
        self.owner = owner
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.view = ttk.Treeview(self.frame, columns=("size",), show="tree headings", selectmode="extended", height=8)
        self.view.heading("#0", text="Folder or recording", anchor="w")
        self.view.heading("size", text="Details", anchor="w")
        widths = owner.state.get("column_widths", {})
        self.view.column("#0", width=max(280, int(widths.get("title", 450))), minwidth=280, stretch=True)
        self.view.column("size", width=max(110, int(widths.get("size", 155))), minwidth=110, stretch=False)
        self.view.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(self.frame, orient="vertical", command=self.view.yview).grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(self.frame, orient="horizontal", command=self.view.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.view.configure(yscrollcommand=self._scroll, xscrollcommand=horizontal.set)
        self.vertical = self.frame.grid_slaves(row=0, column=1)[0]
        self.rows = {}
        self.children = {}
        self.expanded = set()
        self.pending = {}
        self.errors = {}
        self.visible_ids = []
        self.anchor = ""
        self.suspend = False
        self.tip_row = ""
        self.spin_frame = 0
        self.spin_timer = None
        self.collapsed_search = set()
        self.positions = {}
        self.context = None
        self.keyboard_focus = False
        self.painted_focus = ''
        self.tooltip = Tooltip(self.view, lambda: self.rows[self.tip_row].title if self.tip_row in self.rows else "")
        self.view.tag_configure("checked", background="#f7ede5")
        self.view.tag_configure("unavailable", foreground="#777e77")
        self.view.bind("<Button-1>", self.click)
        self.view.bind("<Double-1>", self.open)
        self.view.bind("<space>", self.space)
        self.view.bind("<Return>", self.open)
        self.view.bind("<Control-a>", self.all)
        self.view.bind("<Control-A>", self.all)
        self.view.bind("<Motion>", self.motion, add=True)
        for key in ("Up", "Down", "Home", "End", "Prior", "Next", "Left", "Right"):
            self.view.bind(f"<{key}>", self.key)
        self.view.bind('<Alt-Up>',lambda _:self.alt_navigation('up'))
        self.view.bind('<Alt-Left>',lambda _:self.alt_navigation('back'))

    def alt_navigation(self, action):
        getattr(self.owner,action)()
        return 'break'

    def paint_focus(self):
        old=self.painted_focus
        if old and self.view.exists(old):
            self.view.item(old,tags=tuple(t for t in self.view.item(old,'tags') if t!='keyboard_focus'))
        node=self.view.focus()
        self.painted_focus=node if self.keyboard_focus and node in self.visible_ids else ''
        if self.painted_focus:
            tags=tuple(t for t in self.view.item(node,'tags') if t!='keyboard_focus')
            self.view.item(node,tags=('keyboard_focus',)+tags)

    def focus_only(self,node):
        if node not in self.visible_ids:
            return
        self.keyboard_focus=True
        self.view.selection_set(())
        self.view.focus(node)
        self.anchor=node
        self.paint_focus()
        self.view.see(node)

    def checkbox(self, state):
        name = f'spinner-{self.spin_frame}' if state == 'loading' else 'check-' + state
        return self.owner.icons.get(name, '')

    def animate(self):
        self.spin_timer = None
        if self.owner.closing or not self.view.winfo_exists():
            return
        self.spin_frame = (self.spin_frame + 1) % 8
        active = False
        for node, entry in self.rows.items():
            if self.owner.selected().state(entry) == 'loading':
                self.view.item(node, image=self.checkbox('loading'))
                active = True
        if active:
            self.spin_timer = self.owner.root.after(85, self.animate)

    def message(self, value):
        if value and not self.rows:
            self.view.insert('', 'end', text=value, tags=('unavailable',))

    def collapse_all(self):
        self.expanded.clear()
        self.collapsed_search=set(self.children)
        for node in self.view.get_children():
            if node in self.rows and self.rows[node].key == getattr(self.owner, 'root_key', None):
                self.expanded.add(node)
                self.collapsed_search.discard(node)
        self.owner.render_files()

    def _scroll(self, first, last):
        self.vertical.set(first, last)

    def iid(self, parent, entry):
        return hashlib.sha256((parent + "|" + entry.key).encode()).hexdigest()[:24]

    def render(self, roots, query="", selected_only=False):
        if query!=getattr(self,'query',''):
            self.collapsed_search.clear()
        self.query=query
        focus = self.view.focus()
        highlighted = set(self.view.selection())
        scroll = self.view.yview()[0] if self.view.get_children() else 0
        if focus in self.rows and self.context is not None:
            self.positions[self.context] = dict(key=self.rows[focus].key,
                index=self.visible_ids.index(focus) if focus in self.visible_ids else 0,
                scroll=scroll, was_visible=bool(self.view.bbox(focus)))
        self.suspend = True
        self.view.delete(*self.view.get_children())
        self.rows = {}
        self.visible_ids = []
        selection = self.owner.selected()
        root_key = "selected:" + self.owner.source if selected_only else (self.owner.collection.url if self.owner.collection else "")
        context=(self.owner.source,root_key)

        def matches(entry, node):
            if query in entry.title.casefold():
                return True
            return any(matches(child, self.iid(node, child)) for child in self.children.get(node, []))

        def known_members(entry,node):
            if not entry.container:
                return {entry.key}
            if node not in self.children:
                return None
            result=set()
            for child in self.children[node]:
                members=known_members(child,self.iid(node,child))
                if members is None:
                    return None
                result.update(members)
            return result

        def add(parent, parent_key, entries, ancestors=()):
            for entry in entries:
                node = self.iid(parent_key, entry)
                if entry.key in ancestors or query and not matches(entry, node):
                    continue
                members=known_members(entry,node) if entry.container else None
                if members is not None:
                    selection.members[entry.key]=members
                state = selection.state(entry)
                if entry.container:
                    detail = (f"Finding recordings… {getattr(self.owner, 'discovery_counts', {}).get(entry.key, 0):,} found"
                              if state == 'loading' else "Loading…" if node in self.pending else "Folder" if entry.kind == "folder" else "Playlist")
                elif not entry.available:
                    detail = "Unavailable"
                else:
                    details = [f"{entry.duration/60:.0f} min"] if entry.duration else []
                    size = entry.size_for(self.owner.quality.get())
                    if size:
                        details.append(("≈ " if entry.source == "youtube" else "") + format_size(size))
                    detail = " · ".join(details) or "Original MP3"
                opened = (node in self.expanded or bool(query and node in self.children)) and node not in self.collapsed_search
                image = self.checkbox(state)
                self.view.insert(parent, "end", iid=node, text=("" if image else MARKS[state] + "  ") + entry.title, image=image,
                    values=(detail,), open=opened, tags=("checked",) if state == "checked" else ("unavailable",) if not entry.available else ())
                self.rows[node] = entry
                selection.parents[entry.key]=set(ancestors)
                if entry.container:
                    if node in self.children:
                        add(node, node, self.children[node], ancestors + (entry.key,))
                    else:
                        self.view.insert(node, "end", iid=node + "-dummy", text=self.errors.get(node) or ("Loading…" if node in self.pending else "Expand to load"),tags=('unavailable',))
                    if node in self.children and not self.children[node]:
                        self.view.insert(node,'end',text='No recordings in this collection.',tags=('unavailable',))

        add("", root_key, roots)

        def visible(parent=""):
            for node in self.view.get_children(parent):
                if node in self.rows:
                    self.visible_ids.append(node)
                    if self.view.item(node, "open"):
                        visible(node)

        visible()
        valid = highlighted & self.rows.keys()
        if valid:
            self.view.selection_set(list(valid))
        point=self.positions.get(context)
        restored=focus if focus in self.rows else ''
        if not restored and point:
            restored=next((n for n,e in self.rows.items() if e.key==point['key']),'')
        while restored and restored not in self.visible_ids:
            restored=self.view.parent(restored)
        if not restored and point and self.visible_ids:
            restored=self.visible_ids[min(point['index'],len(self.visible_ids)-1)]
        if restored:
            self.view.focus(restored)
        self.view.yview_moveto(point['scroll'] if point else scroll if context==self.context else 0)
        if restored and point and (point['was_visible'] or restored!=focus):
            self.view.see(restored)
        if not self.owner.loading:
            self.context=context
        self.paint_focus()
        self.suspend = False
        if selection.loading and self.spin_timer is None:
            self.spin_timer = self.owner.root.after(85, self.animate)
        return [self.rows[node] for node in self.visible_ids]

    def expand(self, node, collapse=False):
        if node not in self.rows or not self.rows[node].container:
            return
        if collapse or self.view.item(node,'open'):
            self.expanded.discard(node)
            if getattr(self,'query',''):
                self.collapsed_search.add(node)
            self.owner.render_files()
            return
        self.expanded.add(node)
        self.collapsed_search.discard(node)
        self.errors.pop(node,None)
        if node in self.children or node in self.pending:
            self.owner.render_files()
            return
        import threading
        token = threading.Event()
        self.pending[node] = token
        entry = self.rows[node]
        source, mode = entry.source, self.owner.mode.get()

        def done(collection):
            self.pending.pop(node, None)
            if token.is_set() or self.owner.closing:
                return
            self.children[node] = collection.entries
            if source == self.owner.source:
                self.owner.render_files()

        def failed(error):
            self.pending.pop(node, None)
            if not token.is_set():
                self.errors[node]=str(error) if isinstance(error,UserError) else 'Could not load. Collapse and expand to retry.'
                self.owner.render_files()
                self.owner.error(error)
                self.owner.notice.configure(text='')

        self.owner.submit(lambda: self.owner.fetch(entry.url, source, mode, token), done, failed)
        self.owner.render_files()

    def minimal(self, nodes):
        result = set(nodes)
        for node in nodes:
            parent = self.view.parent(node)
            while parent:
                if parent in nodes:
                    result.discard(node)
                    break
                parent = self.view.parent(parent)
        return result

    def select(self, node, ctrl=False, shift=False, click=False):
        if node not in self.rows:
            return
        self.keyboard_focus=False
        current = set(self.view.selection())
        if shift and self.anchor in self.visible_ids and node in self.visible_ids:
            a, b = sorted((self.visible_ids.index(self.anchor), self.visible_ids.index(node)))
            chosen = set(self.visible_ids[a:b+1]) | (current if ctrl else set())
        elif ctrl or click and self.owner.selected().state(self.rows[node]) in ('checked', 'loading'):
            checked = self.owner.selected().state(self.rows[node]) in ('checked', 'loading')
            chosen = (current - {node}) if checked else (current | {node})
            self.anchor = node
        else:
            chosen = {node}
            self.anchor = node
        self.view.focus(node)
        self.view.selection_set(list(chosen))
        self.view.see(node)
        if not self.owner.locked():
            if ctrl or click and not shift and node not in chosen:
                self.owner.toggle(self.rows[node], node in chosen, render=False)
            else:
                # Clearing the previous visible group includes parent intentions,
                # even when their loaded descendants are currently collapsed.
                removed = current - chosen
                for key in self.minimal(removed):
                    if key in self.rows:
                        self.owner.toggle(self.rows[key], False, render=False)
                for key in self.minimal(chosen):
                    if self.owner.selected().state(self.rows[key]) not in ('checked', 'loading'):
                        self.owner.toggle(self.rows[key], True, render=False)
        self.owner.render_files()

    def click(self, event):
        node = self.view.identify_row(event.y)
        if node not in self.rows:
            return
        self.view.focus_set()
        element = self.view.identify_element(event.x, event.y)
        if "indicator" in element:
            self.expand(node)
            return "break"
        if event.state & (4|1):
            self.select(node,bool(event.state & 4),bool(event.state & 1),click=True)
            return 'break'
        # Checkbox sits immediately after the native expansion indicator.
        depth, parent = 0, self.view.parent(node)
        while parent:
            depth += 1
            parent = self.view.parent(parent)
        box = self.view.bbox(node, "#0")
        check_x = box[0] + 20 * (depth + 1) if box else -100
        if self.view.identify_column(event.x) == "#0" and check_x <= event.x <= check_x + 21:
            loading=self.owner.selected().state(self.rows[node])=='loading'
            group = self.view.selection() if not loading and node in self.view.selection() else (node,)
            desired = self.owner.selected().state(self.rows[node]) not in ("checked", "loading")
            for key in group:
                if key in self.rows:
                    self.owner.toggle(self.rows[key], desired, render=False)
            self.view.focus(node)
            if desired:
                self.view.selection_set(group)
            else:
                self.view.selection_remove(group)
            self.owner.render_files()
        else:
            self.select(node, bool(event.state & 4), bool(event.state & 1), click=True)
        return "break"

    def space(self, event=None):
        node=self.view.focus()
        if node not in self.rows:
            return 'break'
        self.focus_only(node)
        self.owner.toggle(self.rows[node],render=False)
        self.owner.render_files()
        return "break"

    def all(self, event=None):
        nodes=self.shown_selection()
        self.view.selection_set(list(nodes))
        for node in self.minimal(nodes):
            self.owner.toggle(self.rows[node], True, render=False)
        self.owner.render_files()
        return "break"

    def shown_selection(self):
        query=getattr(self,'query','')
        return {n for n in self.visible_ids if not query or
                (self.rows[n].key!=getattr(self.owner,'root_key',None) and query in self.rows[n].title.casefold())}

    def open(self, event=None):
        if event and getattr(event,"keysym","")!="Return" and "indicator" in self.view.identify_element(event.x,event.y):
            return "break"
        node = self.view.identify_row(event.y) if event and getattr(event, "keysym", "") != "Return" else self.view.focus()
        if node in self.rows and self.rows[node].container:
            if self.rows[node].key == getattr(self.owner,'root_key',None):
                self.expand(node)
                return 'break'
            self.owner.load(self.rows[node].url)
        return "break"

    def key(self, event):
        node = self.view.focus()
        if not self.visible_ids:
            return "break"
        new_focus=node not in self.visible_ids
        if new_focus:
            node = self.visible_ids[0]
            if event.keysym in ("Up","Down"):
                self.focus_only(node);return "break"
        ctrl, shift = bool(event.state & 4), bool(event.state & 1)
        if event.keysym == "Right":
            if self.rows[node].container and not self.view.item(node, "open"):
                self.focus_only(node)
                self.expand(node)
        elif event.keysym == "Left":
            if self.rows[node].container and self.view.item(node, "open"):
                self.focus_only(node)
                self.expand(node, collapse=True)
        else:
            index = self.visible_ids.index(node)
            step = max(1, self.view.winfo_height() // 30 - 1)
            target = {"Up": index-1, "Down": index+1, "Home": 0, "End": len(self.visible_ids)-1,
                      "Prior": index-step, "Next": index+step}.get(event.keysym, index)
            next_node = self.visible_ids[max(0, min(len(self.visible_ids)-1, target))]
            if shift:
                self.select(next_node, ctrl, shift)
            else:
                self.focus_only(next_node)
        return "break"

    def motion(self, event):
        node = self.view.identify_row(event.y)
        if node != self.tip_row:
            self.tip_row = node
            self.tooltip.schedule()

    def cancel(self):
        for event in self.pending.values():
            event.set()
        self.pending.clear()
