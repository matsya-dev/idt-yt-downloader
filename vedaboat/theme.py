"""Small shared palettes for native Tk and ttk widgets."""
import tkinter as tk
import os
from tkinter import ttk

LIGHT = dict(bg='#ffffff', soft='#f7f7f5', line='#e2e5de', text='#252925', muted='#60665f',
             warm='#8e4b30', selected='#f7ede5', error='#a12d2d', disabled='#999e98', accent='#713a25', focus='#E4EDF6')
DARK = dict(bg='#202427', soft='#292f33', line='#485156', text='#f1f0e9', muted='#bdc5c4',
            warm='#bd713c', selected='#53402f', error='#ff9393', disabled='#8f999e', accent='#f3bc8c', focus='#314A5A')

THEME_OPTIONS=('System','Light','Dark')


def theme_choice(value):
    return next((mode for mode in THEME_OPTIONS if mode.casefold()==str(value).casefold()),'System')


def system_is_dark():
    """Read Windows' app theme preference without changing any system setting."""
    if os.name!='nt':
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            value,_=winreg.QueryValueEx(key,'AppsUseLightTheme')
        return value==0
    except OSError:
        return False


def apply_theme(root, dark):
    c = DARK if dark else LIGHT
    root.vedaboat_colors = c
    style = ttk.Style(root)
    style.configure('.', background=c['bg'], foreground=c['text'])
    for name in ('TFrame', 'TLabel', 'TCheckbutton', 'TRadiobutton', 'TPanedwindow'):
        style.configure(name, background=c['bg'], foreground=c['text'])
    style.configure('Muted.TLabel', foreground=c['muted'])
    style.configure('TButton', background=c['bg'], foreground=c['text'], bordercolor=c['line'], focuscolor=c['warm'])
    style.map('TButton', background=[('active', c['soft'])], foreground=[('disabled', c['disabled'])])
    style.configure('Quiet.TButton', foreground=c['muted'])
    style.configure('Icon.TButton', background=c['bg'])
    for name in ('Primary.TButton', 'Primary.Icon.TButton'):
        style.configure(name, background=c['warm'], foreground='#ffffff')
        style.map(name, background=[('disabled', c['line']), ('active', c['warm'])], foreground=[('disabled', c['muted'])])
    style.configure('Tab.TButton', background=c['soft'], foreground=c['muted'])
    style.configure('Active.Tab.TButton', background=c['selected'], foreground=c['accent'])
    style.map('Active.Tab.TButton', background=[('active', c['selected'])])
    for name in ('TEntry', 'TCombobox', 'TSpinbox'):
        style.configure(name, fieldbackground=c['bg'], foreground=c['text'], bordercolor=c['line'],
                        selectbackground=c['selected'], selectforeground=c['text'], insertcolor=c['text'], arrowcolor=c['text'])
        style.map(name, fieldbackground=[('readonly', c['soft'])], foreground=[('readonly', c['text']), ('disabled', c['disabled'])])
    for name in ('TCheckbutton', 'TRadiobutton'):
        style.configure(name, indicatorbackground=c['soft'], indicatorforeground=c['text'])
        style.map(name, background=[('active', c['bg'])], foreground=[('disabled', c['disabled'])],
                  indicatorbackground=[('selected', c['warm']), ('alternate', c['warm']), ('active', c['selected'])])
    style.configure('Treeview', background=c['bg'], fieldbackground=c['bg'], foreground=c['text'])
    style.configure('Treeview.Heading', background=c['soft'], foreground=c['muted'])
    style.map('Treeview', background=[('selected', c['selected'])], foreground=[('selected', c['text'])])
    style.configure('Horizontal.TProgressbar', background=c['warm'], troughcolor=c['soft'])
    for name in ('Vertical.TScrollbar', 'Horizontal.TScrollbar'):
        style.configure(name, background=c['line'], troughcolor=c['soft'], arrowcolor=c['muted'],
                        bordercolor=c['soft'], lightcolor=c['line'], darkcolor=c['line'])
        style.map(name, background=[('active',c['muted']),('!active',c['line'])])
    root.option_add('*TCombobox*Listbox.background', c['soft'])
    root.option_add('*TCombobox*Listbox.foreground', c['text'])
    root.option_add('*TCombobox*Listbox.selectBackground', c['selected'])
    root.option_add('*TCombobox*Listbox.selectForeground', c['text'])
    mapping = {LIGHT[k].lower(): c[k] for k in LIGHT}
    mapping.update({DARK[k].lower(): c[k] for k in DARK})

    def visit(widget):
        if isinstance(widget, ttk.Treeview):
            widget.tag_configure('checked', background=c['selected'])
            widget.tag_configure('unavailable', foreground=c['muted'])
            widget.tag_configure('keyboard_focus',background=c['focus'],foreground=c['text'])
        if isinstance(widget,ttk.Combobox):
            popup=widget.tk.call('ttk::combobox::PopdownWindow',str(widget))
            widget.tk.call(str(popup)+'.f.l','configure','-background',c['soft'],'-foreground',c['text'],
                           '-selectbackground',c['selected'],'-selectforeground',c['text'])
        if not isinstance(widget, ttk.Widget):
            options = widget.keys()
            for key in ('background', 'foreground', 'insertbackground', 'highlightbackground'):
                if key in options:
                    old = str(widget.cget(key)).lower()
                    if old in mapping:
                        widget.configure(**{key: mapping[old]})
            if isinstance(widget, tk.Text):
                widget.configure(selectbackground=c['selected'], selectforeground=c['text'])
            if isinstance(widget, (tk.Tk, tk.Toplevel)):
                widget.vedaboat_colors=c
                widget.configure(background=c['bg'])
                if widget.winfo_id() and __import__('os').name == 'nt':
                    try:
                        import ctypes
                        value = ctypes.c_int(bool(dark))
                        hwnd = ctypes.windll.user32.GetParent(widget.winfo_id())
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
                    except (OSError, AttributeError):
                        pass
        else:
            # Explicit label/placeholder colors also need to follow the palette.
            if 'foreground' in widget.keys():
                old = str(widget.cget('foreground')).lower()
                if old in mapping:
                    widget.configure(foreground=mapping[old])
        for child in widget.winfo_children():
            visit(child)
    visit(root)
    return c
