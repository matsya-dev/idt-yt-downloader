"""Compact three-step layout: flexible browser above two short action sections."""
import tkinter as tk
import base64
from tkinter import ttk

from .browser import RecordingBrowser
from .tools import application_directory
from .widgets import Tooltip
from .breadcrumbs import Breadcrumbs
from . import APP_NAME


def build_layout(a):
    a.icons = {}
    a.icon_widgets = []
    for path in (application_directory() / "assets" / "toolbar").glob("*.png"):
        a.icons[path.stem] = tk.PhotoImage(master=a.root,data=base64.b64encode(path.read_bytes()).decode('ascii'))

    def icon(parent, text, name, action, primary=False):
        button = ttk.Button(parent, text=text, command=action,
            style="Primary.Icon.TButton" if primary else "Icon.TButton", width=0)
        if name in a.icons:
            button.configure(image=a.icons[name], compound="image")
            a.icon_widgets.append((button, name))
        Tooltip(button, lambda: button["text"])
        return button

    a.icon_button = icon
    a.root.columnconfigure(0, weight=1)
    a.root.rowconfigure(2, weight=1)
    header = tk.Frame(a.root, bg="#f7f7f5", padx=14, pady=6)
    header.grid(row=0, column=0, sticky="ew")
    path = application_directory()/"assets"/"app-icon.png"
    if path.exists():
        a.header_icon = tk.PhotoImage(master=a.root,data=base64.b64encode(path.read_bytes()).decode('ascii')).subsample(8,8)
        tk.Label(header, image=a.header_icon, bg="#f7f7f5").pack(side="left", padx=(0,9))
    tk.Label(header, text=APP_NAME, bg="#f7f7f5", fg="#252925", font=("Segoe UI",15,"bold")).pack(side="left")
    tk.Label(header, text="Audio Downloader", bg="#f7f7f5", fg="#60665f", font=("Segoe UI",9)).pack(side="left", padx=12)
    ttk.Button(header,text="Settings",style="Quiet.TButton",command=a.settings).pack(side="right")
    ttk.Button(header,text="Help",style="Quiet.TButton",command=a.help).pack(side="right",padx=4)
    tabs = tk.Frame(a.root,bg="#f7f7f5",padx=14)
    tabs.grid(row=1,column=0,sticky="ew")
    a.tab_buttons={}
    for source,title in (("tree","Desire Tree Audio"),("youtube","YouTube → MP3")):
        button=ttk.Button(tabs,text=title,style="Tab.TButton",command=lambda s=source:a.switch_source(s))
        button.pack(side="left");a.tab_buttons[source]=button

    section=ttk.Frame(a.root,padding=(14,7))
    section.grid(row=2,column=0,sticky="nsew")
    section.columnconfigure(0,weight=1);section.rowconfigure(2,weight=1)
    ttk.Label(section,text="1. Choose recordings",font=("Segoe UI",11,"bold")).grid(row=0,column=0,sticky="w",pady=(0,5))
    links=ttk.Frame(section);links.grid(row=1,column=0,sticky="ew",pady=(0,6));links.columnconfigure(0,weight=1)
    # Import after the module has loaded: HintEntry belongs to the main window.
    from .ui import HintEntry
    a.link=HintEntry(links,hint="Paste a Desire Tree folder or MP3 link…")
    a.link.grid(row=0,column=0,sticky="ew")
    a.link.bind("<Return>",lambda _:a.open_link())
    a.open_link_button=icon(links,"Open link","open",a.open_link)
    a.open_link_button.grid(row=0,column=1,padx=(5,0))
    a.panes=ttk.Panedwindow(section,orient="horizontal")
    a.panes.grid(row=2,column=0,sticky="nsew")
    a.sidebar=ttk.Frame(a.panes,width=165)
    content=ttk.Frame(a.panes,padding=(8,0,0,0))
    a.panes.add(a.sidebar,weight=0);a.panes.add(content,weight=1)
    a.root.after_idle(lambda:a.panes.sashpos(0,max(120,min(240,a.state.get("sidebar_width",165)))))
    content.columnconfigure(0,weight=1);content.rowconfigure(3,weight=1,minsize=145)
    nav=ttk.Frame(content);nav.grid(row=0,column=0,sticky="ew",pady=(0,3))
    for title,key,action in (("Home","home",a.home),("Back · Alt+Left","back",a.back)):
        icon(nav,title,key,action).pack(side="left",padx=(0,2))
    a.collapse_button=icon(nav,"Collapse all","collapse",lambda:a.browser.collapse_all())
    a.collapse_button.pack(side="left",padx=(0,5))
    a.select_all_check=ttk.Checkbutton(nav,text="Select all shown",variable=a.select_all_var,command=a.select_all)
    a.select_all_check.pack(side="left",padx=(0,5))
    icon(nav,"Refresh · F5","refresh",lambda:a.load(a.current_url(),force=True,history=False)).pack(side="right")
    a.location=a.label(nav,"Loading…",muted=True,width=1,anchor="w")
    Tooltip(a.location,lambda:a.collection.title if a.collection else "")
    a.youtube_modes=ttk.Frame(nav)
    a.mode_buttons={}
    for value,text in (("videos","Videos"),("playlists","Playlists")):
        button=ttk.Button(a.youtube_modes,text=text,style="Tab.TButton",command=lambda v=value:a.choose_mode(v))
        button.pack(side="left",padx=2);a.mode_buttons[value]=button
    a.youtube_modes.pack(side="right",padx=5)
    if a.source=="tree":a.youtube_modes.pack_forget()
    a.breadcrumbs=Breadcrumbs(content,a)
    a.breadcrumbs.grid(row=1,column=0,sticky="ew",pady=(0,4))
    controls=ttk.Frame(content);controls.grid(row=2,column=0,sticky="ew",pady=(0,5));controls.columnconfigure(0,weight=1)
    a.search_box=HintEntry(controls,hint="Search titles in this collection…",textvariable=a.search)
    a.search_box.grid(row=0,column=0,sticky="ew")
    a.search_box.bind("<Escape>",lambda _:a.search_box.set())
    a.selected_button=ttk.Button(controls,text="Show selected",style="Quiet.TButton",command=a.show_selected)
    a.selected_button.grid(row=0,column=1,padx=3)
    listing=ttk.Frame(content);listing.grid(row=3,column=0,sticky="nsew");listing.columnconfigure(0,weight=1);listing.rowconfigure(0,weight=1,minsize=120)
    a.browser=RecordingBrowser(listing,a);a.browser.frame.grid(row=0,column=0,sticky="nsew")
    a.files=a.browser.view
    listfoot=ttk.Frame(listing);listfoot.grid(row=1,column=0,sticky="ew",pady=(4,0))
    a.clear_button=ttk.Button(listfoot,text="Clear selection",style="Quiet.TButton",command=a.clear_selection)
    a.clear_button.pack(side='left',padx=(8,0))
    counts=ttk.Frame(listfoot);counts.pack(side='right')
    a.count=a.label(counts,"",muted=True);a.count.pack(side='left')
    a.label(counts,' · ',muted=True).pack(side='left')
    a.selection_label=a.label(counts,'0 selected',muted=True);a.selection_label.pack(side='left')
    Tooltip(a.selection_label,'Selected recordings across this source, including hidden search results and other folders.')
    a.notice=a.label(section,"",muted=True,wraplength=950)
    a.notice.grid(row=3,column=0,sticky="ew",pady=(3,0))

    tk.Frame(a.root,bg="#e2e5de",height=1).grid(row=3,column=0,sticky="ew")
    folder=ttk.Frame(a.root,padding=(14,7));folder.grid(row=4,column=0,sticky="ew");folder.columnconfigure(1,weight=1)
    ttk.Label(folder,text="2. Choose download folder",font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w",padx=(0,12))
    a.destination_label=a.label(folder,"No folder chosen",muted=True,width=1,anchor="w")
    a.destination_label.grid(row=0,column=1,sticky="ew")
    Tooltip(a.destination_label,lambda:a.destination.get() or "No folder chosen")
    a.folder_button=ttk.Button(folder,text="Choose folder…",command=a.choose_folder)
    a.folder_button.grid(row=0,column=2,padx=(8,0))
    tk.Frame(a.root,bg="#e2e5de",height=1).grid(row=5,column=0,sticky="ew")
    download=ttk.Frame(a.root,padding=(14,7));download.grid(row=6,column=0,sticky="ew");download.columnconfigure(1,weight=1)
    ttk.Label(download,text="3. Download recordings",font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w",padx=(0,12))
    a.summary=a.label(download,"Choose recordings to begin",width=1,anchor="w")
    a.summary.grid(row=0,column=1,sticky="ew")
    Tooltip(a.summary,lambda:a.summary["text"])
    a.main_button=icon(download,"Download","download-white",a.download,primary=True)
    a.main_button.grid(row=0,column=2,padx=(8,0))
    a.status_label=ttk.Label(download,textvariable=a.status,style="Muted.TLabel",wraplength=700)
    a.status_label.grid(row=1,column=0,columnspan=2,sticky="w",pady=(3,0))
    actions=ttk.Frame(download);actions.grid(row=1,column=2,sticky="e")
    a.open_folder_button=ttk.Button(actions,text="Open download folder",style="Quiet.TButton",command=a.open_folder)
    a.retry_button=ttk.Button(actions,text="Retry failed",style="Quiet.TButton",command=a.retry_failed)
    a.details_button=ttk.Button(actions,text="Details…",style="Quiet.TButton",command=a.details)
    a.bar=ttk.Progressbar(download,maximum=100,mode="determinate")
    a.bar.grid(row=2,column=0,columnspan=3,sticky="ew",pady=(5,0))
    a.footer=tk.Label(a.root,text="Manual downloads",bg="#f7f7f5",fg="#60665f",font=("Segoe UI",9),padx=14,pady=3,anchor="w")
    a.footer.grid(row=7,column=0,sticky="ew")
    a.root.bind("<Alt-Left>",lambda _:a.back())
    a.root.bind("<Alt-Up>",lambda _:a.up())
    a.root.bind("<F5>",lambda _:a.load(a.current_url(),force=True,history=False))
    def focus_link(_):
        a.link.focus_set();a.link._focus();a.link.selection_range(0,"end");return "break"
    a.root.bind("<Control-l>",focus_link)
    a.root.bind("<Control-L>",focus_link)
    def resize(event):
        if event.widget is a.root and not a.closing and a.status_label.winfo_exists():
            a.status_label.configure(wraplength=max(300,event.width-180))
            a.notice.configure(wraplength=max(300,event.width-35))
    a.root.bind("<Configure>",resize,add=True)
