"""Developer verification entry point for the frozen runtime, outside the GUI."""
import json
import os
import traceback
import wave
from pathlib import Path

from .model import TREE_HOME
from .sources import DesireTree
from .state import State
from .tools import Tools, application_directory, run_process
from . import APP_NAME


def self_test(report_path: Path, network=False):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    work = report_path.parent / "self-test"
    work.mkdir(exist_ok=True)
    report = {}
    state = State(work / "state")
    tools = Tools(state.directory)

    def check(key, fn):
        try:
            report[key] = {"ok": True, "result": fn()}
        except Exception:
            report[key] = {"ok": False, "error": traceback.format_exc()}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    check("sqlite", lambda: (state.put("verified", True), state.get("verified"))[1])
    def tool_check(args):
        code,output=run_process(args,timeout=60)
        if code:
            raise RuntimeError(output[-2000:])
        return output
    check("yt_dlp", lambda: tool_check([str(tools.path("yt-dlp")), "--version"]))
    check("javascript", lambda: tool_check([str(tools.path("qjs")), "-e", f"console.log('{APP_NAME}')"]))

    def interface():
        import tkinter as tk
        from .ui import App
        from .model import Collection,Entry
        root=tk.Tk();root.withdraw()
        original=App.load
        App.load=lambda *_args,**_kwargs:None
        app=None
        try:
            app=App(root,state)
            assert root.title()==APP_NAME
            assert app.theme_mode.get()=='System'
            app.collection=Collection('test:self-test','Test',[
                Entry('tree:/one.mp3','tree','audio','One','url',path='/one.mp3',size=100),
                Entry('tree:/two.mp3','tree','audio','Two','url',path='/two.mp3',size=100)],'tree')
            app.render_files();nodes=app.browser.visible_ids
            app.browser.focus_only(nodes[1])
            from types import SimpleNamespace
            app.browser.key(SimpleNamespace(keysym='Up',state=8))
            assert app.files.focus()==nodes[0] and not app.selected().entries
            app.theme_mode.set('Dark');app.set_theme();assert app.dark.get()
            app.settings()
            app.theme_mode.set('Light');app.set_theme();assert not app.dark.get()
            app.theme_mode.set('System');app.set_theme()
            assert app.header_icon.width()>0
            app.licenses()
            assert any(isinstance(w, tk.Toplevel) and 'Licenses and source' in w.title() for w in root.winfo_children())
            assert (application_directory() / 'third-party' / 'LAME-license.txt').is_file()
            return dict(name=root.title(),theme=app.theme_mode.get(),arrows='focus only',icon='D3')
        finally:
            App.load=original
            if app:
                app.closing=True;app.executor.shutdown(wait=False,cancel_futures=True)
            root.destroy()
    check('native_interface',interface)

    def convert(quality=128):
        source = work / "বাংলা భక్తి.wav"
        output = work / f"বাংলা భక్తి {quality}.mp3"
        with wave.open(str(source), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(22050)
            stream.writeframes(b"\0\0" * 22050)
        output.unlink(missing_ok=True)
        tools.convert(source, output,quality=quality)
        return tools.probe(output)

    check("mp3_conversion", convert)
    check("mp3_conversion_320",lambda:convert(320))
    def decode_formats():
        import base64
        from .diagnostic_samples import SAMPLES
        results = {}
        for extension, encoded in SAMPLES.items():
            source = work / ('generated.' + extension)
            target = work / ('decoded-' + extension + '.mp3')
            source.write_bytes(base64.b64decode(encoded))
            target.unlink(missing_ok=True)
            tools.convert(source, target, quality=128)
            probe = tools.probe(target)
            if probe['streams'][0]['codec_name'] != 'mp3':
                raise RuntimeError('Decoder conversion failed: ' + extension)
            results[extension] = 'decoded and converted'
        return results
    check('audio_formats', decode_formats)
    check("approved_icon",lambda:(application_directory()/"assets"/"icon-choice.txt").read_text(encoding="utf-8").strip())
    if network:
        import certifi
        import ssl
        import socket
        report["tls_paths"] = {"ok": True, "result": {"certifi": certifi.where(), "exists": Path(certifi.where()).exists(),
            "default": str(ssl.get_default_verify_paths()), "openssl": ssl.OPENSSL_VERSION}}

        def tls():
            context = ssl.create_default_context(cafile=certifi.where())
            with socket.create_connection(("audio.iskcondesiretree.com", 443), timeout=15) as conn:
                with context.wrap_socket(conn, server_hostname="audio.iskcondesiretree.com") as secured:
                    return secured.version()

        check("tls", tls)
        check("desire_tree", lambda: [e.title for e in DesireTree().browse(TREE_HOME).entries])
    state.close()
    return all(item["ok"] for item in report.values())
