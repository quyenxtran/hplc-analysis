"""Authenticated loopback HTTP transport; no arbitrary file-path endpoints."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
import json
import secrets
from urllib.parse import urlsplit
from ..editing.model import json_value

ASSETS = Path(__file__).parent / "assets"
TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}


def make_server(workbench, port=0):
    token, lock = secrets.token_urlsafe(32), RLock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, mime="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def json(self, status, value):
            self.send(status, json.dumps(json_value(value), allow_nan=False).encode())

        def authorized(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            origin = self.headers.get("Origin")
            return (self.headers.get("Host") == expected and
                    (not origin or origin == "http://" + expected) and
                    secrets.compare_digest(self.headers.get("X-Session", ""), token))

        def do_GET(self):
            route = urlsplit(self.path).path
            if route == "/api/state":
                if not self.authorized():
                    return self.json(403, {"error": "Invalid local session."})
                with lock:
                    return self.json(200, workbench.payload())
            name = "index.html" if route == "/" else route.removeprefix("/")
            if name not in {p.name for p in ASSETS.iterdir() if p.is_file()}:
                return self.json(404, {"error": "Not found"})
            path = ASSETS / name
            self.send(200, path.read_bytes(), TYPES[path.suffix])

        def do_POST(self):
            if urlsplit(self.path).path != "/api/action" or not self.authorized():
                return self.json(403, {"error": "Invalid local session."})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 4_000_000:
                    raise ValueError("Request body must be at most 4 MB.")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Request must be an object.")
                with lock:
                    self.json(200, workbench.dispatch(data))
            except (ValueError, TypeError, KeyError, OSError) as error:
                self.json(400, {"error": str(error)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server, token
