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
    preferred_port = int(os.getenv("DASHBOARD_PORT", "8765"))
    ports = [preferred_port, 8787, 8888, 9000, 0]
    last_error: OSError | None = None

    for port in ports:
        try:
            return ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
        except OSError as error:
            last_error = error

    raise RuntimeError("Could not start dashboard server.") from last_error


def start_dashboard_in_thread() -> ThreadingHTTPServer:
    server = create_server()
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Dashboard running at http://{host}:{port}")
    return server


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
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
