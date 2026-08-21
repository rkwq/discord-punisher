import base64
import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from bot_config import DEFAULT_CONFIG, CONFIG_PATH, ensure_config_file, load_bot_config, merge_defaults, save_config


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web"


def create_server() -> ThreadingHTTPServer:
    ensure_config_file()
    # Render (and most hosts) assign the port via $PORT and only expose that
    # one port publicly. Fall back to DASHBOARD_PORT for local runs.
    port = int(os.getenv("PORT") or os.getenv("DASHBOARD_PORT", "8765"))
    # Bind on all interfaces, not just localhost, so the host's proxy can
    # reach the server from outside the container.
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    return ThreadingHTTPServer((host, port), DashboardHandler)


def start_dashboard_in_thread() -> ThreadingHTTPServer:
    server = create_server()
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Dashboard running at http://{host}:{port}")
    return server


def _check_auth(handler: "DashboardHandler") -> bool:
    """Require HTTP Basic Auth if DASHBOARD_PASSWORD is set. Skipped locally
    (no password set) so nothing breaks for people not deploying publicly."""
    password = os.getenv("DASHBOARD_PASSWORD", "")
    if not password:
        return True

    username = os.getenv("DASHBOARD_USERNAME", "admin")
    header = handler.headers.get("Authorization", "")
    if header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            sent_user, _, sent_pass = decoded.partition(":")
        except Exception:
            sent_user, sent_pass = "", ""
        if hmac.compare_digest(sent_user, username) and hmac.compare_digest(sent_pass, password):
            return True

    handler.send_response(401)
    handler.send_header("WWW-Authenticate", 'Basic realm="Bot Dashboard"')
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return False


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not _check_auth(self):
            return

        path = urlparse(self.path).path
        if path == "/api/config":
            self.send_json(load_bot_config())
            return

        if path in {"/", "/index.html"}:
            self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path == "/styles.css":
            self.send_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
            return

        if path == "/app.js":
            self.send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return

        self.send_error(404)

    def do_POST(self) -> None:
        if not _check_auth(self):
            return

        path = urlparse(self.path).path
        if path != "/api/config":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            incoming = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        config = merge_defaults(incoming, DEFAULT_CONFIG)
        save_config(config)
        self.send_json({"ok": True, "path": str(CONFIG_PATH), "config": config})

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return

        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, data: dict) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    server = create_server()
    host, port = server.server_address
    print(f"Dashboard running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
