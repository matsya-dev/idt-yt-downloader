"""Clickable source paths with on-demand sibling menus."""
import re
import tkinter as tk
from tkinter import ttk

from .model import tree_path, tree_url, youtube_url
from .widgets import Tooltip


class Breadcrumbs(ttk.Frame):
    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.parts = []
        self.timer = None
        self.bind('<Configure>', self.resize)

    def resize(self, _=None):
        if self.timer:
            self.owner.root.after_cancel(self.timer)
        self.timer = self.owner.root.after(80, self.draw)

    def render(self):
        a = self.owner
        self.parts = []
        if a.loading:
            self.parts = [('Loading collection…', None)]
        elif a.collection:
            c = a.collection
            if c.source == 'tree':
                try:
                    path = tree_path(c.url)
                except Exception:
                    path = '/'
                self.parts = [('Desire Tree', tree_url('/'))]
                bits = path.strip('/').split('/') if path != '/' else []
                if bits and bits[0] in ('04_-_ISKCON_Matajis', '05_-_ISKCON_Chowpatty'):
                    self.parts.append(('More', tree_url('/06_-_More')))
                for i, bit in enumerate(bits):
                    title = re.sub(r'^\d+_-_', '', bit).replace('_', ' ')
                    self.parts.append((title, tree_url('/' + '/'.join(bits[:i+1]))))
            else:
                self.parts = [('YouTube', a.last_channel)]
                e = next(iter(c.entries), None)
                if e and e.channel_id:
                    self.parts.append((e.channel_title, 'https://www.youtube.com/channel/' + e.channel_id + '/' + a.mode.get()))
                if not self.parts or self.parts[-1][1] != c.url:
                    self.parts.append((c.title, c.url))
        self.draw()

    def draw(self):
        self.timer = None
        if self.owner.closing or not self.winfo_exists():
            return
        for widget in self.winfo_children():
            widget.destroy()
        parts = self.parts
        # Leave the full path available in the ellipsis menu on narrow windows.
        budget = max(160, self.winfo_width())
        estimated = sum(min(len(title), 28)*7+32 for title, _ in parts)
        if len(parts) > 2 and estimated > budget:
            hidden = parts[1:-1]
            parts = [parts[0], ('…', hidden), parts[-1]]
        for index, (title, url) in enumerate(parts):
            if isinstance(url, list):
                button = ttk.Button(self, text='…', style='Quiet.TButton', width=2,
                                    command=lambda p=url: self.ancestors(p))
            else:
                cap = max(12, min(32, (budget-110)//7)) if index == len(parts)-1 else 23
                short = title if len(title) <= cap else title[:cap-1] + '…'
                button = ttk.Button(self, text=short, style='Quiet.TButton', command=lambda u=url: self.owner.load(u) if u else None)
                Tooltip(button, title)
            button.pack(side='left')
            if index < len(parts)-1:
                arrow = ttk.Button(self, text='▾', style='Quiet.TButton', width=2,
                                   command=lambda u=url: self.siblings(u) if isinstance(u, str) else self.ancestors(u))
                arrow.pack(side='left')
                Tooltip(arrow, 'Choose a branch')

    def popup(self):
        c = self.owner.colors
        menu = tk.Menu(self, tearoff=False, bg=c['soft'], fg=c['text'], activebackground=c['selected'], activeforeground=c['text'])
        return menu

    def ancestors(self, parts):
        menu = self.popup()
        for title, url in parts:
            menu.add_command(label=title, command=lambda u=url: self.owner.load(u))
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def siblings(self, url):
        # A branch arrow lists children of that path, like Explorer breadcrumbs.
        menu = self.popup()
        menu.add_command(label='Loading branches…', state='disabled')
        source, mode = self.owner.source, self.owner.mode.get()
        def done(collection):
            if not menu.winfo_exists():
                return
            menu.delete(0, 'end')
            branches = [e for e in collection.entries if e.container]
            for entry in branches:
                menu.add_command(label=entry.title, command=lambda u=entry.url: self.owner.load(u))
            if not branches:
                menu.add_command(label='No subfolders or playlists', state='disabled')
        def fail(_):
            if menu.winfo_exists():
                menu.delete(0, 'end'); menu.add_command(label='Could not load. Try Refresh.', state='disabled')
        self.owner.submit(lambda: self.owner.fetch(url, source, mode), done, fail)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
