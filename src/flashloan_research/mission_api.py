from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import SETTINGS
from .mission_queue import MissionQueue, MissionValidationError

MAX_REQUEST_BYTES = 256_000
UI_PATH = Path(__file__).resolve().parents[2] / "ui" / "research-mission-form.html"


class MissionRequestHandler(BaseHTTPRequestHandler):
    server_version = "ResearchMissionAPI/0.1"

    def _send(self, status: int, body: dict, content_type: str = "application/json") -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8") if content_type == "application/json" else body
        self.send_response(status)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            if not UI_PATH.is_file():
                self._send(404, {"error": "mission form not found"})
                return
            self._send(200, UI_PATH.read_bytes(), "text/html")
            return
        if parsed.path == "/health":
            self._send(200, {"status": "ok", "service": "research-mission-intake", "agent_runtime": "not_connected"})
            return
        if parsed.path == "/missions":
            self._send(200, {"missions": self.server.queue.list_recent()})
            return
        if parsed.path.startswith("/missions/"):
            mission_id = parsed.path.rsplit("/", 1)[-1]
            item = self.server.queue.get(mission_id)
            self._send(200 if item else 404, item or {"error": "mission not found"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/missions":
            self._send(404, {"error": "not found"})
            return
        length = self.headers.get("Content-Length")
        try:
            size = int(length or "0")
        except ValueError:
            self._send(400, {"error": "invalid Content-Length"})
            return
        if size < 1 or size > MAX_REQUEST_BYTES:
            self._send(413, {"error": "request must be between 1 and 256000 bytes"})
            return
        if self.headers.get_content_type() != "application/json":
            self._send(415, {"error": "Content-Type must be application/json"})
            return
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            result = self.server.queue.enqueue(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON"})
            return
        except MissionValidationError as exc:
            self._send(422, {"error": str(exc)})
            return
        self._send(202, result)

    def log_message(self, fmt: str, *args) -> None:
        return


class MissionHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, queue: MissionQueue):
        super().__init__(address, handler)
        self.queue = queue


def main() -> None:
    queue = MissionQueue(SETTINGS.database_path)
    server = MissionHTTPServer(("127.0.0.1", 8765), MissionRequestHandler, queue)
    print("Research Mission Form: http://127.0.0.1:8765/")
    print("Local-only intake API. Agent execution is not connected yet.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        queue.close()


if __name__ == "__main__":
    main()
