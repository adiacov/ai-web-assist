import json

import pytest

from ai_web_assist.claude import StreamParser, build_command, tool_summary
from ai_web_assist.config import Config
from ai_web_assist.files import Workspace
from conftest import FIXTURES


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path, Config(title="t"))


def delta(text, parent=None):
    return {"type": "stream_event", "parent_tool_use_id": parent,
            "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}}


def block_start(kind="text", parent=None):
    return {"type": "stream_event", "parent_tool_use_id": parent,
            "event": {"type": "content_block_start", "content_block": {"type": kind}}}


def tool_use(name, inp, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def test_build_command_defaults():
    cmd = build_command(Config(title="t"), None, "PROMPT")
    assert cmd[:2] == ["claude", "-p"]
    for flag in ("--output-format", "--verbose", "--include-partial-messages", "--permission-mode",
                 "--allowedTools", "--append-system-prompt"):
        assert flag in cmd
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert cmd[cmd.index("--permission-mode") + 1] == "acceptEdits"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read Edit Write Glob Grep WebFetch WebSearch Bash"
    assert cmd[cmd.index("--append-system-prompt") + 1] == "PROMPT"
    assert "--resume" not in cmd and "--model" not in cmd


def test_build_command_resume_and_model():
    cmd = build_command(Config(title="t", model="sonnet", permission_mode="plan", allowed_tools=("Read",)), "sid-1", "P")
    assert cmd[cmd.index("--resume") + 1] == "sid-1"
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert cmd[cmd.index("--permission-mode") + 1] == "plan"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read"


def test_parser_text_and_blocks(ws):
    p = StreamParser(ws)
    assert p.feed(block_start()) == []  # no separator before the first text
    assert p.feed(delta("Hello")) == [{"t": "text", "v": "Hello"}]
    assert p.feed(block_start("thinking")) == []
    assert p.feed(block_start()) == [{"t": "text", "v": "\n\n"}]
    p.feed(delta("World"))
    assert p.text == "Hello\n\nWorld"


def test_parser_tools(ws):
    p = StreamParser(ws)
    ev = p.feed(tool_use("Edit", {"file_path": str(ws.root / "docs" / "a.md"), "old_string": "x"}))
    assert ev == [{"t": "tool", "name": "Edit", "summary": "docs/a.md"}]
    assert p.tools == [{"name": "Edit", "summary": "docs/a.md"}]


def test_parser_ignores_subagents_and_unknown(ws):
    p = StreamParser(ws)
    assert p.feed(delta("hidden", parent="toolu_1")) == []
    assert p.feed(tool_use("Read", {"file_path": "/x"}, parent="toolu_1")) == []
    assert p.feed({"type": "rate_limit_event"}) == []
    assert p.feed({"type": "system", "subtype": "hook_started"}) == []
    assert p.feed({"type": "stream_event"}) == []  # malformed: no event
    assert p.text == "" and p.tools == []


def test_parser_session_and_errors(ws):
    p = StreamParser(ws)
    p.feed({"type": "system", "subtype": "init", "session_id": "abc"})
    assert p.session_id == "abc"
    assert p.feed({"type": "result", "subtype": "success", "is_error": False}) == []
    assert p.feed({"type": "result", "subtype": "error_max_turns", "is_error": True}) == [{"t": "error", "v": "error_max_turns"}]
    assert p.feed({"type": "result", "is_error": True, "result": "Not logged in"}) == [{"t": "error", "v": "Not logged in"}]


def test_parser_feed_line(ws):
    p = StreamParser(ws)
    assert p.feed_line("not json\n") == []
    assert p.feed_line("[1, 2]") == []
    assert p.feed_line(json.dumps(delta("hi"))) == [{"t": "text", "v": "hi"}]


def test_parser_recorded_stream(ws):
    p = StreamParser(ws)
    events = []
    for line in (FIXTURES / "stream_basic.jsonl").read_text().replace("/PROJECT", str(ws.root)).splitlines():
        events += p.feed_line(line)
    assert p.session_id
    assert {"t": "tool", "name": "Read", "summary": "a.md"} in events
    assert p.text == 'The file a.md contains a single word: "hello".'
    assert not any(e["t"] == "error" for e in events)


@pytest.mark.parametrize("name, inp, expected", [
    ("Bash", {"command": "ls -la", "description": "List files"}, "List files"),
    ("Bash", {"command": "ls\n  -la"}, "ls -la"),
    ("WebFetch", {"url": "https://x.dev", "prompt": "p"}, "https://x.dev"),
    ("WebSearch", {"query": "spark joins"}, "spark joins"),
    ("Grep", {"pattern": "TODO", "path": "src"}, "TODO"),
    ("Glob", {"pattern": "**/*.md"}, "**/*.md"),
    ("Read", {"file_path": "/etc/hosts"}, "/etc/hosts"),
    ("Task", {"foo": 1}, ""),
])
def test_tool_summary(ws, name, inp, expected):
    assert tool_summary(name, inp, ws) == expected


def test_tool_summary_cap(ws):
    assert len(tool_summary("Bash", {"command": "x" * 500}, ws)) == 160
