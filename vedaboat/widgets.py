"""Small native UI helpers, with no additional runtime dependency."""
import tkinter as tk


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text = widget, text
        self.timer = None
        self.window = None
        widget.bind("<Enter>", self.schedule, add=True)
        widget.bind("<FocusIn>", self.schedule, add=True)
        for event in ("<Leave>", "<FocusOut>", "<ButtonPress>", "<Destroy>"):
            widget.bind(event, self.hide, add=True)

    def schedule(self, *_):
        self.hide()
        self.timer = self.widget.after(650, self.show)

    def show(self):
        self.timer = None
        value = self.text() if callable(self.text) else self.text
        if not value or not self.widget.winfo_exists():
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.title(value)
        colors = getattr(self.widget.winfo_toplevel(), 'vedaboat_colors', {'soft':'#fff9ed', 'text':'#252925'})
        tk.Label(self.window, text=value, bg=colors['soft'], fg=colors['text'], relief="solid", borderwidth=1,
                 padx=9, pady=5, wraplength=620, font=("Segoe UI", 9)).pack()
        self.window.update_idletasks()
        x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth() - self.window.winfo_reqwidth() - 8)
        y = min(self.widget.winfo_rooty() + self.widget.winfo_height() + 4,
                self.widget.winfo_screenheight() - self.window.winfo_reqheight() - 8)
        self.window.geometry(f"+{max(0,x)}+{max(0,y)}")

    def hide(self, *_):
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        if self.window:
            self.window.destroy()
            self.window = None
