import os

import pytest

from ai_web_assist.config import Config
from ai_web_assist.files import Workspace


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    files = [
        "README.md", "docs/plan.md", "docs/deep/x.py", "src/app.js",
        ".hidden.md", ".secret/key.txt", ".git/config", ".ai-web-assist/chat.json",
        "node_modules/pkg/index.js", "target/out.class", "dist/a.js", "build/b.js",
        "src/__pycache__/m.pyc", ".venv/lib.py", "venv/lib.py", "logs/run.log",
    ]
    for f in files:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"content of {f}")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    os.symlink(outside, root / "docs" / "escape.txt")
    os.symlink(root / "docs" / "plan.md", root / "docs" / "inside-link.md")
    return root


def paths(ws):
    files, _ = ws.list_tree()
    return [f["path"] for f in files]


def test_tree_default_excludes(project):
    ws = Workspace(project, Config(title="t"))
    assert paths(ws) == [
        "README.md", "docs/deep/x.py", "docs/inside-link.md", "docs/plan.md", "logs/run.log", "src/app.js",
    ]


def test_tree_entries_have_mtime(project):
    files, truncated = Workspace(project, Config(title="t")).list_tree()
    assert not truncated
    assert all(isinstance(f["mtime"], float) for f in files)


def test_tree_config_exclude_globs(project):
    ws = Workspace(project, Config(title="t", exclude=("*.log", "deep")))
    assert "logs/run.log" not in paths(ws)
    assert "docs/deep/x.py" not in paths(ws)
    assert "docs/plan.md" in paths(ws)


def test_tree_include(project):
    ws = Workspace(project, Config(title="t", include=("docs",)))
    assert paths(ws) == ["docs/deep/x.py", "docs/inside-link.md", "docs/plan.md"]


def test_tree_include_missing_folder(project):
    assert paths(Workspace(project, Config(title="t", include=("nope",)))) == []


def test_tree_limit(project):
    files, truncated = Workspace(project, Config(title="t")).list_tree(limit=2)
    assert len(files) == 2 and truncated


@pytest.mark.parametrize("rel", [
    "", "../outside.txt", "docs/../../outside.txt", "/etc/passwd", "docs/escape.txt",
    ".hidden.md", ".secret/key.txt", ".git/config", ".ai-web-assist/chat.json",
    "node_modules/pkg/index.js", "src/__pycache__/m.pyc", "missing.md", "docs",
])
def test_resolve_refuses(project, rel):
    assert Workspace(project, Config(title="t")).resolve(rel) is None


def test_resolve_ok(project):
    ws = Workspace(project, Config(title="t"))
    assert ws.resolve("docs/plan.md") == project / "docs" / "plan.md"
    assert ws.resolve("docs/inside-link.md") is not None


def test_resolve_respects_include_and_exclude(project):
    ws = Workspace(project, Config(title="t", include=("docs",), exclude=("*.py",)))
    assert ws.resolve("README.md") is None
    assert ws.resolve("docs/deep/x.py") is None
    assert ws.resolve("docs/plan.md") is not None


def test_read_file(project):
    r = Workspace(project, Config(title="t")).read_file("docs/plan.md")
    assert r["content"] == "content of docs/plan.md"
    assert r["binary"] is False and r["truncated"] is False
    assert r["path"] == "docs/plan.md"


def test_read_binary(project):
    (project / "img.png").write_bytes(b"\x89PNG\x00\x01\x02")
    r = Workspace(project, Config(title="t")).read_file("img.png")
    assert r["binary"] is True and r["content"] == ""


def test_read_truncated(project):
    (project / "big.txt").write_text("a" * (1024 * 1024 + 10))
    r = Workspace(project, Config(title="t")).read_file("big.txt")
    assert r["truncated"] is True and len(r["content"]) == 1024 * 1024


def test_read_invalid_utf8_replaced(project):
    (project / "latin.txt").write_bytes(b"caf\xe9")
    assert Workspace(project, Config(title="t")).read_file("latin.txt")["content"] == "caf�"


def test_read_refused(project):
    assert Workspace(project, Config(title="t")).read_file("../outside.txt") is None


def test_relpath(project):
    ws = Workspace(project, Config(title="t"))
    assert ws.relpath(str(project / "docs" / "plan.md")) == "docs/plan.md"
    assert ws.relpath("docs/plan.md") == "docs/plan.md"
    assert ws.relpath("/etc/passwd") == "/etc/passwd"


def test_workspace_id_stable(project):
    a = Workspace(project, Config(title="t")).workspace_id
    assert a == Workspace(project, Config(title="other")).workspace_id
    assert len(a) == 12
