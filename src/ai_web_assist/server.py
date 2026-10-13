"""Local HTTP server: static UI, file APIs and the chat stream. Binds 127.0.0.1 only."""

from __future__ import annotations

import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from typing import Callable

from ai_web_assist import __version__
from ai_web_assist.claude import ClaudeRunner, StreamParser, build_command
from ai_web_assist.files import Workspace
from ai_web_assist.prompt import build_prompt
from ai_web_assist.state import ChatStore

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}
# Inline scripts are not allowed: rendered files cannot run code even if the sanitizer misses something.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
MAX_BODY_BYTES = 1024 * 1024


class App:
    """Everything a request needs: the workspace, the chat store, and the one-reply-at-a-time lock."""

    def __init__(self, workspace: Workspace, store: ChatStore):
        self.workspace = workspace
        self.store = store
        self.system_prompt = build_prompt(workspace.config)
        self.chat_lock = threading.Lock()
        self.runner: ClaudeRunner | None = None

    def stop(self) -> None:
        runner = self.runner
        if runner is not None:
            runner.stop()

    def shutdown(self) -> None:
        self.stop()

    def run_chat(self, message: str, emit: Callable[[dict], None]) -> None:
        """Run one Claude turn, streaming UI events to `emit`. The caller holds `chat_lock`."""
        self.store.append("user", message)
        session_id = self.store.load()["session_id"]
        parser = StreamParser(self.workspace)
        runner = ClaudeRunner(build_command(self.workspace.config, session_id, self.system_prompt),
                              self.workspace.root, self.store.stderr_path)
        self.runner = runner
        errors: list[str] = []
        try:
            runner.start(message)
            for line in runner.lines():
                for event in parser.feed_line(line):
                    if event["t"] == "error":
                        errors.append(event["v"])
                    emit(event)
                if parser.session_id and parser.session_id != session_id:
                    session_id = parser.session_id
                    self.store.set_session(session_id)  # saved at once, so a crash still resumes
            code = runner.wait()
        except OSError as e:
            code = None
            errors.append(f"Could not run claude: {e}")
            emit({"t": "error", "v": errors[-1]})
        finally:
            self.runner = None

        late_error = None
        if runner.stopped:
            late_error = "Stopped."
        elif code not in (0, None):
            late_error = runner.stderr_tail() or (None if errors else f"claude exited with code {code}")
            if late_error and "No conversation found" in late_error:
                late_error += "\nThe saved Claude session no longer exists. Click New session to start fresh."
        if late_error:
            errors.append(late_error)
            emit({"t": "error", "v": late_error})
        if parser.text or parser.tools:
            self.store.append("assistant", parser.text, parser.tools)
        for error in errors:
            self.store.append("error", error)


def make_server(app: App, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"app": app})
    srv = ThreadingHTTPServer((HOST, port), handler)
    srv.daemon_threads = True
    return srv


class Handler(BaseHTTPRequestHandler):
    app: App
    server_version = "ai-web-assist/" + __version__

    def log_message(self, *args):  # keep the terminal quiet
        pass

    # ---- guards ----------------------------------------------------------------------------

    def _allowed_hosts(self) -> set[str]:
        port = self.server.server_address[1]
        return {f"{HOST}:{port}", f"localhost:{port}"}

    def _host_ok(self) -> bool:
        # Blocks DNS rebinding: a foreign site's hostname resolving to 127.0.0.1 is refused.
        return self.headers.get("Host", "") in self._allowed_hosts()

    def _post_ok(self) -> bool:
        # Cross-site pages can't send JSON without a CORS preflight, which is never answered.
        ctype = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        origin = self.headers.get("Origin")
        return ctype == "application/json" and (origin is None or origin == f"http://{self.headers.get('Host')}")

    # ---- responses -------------------------------------------------------------------------

    def _common_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

    def send_json(self, obj, code: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._common_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code: int, message: str) -> None:
        self.send_json({"error": message}, code)

    def send_bytes(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP)
        self._common_headers()
        self.end_headers()
        self.wfile.write(body)

    # ---- GET -------------------------------------------------------------------------------

    def do_GET(self):
        if not self._host_ok():
            return self.send_error_json(403, "forbidden host")
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/":
            return self.send_index()
        if url.path.startswith("/static/"):
            return self.send_static(unquote(url.path[len("/static/"):]))
        if url.path == "/api/config":
            return self.send_json(self.config_info())
        if url.path == "/api/tree":
            files, truncated = self.app.workspace.list_tree()
            return self.send_json({"files": files, "truncated": truncated})
        if url.path == "/api/file":
            result = self.app.workspace.read_file(query.get("path", [""])[0])
            if result is None:
                return self.send_error_json(404, "not found")
            return self.send_json(result)
        if url.path == "/api/history":
            st = self.app.store.load()
            return self.send_json({"session_id": st["session_id"], "messages": st["messages"],
                                   "busy": self.app.chat_lock.locked()})
        self.send_error_json(404, "not found")

    def config_info(self) -> dict:
        ws = self.app.workspace
        return {"title": ws.config.title, "workspace_id": ws.workspace_id,
                "version": __version__, "project_name": ws.root.name}

    def send_index(self) -> None:
        page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        page = page.replace("{{TITLE}}", html.escape(self.app.workspace.config.title))
        self.send_bytes(page.encode(), CONTENT_TYPES[".html"])

    def send_static(self, name: str) -> None:
        path = (STATIC_DIR / name).resolve()
        if STATIC_DIR not in path.parents or not path.is_file():
            return self.send_error_json(404, "not found")
        self.send_bytes(path.read_bytes(), CONTENT_TYPES.get(path.suffix, "application/octet-stream"))

    # ---- POST ------------------------------------------------------------------------------

    def do_POST(self):
        if not self._host_ok() or not self._post_ok():
            return self.send_error_json(403, "forbidden")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                return self.send_error_json(413, "request too large")
            data = json.loads(self.rfile.read(length) or b"null")
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
            return self.send_error_json(400, "expected a JSON object")
        route = self.POST_ROUTES.get(urlparse(self.path).path)
        if route is None:
            return self.send_error_json(404, "not found")
        getattr(self, route)(data)

    POST_ROUTES = {"/api/chat": "post_chat", "/api/stop": "post_stop"}

    def post_chat(self, data: dict) -> None:
        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            return self.send_error_json(400, "empty message")
        if not self.app.chat_lock.acquire(blocking=False):
            return self.send_error_json(409, "Claude is still working on the previous message")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self._common_headers()
            self.end_headers()
            connected = True

            def emit(event: dict) -> None:
                nonlocal connected
                if not connected:
                    return  # browser went away; Claude keeps going so the files stay consistent
                try:
                    self.wfile.write((json.dumps(event) + "\n").encode())
                    self.wfile.flush()
                except OSError:
                    connected = False

            try:
                self.app.run_chat(message, emit)
            except Exception as e:  # never leave the browser waiting without an answer
                emit({"t": "error", "v": f"Internal error: {e}"})
            emit({"t": "done"})
        finally:
            self.app.chat_lock.release()

    def post_stop(self, data: dict) -> None:
        self.app.stop()
        self.send_json({"ok": True})
