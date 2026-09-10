#!/usr/bin/env python3
"""Serve a set of clip galleries with per-clip star ratings and notes.

The reviewer's ratings and notes have to come back to the machine, not sit in
the browser, so the page POSTs every change to this server and it persists them
to `ratings.json` beside the galleries. Autosave on change — no save button, and
nothing to remember to press before closing the tab.

Ratings are keyed "<gallery dir>/<clip filename>" so every clip across every
gallery lands in one flat file.

Usage:
  scripts/h3_review.py <root dir> [--port 8770] [--no-open]
"""
import argparse
import functools
import http.server
import json
import socket
import socketserver
import subprocess
import threading
from pathlib import Path

REVIEW_JS = Path(__file__).with_name("h3_review.js")


class ReviewHandler(http.server.SimpleHTTPRequestHandler):
    root = Path(".")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def ratings_path(self):
        return self.root / "ratings.json"

    def do_GET(self):
        if self.path == "/api/ratings":
            if self.ratings_path.exists():
                return self._json(json.loads(self.ratings_path.read_text()))
            return self._json({})
        if self.path == "/review.js":
            body = REVIEW_JS.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/ratings":
            return self._json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        incoming = json.loads(self.rfile.read(length))
        with self.server.lock:
            current = (json.loads(self.ratings_path.read_text())
                       if self.ratings_path.exists() else {})
            for key, entry in incoming.items():
                current.setdefault(key, {}).update(entry)
            self.ratings_path.write_text(json.dumps(current, indent=2, sort_keys=True))
        return self._json({"saved": len(incoming)})

    def log_message(self, fmt, *args):
        if "/api/" not in fmt % args:
            super().log_message(fmt, *args)


def free_port(start):
    for port in range(start, start + 100):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port in {start}..{start + 100}")


def main():
    ap = argparse.ArgumentParser(description="Serve clip galleries with ratings + notes")
    ap.add_argument("root")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    ReviewHandler.root = root
    port = free_port(a.port)
    handler = functools.partial(ReviewHandler, directory=str(root))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    httpd.lock = threading.Lock()

    url = f"http://127.0.0.1:{port}/index.html"
    print(f"  {url}")
    print(f"  ratings -> {root / 'ratings.json'}  (autosaved, no button)")
    if not a.no_open:
        subprocess.Popen(["firefox", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")


if __name__ == "__main__":
    main()
