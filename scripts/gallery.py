#!/usr/bin/env python3
"""Shared browser-gallery helpers for the shot-list drivers.

One static file server + themed HTML builder used by storyboard.py,
video_shot.py, and video_post.py. (The FLUX.2 drivers keep their own copy in
flux2_common.py — different ComfyUI instance, different conventions.)

Each driver builds its own list of cards (a media file + a caption) and picks an
image/video layout in a light/dark theme; the free port, static server, browser
open, and the serve-and-wait loop all route through here.
"""
import http.server
import shutil
import socket
import socketserver
import subprocess
import threading
import time
from pathlib import Path

# Media render at NATURAL resolution (1:1 pixels) so detail can be judged
# honestly — no width:100% downscaling. Items flow and wrap; the page scrolls
# for media larger than the viewport.
_THEMES = {
    "light": (
        "body{background:#f6f3ee;color:#222;font:13px/1.4 -apple-system,system-ui,sans-serif;margin:1.5em;}"
        "header{border-bottom:1px solid #ccc;padding-bottom:.6em;margin-bottom:1.5em;}"
        ".grid{display:flex;flex-wrap:wrap;align-items:flex-start;gap:1.2em;}"
        "figure{margin:0;background:#fff;border:1px solid #bbb;box-shadow:0 1px 3px rgba(0,0,0,.08);display:flex;flex-direction:column;}"
        "img{display:block;width:auto;height:auto;max-width:none;border-bottom:1px solid #ccc;}"
        "figcaption{padding:.5em .7em;font-size:12px;color:#333;max-width:60ch;}"
        "footer{margin-top:2em;padding-top:1em;border-top:1px solid #ccc;font-size:12px;color:#666;}"
        "code{background:#eae6df;padding:1px 4px;border-radius:3px;}"
    ),
    "dark": (
        "body{background:#0f0f12;color:#eee;font:13px/1.4 -apple-system,system-ui,sans-serif;margin:1.5em;}"
        "header{border-bottom:1px solid #333;padding-bottom:.6em;margin-bottom:1em;}"
        ".grid{display:flex;flex-wrap:wrap;align-items:flex-start;gap:1em;}"
        "figure{margin:0;background:#1a1a1f;border:1px solid #333;border-radius:6px;overflow:hidden;}"
        "video{display:block;width:auto;height:auto;max-width:none;background:#000;}"
        "figcaption{padding:.6em .8em;color:#bbb;max-width:60ch;}"
        "footer{margin-top:2em;padding-top:1em;border-top:1px solid #333;font-size:12px;color:#888;}"
        "code{background:#26262d;padding:1px 4px;border-radius:3px;}"
    ),
}


def write_gallery(serve_dir, title, cards, *, media="img", theme="dark", subtitle="", footer="", muted=True):
    """Write index.html into serve_dir.

    cards: list of {"src": filename, "caption": html}. media is "img" or
    "video"; theme is "light" or "dark". subtitle/footer are optional HTML.
    muted applies to video only — pass False for clips whose audio is part of
    the output rather than incidental.
    """
    if media == "video":
        tag = ('<video src="{src}" controls loop playsinline preload="metadata"'
               + (' muted' if muted else '') + '></video>')
    else:
        tag = '<img src="{src}" alt="">'
    figs = "".join(
        f'<figure>{tag.format(src=c["src"])}<figcaption>{c["caption"]}</figcaption></figure>'
        for c in cards
    )
    subtitle_html = f"<div>{subtitle}</div>" if subtitle else ""
    footer_html = f"<footer>{footer}</footer>" if footer else ""
    html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{_THEMES[theme]}</style></head><body>"
        f"<header><h2>{title}</h2>{subtitle_html}</header>"
        f'<div class="grid">{figs}</div>{footer_html}</body></html>'
    )
    (Path(serve_dir) / "index.html").write_text(html)


def free_port(start=8765, span=100):
    for port in range(start, start + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port in {start}..{start + span}")


def serve(serve_dir, port):
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(serve_dir), **k)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def open_in_browser(url):
    for cmd in (["xdg-open", url], ["firefox", url]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            continue
    return False


def serve_and_block(serve_dir, *, keep=False):
    """Serve serve_dir, open a browser, and block until Ctrl-C; clean up unless keep."""
    serve_dir = Path(serve_dir)
    port = free_port()
    httpd = serve(str(serve_dir), port)
    url = f"http://localhost:{port}/index.html"
    opened = open_in_browser(url)
    print(f"\n  Gallery: {url}" + ("" if opened else
          f"  (no display — open it manually; ssh -L {port}:localhost:{port} if remote)"))
    print("  Ctrl-C to stop the server." + ("" if keep else f"  Temp dir {serve_dir} removed on exit."))
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()
        if not keep:
            shutil.rmtree(serve_dir, ignore_errors=True)
        print("\n  stopped.")
