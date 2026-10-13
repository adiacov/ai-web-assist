import json
import os
import socket
import threading
import time

# --- US1: workspace, static files, read APIs, request guards ---------------------------------


def test_index_has_escaped_title(server, project):
    (project / ".ai-web-assist" / "config.toml").write_text('title = "<b>Tom & Jerry</b>"')
    server.restart()
    resp, raw = server.get("/")
    assert resp.status == 200
    assert resp.getheader("Content-Type").startswith("text/html")
    html = raw.decode()
    assert "<title>&lt;b&gt;Tom &amp; Jerry&lt;/b&gt;</title>" in html
    assert "{{TITLE}}" not in html


def test_security_headers(server):
    resp, _ = server.get("/")
    assert "default-src 'self'" in resp.getheader("Content-Security-Policy")
    assert resp.getheader("X-Content-Type-Options") == "nosniff"


def test_static_files(server):
    resp, raw = server.get("/static/app.js")
    assert resp.status == 200 and "javascript" in resp.getheader("Content-Type")
    resp, _ = server.get("/static/vendor/highlight.min.js")
    assert resp.status == 200
    resp, _ = server.get("/static/app.css")
    assert resp.status == 200 and "text/css" in resp.getheader("Content-Type")


def test_static_traversal(server):
    for path in ("/static/../config.py", "/static/%2e%2e/config.py", "/static/missing.js", "/static/"):
        resp, _ = server.get(path)
        assert resp.status == 404, path


def test_api_config(server, project):
    status, body = server.get_json("/api/config")
    assert status == 200
    assert body["title"] == project.name
    assert body["project_name"] == project.name
    assert len(body["workspace_id"]) == 12
    assert body["version"]


def test_api_tree(server):
    status, body = server.get_json("/api/tree")
    assert status == 200
    assert [f["path"] for f in body["files"]] == ["README.md", "docs/plan.md"]
    assert body["truncated"] is False


def test_api_file(server):
    status, body = server.get_json("/api/file?path=docs/plan.md")
    assert status == 200 and body["content"].startswith("| a |")
    for bad in ("../../etc/passwd", ".git/config", "%2Fetc%2Fpasswd", "missing.md", ".ai-web-assist/.gitignore", ""):
        status, body = server.get_json(f"/api/file?path={bad}")
        assert status == 404, bad
        assert "error" in body


def test_unknown_route(server):
    assert server.get("/api/nope")[0].status == 404
    assert server.post("/api/nope")[0].status == 404


def test_host_guard(server):
    for host in ("evil.example", f"evil.example:{server.port}", "127.0.0.1:1", ""):
        resp, _ = server.get("/api/tree", headers={"Host": host})
        assert resp.status == 403, host
    resp, _ = server.get("/api/tree", headers={"Host": f"localhost:{server.port}"})
    assert resp.status == 200


def test_post_requires_json(server):
    resp, _ = server.request("POST", "/api/stop", body=None, headers={"Content-Type": "text/plain"})
    assert resp.status == 403


def test_post_origin_guard(server):
    resp, _ = server.post("/api/stop", headers={"Origin": "http://evil.example"})
    assert resp.status == 403
    resp, _ = server.post("/api/stop", headers={"Origin": f"http://127.0.0.1:{server.port}"})
    assert resp.status == 200


def test_bad_json_body(server):
    resp, raw = server.request("POST", "/api/chat", headers={"Content-Type": "application/json"})
    assert resp.status == 400
    assert json.loads(raw)["error"]


# --- US2: chat streaming -----------------------------------------------------------------------


