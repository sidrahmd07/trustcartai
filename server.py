"""Local chat demo: serves ui/ and a small JSON API using only the Python standard library.

    python server.py            # then open http://127.0.0.1:8000
"""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from trustcart.config import load_config
from trustcart.pipeline import Assistant

UI_DIR = Path(__file__).resolve().parent / "ui"
MAX_QUERY_CHARS = 300
MAX_BODY_BYTES = 4096
_assistant: Assistant | None = None


def get_assistant() -> Assistant:
    global _assistant
    if _assistant is None:
        _assistant = Assistant()
    return _assistant


def handle_chat(payload: dict) -> tuple[int, dict]:
    """Validate the request and return (status code, JSON body). Kept separate from HTTP so it can be tested."""
    query = payload.get("query")
    conversation_id = payload.get("conversation_id", "default")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        return 400, {"error": f"query must be a non-empty string of at most {MAX_QUERY_CHARS} characters"}
    if not isinstance(conversation_id, str) or len(conversation_id) > 64:
        return 400, {"error": "conversation_id must be a string of at most 64 characters"}
    return 200, get_assistant().respond(query.strip(), conversation_id)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        name = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        target = (UI_DIR / name).resolve()
        if UI_DIR not in target.parents or not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), f"{content_type}; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            self._send(413, b'{"error": "request too large"}', "application/json")
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, b'{"error": "invalid JSON"}', "application/json")
            return
        status, body = handle_chat(payload if isinstance(payload, dict) else {})
        self._send(status, json.dumps(body, ensure_ascii=False).encode("utf-8"), "application/json")


def main() -> None:
    server_cfg = load_config()["server"]
    server = ThreadingHTTPServer((server_cfg["host"], server_cfg["port"]), Handler)
    print(f"TrustCart AI running on http://{server_cfg['host']}:{server_cfg['port']}")
    server.serve_forever()


if __name__ == "__main__":
    main()
