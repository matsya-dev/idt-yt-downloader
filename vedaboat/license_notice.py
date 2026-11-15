"""One-time agreement to the conditions bundled with Windows CPython."""
import hashlib
import tkinter as tk
from tkinter import ttk

from . import APP_NAME
from .tools import application_directory


def ensure_runtime_terms(root, state):
    path = application_directory() / 'third-party' / 'Python-Windows-CRT-license.txt'
    text = path.read_text(encoding='utf-8-sig')
    signature = hashlib.sha256(text.encode('utf8')).hexdigest()
    if state.get('runtime_terms_accepted') == signature:
        return True
    if show_runtime_terms(root, text):
        state.put('runtime_terms_accepted', signature)
        return True
    return False


def show_runtime_terms(root, text):
    accepted = False
    window = tk.Toplevel(root)
    window.title(APP_NAME + ' — Runtime license conditions')
    width, height = min(680, root.winfo_screenwidth() - 80), min(500, root.winfo_screenheight() - 120)
    window.geometry(f'{width}x{height}+{(root.winfo_screenwidth()-width)//2}+{(root.winfo_screenheight()-height)//2}')
    window.resizable(False, False)
    ttk.Style(window).theme_use('clam')
    frame = ttk.Frame(window, padding=16)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Please review these one-time runtime conditions.', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='These apply only to the Microsoft components included with Python.\nThe app and other open-source components keep their own licenses.', wraplength=620).pack(anchor='w', pady=(8, 12))
    body = ttk.Frame(frame)
    body.pack(fill='both', expand=True)
    scroll = ttk.Scrollbar(body)
    scroll.pack(side='right', fill='y')
    box = tk.Text(body, wrap='word', relief='solid', borderwidth=1, padx=10, pady=8,
                  bg='#f7f7f5', fg='#252925',
                  font=('Segoe UI', 9), yscrollcommand=scroll.set)
    box.insert('1.0', text)
    box.configure(state='disabled')
    box.pack(fill='both', expand=True)
    scroll.configure(command=box.yview)
    actions = ttk.Frame(frame)
    actions.pack(fill='x', pady=(12, 0))

    def agree():
        nonlocal accepted
        accepted = True
        window.destroy()

    ttk.Button(actions, text='Exit', command=window.destroy).pack(side='left')
    ttk.Button(actions, text='Agree and open', command=agree).pack(side='right')
    from .theme import apply_theme, system_is_dark
    apply_theme(window, system_is_dark())
    window.protocol('WM_DELETE_WINDOW', window.destroy)
    window.grab_set()
    window.focus_set()
    root.wait_window(window)
    return accepted
