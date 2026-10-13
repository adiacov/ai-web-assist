import json

from ai_web_assist.state import ChatStore, ensure_state_dir


def test_load_missing(tmp_path):
    assert ChatStore(tmp_path / "s").load() == {"session_id": None, "messages": []}


def test_append_and_session(tmp_path):
    s = ChatStore(tmp_path / "s")
    s.append("user", "hi")
    s.set_session("abc")
    s.append("assistant", "hello", [{"name": "Read", "summary": "a.md"}])
    st = ChatStore(tmp_path / "s").load()
    assert st["session_id"] == "abc"
    assert [m["role"] for m in st["messages"]] == ["user", "assistant"]
    assert st["messages"][1]["tools"] == [{"name": "Read", "summary": "a.md"}]
    assert isinstance(st["messages"][0]["ts"], float)
    assert not list((tmp_path / "s").glob("*.tmp"))


def test_archive(tmp_path):
    s = ChatStore(tmp_path / "s")
    assert s.archive() is None  # nothing to archive
    s.append("user", "one")
    a1 = s.archive()
    s.append("user", "two")
    a2 = s.archive()
    assert a1 != a2 and a1.exists() and a2.exists()
    assert a1.parent == tmp_path / "s" / "archive"
    assert a1.name.startswith("chat-") and a1.suffix == ".json"
    assert json.loads(a1.read_text())["messages"][0]["text"] == "one"
    assert s.load() == {"session_id": None, "messages": []}


def test_corrupt_state(tmp_path):
    d = tmp_path / "s"
    d.mkdir()
    (d / "chat.json").write_text("{not json")
    s = ChatStore(d)
    assert s.load() == {"session_id": None, "messages": []}
    assert len(list(d.glob("chat.corrupt-*.json"))) == 1
    assert not (d / "chat.json").exists()


def test_ensure_state_dir(tmp_path):
    d = ensure_state_dir(tmp_path)
    assert d == tmp_path / ".ai-web-assist"
    lines = (d / ".gitignore").read_text().split()
    assert lines == ["*", "!.gitignore", "!config.toml"]


def test_ensure_state_dir_keeps_existing_gitignore(tmp_path):
    d = tmp_path / ".ai-web-assist"
    d.mkdir()
    (d / ".gitignore").write_text("custom\n")
    ensure_state_dir(tmp_path)
    assert (d / ".gitignore").read_text() == "custom\n"
