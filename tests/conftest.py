import http.client
import json
import os
import stat
import sys
import threading
from pathlib import Path

import pytest

from ai_web_assist.config import load_config
from ai_web_assist.files import Workspace
from ai_web_assist.server import App, make_server
from ai_web_assist.state import ChatStore, ensure_state_dir

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "README.md").write_text("# Hello\n\nSee `docs/plan.md`.\n")
    (root / "docs" / "plan.md").write_text("| a | b |\n|---|---|\n| 1 | 2 |\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]")
    return root


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """Put a fake `claude` on PATH that replays a recorded stream; returns a settings helper."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(f"#!/bin/sh\nexec {sys.executable} {FIXTURES / 'fake_claude.py'} \"$@\"\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    record = tmp_path / "claude-record.jsonl"
    monkeypatch.setenv("FAKE_CLAUDE_RECORD", str(record))
    monkeypatch.setenv("FAKE_CLAUDE_STREAM", str(FIXTURES / "stream_basic.jsonl"))

    class Fake:
        def set(self, **env):
            for k, v in env.items():
                monkeypatch.setenv(f"FAKE_CLAUDE_{k.upper()}", str(v))

        def calls(self):
            if not record.exists():
                return []
            return [json.loads(line) for line in record.read_text().splitlines()]

    return Fake()


class Client:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        hdrs = {"Host": f"127.0.0.1:{self.port}"}
        if body is not None:
            hdrs["Content-Type"] = "application/json"
        hdrs.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=data, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp, raw

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def get_json(self, path):
        resp, raw = self.get(path)
        return resp.status, json.loads(raw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body={} if body is None else body, **kw)

    def chat(self, message):
        """Send a chat message and return (status, list of stream events or error body)."""
        resp, raw = self.post("/api/chat", {"message": message})
        if resp.status != 200:
            return resp.status, json.loads(raw)
        return 200, [json.loads(line) for line in raw.decode().splitlines() if line]


def start_server(root):
    config = load_config(root)
    ws = Workspace(root, config)
    store = ChatStore(ensure_state_dir(ws.root))
    app = App(ws, store)
    srv = make_server(app, 0)
    t = threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True)
    t.start()
    return srv, app


@pytest.fixture
def server(project):
    """Start a server on a free port; yields a client. Call `server.restart()` for a fresh instance."""
    state = {}

    def start():
        srv, app = start_server(project)
        state.update(srv=srv, app=app)
        client.port = srv.server_address[1]
        client.app = app

    def stop():
        state["app"].shutdown()
        state["srv"].shutdown()
        state["srv"].server_close()

    client = Client(0)
    client.root = project
    client.restart = lambda: (stop(), start())
    start()
    yield client
    stop()
