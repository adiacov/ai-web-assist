import json

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