def wait_for(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def is_busy(server):
    return server.get_json("/api/history")[1]["busy"]


def test_chat_streams_and_saves(server, fake_claude, project):
    (project / "a.md").write_text("hello")
    status, events = server.chat("-- read a.md, \"quoted\"\nsecond line")
    assert status == 200
    kinds = [e["t"] for e in events]
    assert kinds[-1] == "done" and "error" not in kinds
    assert {"t": "tool", "name": "Read", "summary": "a.md"} in events
    text = "".join(e["v"] for e in events if e["t"] == "text")
    assert text == 'The file a.md contains a single word: "hello".'

    call = fake_claude.calls()[0]
    assert call["stdin"] == "-- read a.md, \"quoted\"\nsecond line"
    assert all("read a.md" not in arg for arg in call["argv"])
    assert call["cwd"] == str(project)
    assert "--resume" not in call["argv"]

    history = server.get_json("/api/history")[1]
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["text"] == text
    assert history["messages"][1]["tools"] == [{"name": "Read", "summary": "a.md"}]
    assert history["session_id"] and history["busy"] is False


def test_chat_empty_message(server, fake_claude):
    status, body = server.chat("   ")
    assert status == 400 and body["error"]


def test_chat_one_at_a_time(server, fake_claude):
    fake_claude.set(delay=0.05)
    t = threading.Thread(target=server.chat, args=("first",))
    t.start()
    assert wait_for(lambda: is_busy(server))
    status, body = server.chat("second")
    assert status == 409 and "working" in body["error"]
    t.join(10)
    assert not is_busy(server)


def test_chat_stop_kills_process_group(server, fake_claude):
    fake_claude.set(delay=0.3, child=1)
    result = {}
    t = threading.Thread(target=lambda: result.update(r=server.chat("long task")))
    t.start()
    assert wait_for(lambda: fake_claude.calls())
    assert server.post("/api/stop")[0].status == 200
    t.join(10)
    assert not t.is_alive()
    status, events = result["r"]
    assert events[-1] == {"t": "done"}
    assert any(e["t"] == "error" and "Stopped" in e["v"] for e in events)

    child = fake_claude.calls()[0]["child_pid"]

    def child_gone():
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            return True
        with open(f"/proc/{child}/stat") as f:  # a zombie waiting to be reaped counts as gone
            return f.read().split()[2] == "Z"
    assert wait_for(child_gone)
    roles = [m["role"] for m in server.get_json("/api/history")[1]["messages"]]
    assert roles[0] == "user" and "error" in roles


def test_chat_claude_failure(server, fake_claude):
    fake_claude.set(stream="", exit=1, stderr="Error: not logged in")
    status, events = server.chat("hi")
    assert status == 200
    errors = [e["v"] for e in events if e["t"] == "error"]
    assert errors and "not logged in" in errors[0]
    assert events[-1] == {"t": "done"}
    roles = [m["role"] for m in server.get_json("/api/history")[1]["messages"]]
    assert roles == ["user", "error"]  # no empty assistant message


def test_chat_survives_client_disconnect(server, fake_claude):
    fake_claude.set(delay=0.03)
    body = b'{"message": "hi"}'
    s = socket.create_connection(("127.0.0.1", server.port))
    s.sendall(b"POST /api/chat HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nContent-Type: application/json\r\n"
              b"Content-Length: %d\r\n\r\n%s" % (server.port, len(body), body))
    assert s.recv(100)  # response started
    s.close()
    assert wait_for(lambda: not is_busy(server) and len(server.get_json("/api/history")[1]["messages"]) == 2, 10)
    reply = server.get_json("/api/history")[1]["messages"][1]
    assert reply["text"].startswith("The file a.md")


def test_chat_unknown_session_explains(server, fake_claude):
    from conftest import FIXTURES
    fake_claude.set(stream=FIXTURES / "stream_bad_resume.jsonl", exit=1,
                    stderr="No conversation found with session ID: 0000")
    status, events = server.chat("hi")
    errors = " | ".join(e["v"] for e in events if e["t"] == "error")
    assert "No conversation found" in errors and "New session" in errors


# --- US3: resume and new session -----------------------------------------------------------------


def test_next_chat_resumes_session(server, fake_claude):
    server.chat("first")
    sid = server.get_json("/api/history")[1]["session_id"]
    assert sid
    server.chat("second")
    argv = fake_claude.calls()[1]["argv"]
    assert argv[argv.index("--resume") + 1] == sid


def test_history_survives_restart(server, fake_claude):
    server.chat("remember me")
    before = server.get_json("/api/history")[1]
    server.restart()
    after = server.get_json("/api/history")[1]
    assert after["messages"] == before["messages"] and after["session_id"] == before["session_id"]
    server.chat("again")
    assert "--resume" in fake_claude.calls()[-1]["argv"]


def test_new_session_archives(server, fake_claude, project):
    server.chat("old topic")
    resp, raw = server.post("/api/new")
    assert resp.status == 200 and json.loads(raw) == {"ok": True}
    history = server.get_json("/api/history")[1]
    assert history == {"session_id": None, "messages": [], "busy": False}
    archives = list((project / ".ai-web-assist" / "archive").glob("chat-*.json"))
    assert len(archives) == 1
    assert json.loads(archives[0].read_text())["messages"][0]["text"] == "old topic"
    server.chat("new topic")
    assert "--resume" not in fake_claude.calls()[-1]["argv"]


def test_new_session_refused_while_busy(server, fake_claude):
    fake_claude.set(delay=0.05)
    t = threading.Thread(target=server.chat, args=("busy",))
    t.start()
    assert wait_for(lambda: is_busy(server))
    resp, raw = server.post("/api/new")
    assert resp.status == 409 and json.loads(raw)["error"] == "busy"
    t.join(10)
