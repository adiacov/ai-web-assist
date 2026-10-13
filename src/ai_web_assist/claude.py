"""Running `claude -p` and turning its stream-json output into small UI events.

UI events: {"t": "text", "v": str} | {"t": "tool", "name": str, "summary": str} | {"t": "error", "v": str}
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Iterator

from ai_web_assist.config import Config
from ai_web_assist.files import Workspace

SUMMARY_KEYS = ("file_path", "notebook_path", "url", "query", "description", "command", "pattern", "path")
PATH_KEYS = ("file_path", "notebook_path", "path")
SUMMARY_MAX = 160
STOP_GRACE_SECONDS = 5


def build_command(config: Config, session_id: str | None, system_prompt: str) -> list[str]:
    """The message itself is sent on stdin, never in argv."""
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
           "--permission-mode", config.permission_mode,
           "--allowedTools", " ".join(config.allowed_tools),
           "--append-system-prompt", system_prompt]
    if config.model:
        cmd += ["--model", config.model]
    if session_id:
        cmd += ["--resume", session_id]
    return cmd


def tool_summary(name: str, inp: dict, workspace: Workspace) -> str:
    for key in SUMMARY_KEYS:
        if key in inp:
            value = " ".join(str(inp[key]).split())
            if key in PATH_KEYS:
                value = workspace.relpath(value)
            return value[:SUMMARY_MAX]
    return ""


class StreamParser:
    """Feed it stream-json events; it collects the reply text, tool uses and the session id."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.session_id: str | None = None
        self.text = ""
        self.tools: list[dict] = []

    def feed_line(self, line: str) -> list[dict]:
        try:
            event = json.loads(line)
        except ValueError:
            return []
        return self.feed(event) if isinstance(event, dict) else []

    def feed(self, event: dict) -> list[dict]:
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and event.get("session_id"):
            self.session_id = event["session_id"]
            return []
        if kind == "result":
            if event.get("is_error"):
                return [{"t": "error", "v": str(event.get("result") or event.get("subtype") or "Claude reported an error")}]
            return []
        if event.get("parent_tool_use_id") is not None:
            return []  # sub-agent activity: not part of the visible reply
        if kind == "stream_event":
            return self._stream_event(event.get("event") or {})
        if kind == "assistant":
            return self._assistant(event.get("message") or {})
        return []

    def _stream_event(self, e: dict) -> list[dict]:
        if e.get("type") == "content_block_delta" and (e.get("delta") or {}).get("type") == "text_delta":
            chunk = e["delta"].get("text", "")
            self.text += chunk
            return [{"t": "text", "v": chunk}] if chunk else []
        if e.get("type") == "content_block_start" and (e.get("content_block") or {}).get("type") == "text" and self.text:
            self.text += "\n\n"
            return [{"t": "text", "v": "\n\n"}]
        return []

    def _assistant(self, message: dict) -> list[dict]:
        out = []
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool = {"name": str(block.get("name", "?")),
                        "summary": tool_summary(str(block.get("name")), block.get("input") or {}, self.workspace)}
                self.tools.append(tool)
                out.append({"t": "tool", **tool})
        return out


class ClaudeRunner:
    """One `claude -p` process in its own process group, so Stop also ends the tools it started."""

    def __init__(self, cmd: list[str], cwd: Path, stderr_path: Path):
        self.cmd = cmd
        self.cwd = cwd
        self.stderr_path = stderr_path
        self.proc: subprocess.Popen | None = None
        self.stopped = False

    def start(self, message: str) -> None:
        self.stderr_path.parent.mkdir(parents=True, exist_ok=True)
        with self.stderr_path.open("w") as err:
            self.proc = subprocess.Popen(
                self.cmd, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                text=True, encoding="utf-8", errors="replace", bufsize=1, start_new_session=True,
            )
        try:
            self.proc.stdin.write(message)
            self.proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass  # claude exited early; its stderr explains why

    def lines(self) -> Iterator[str]:
        assert self.proc and self.proc.stdout
        yield from self.proc.stdout

    def wait(self) -> int:
        assert self.proc
        return self.proc.wait()

    def stop(self) -> None:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        self.stopped = True
        self._signal(signal.SIGTERM)
        threading.Thread(target=self._kill_after_grace, daemon=True).start()

    def _kill_after_grace(self) -> None:
        try:
            self.proc.wait(timeout=STOP_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            self._signal(signal.SIGKILL)

    def _signal(self, sig: int) -> None:
        try:
            os.killpg(self.proc.pid, sig)  # pgid == pid thanks to start_new_session
        except (ProcessLookupError, PermissionError):
            pass

    def stderr_tail(self, limit: int = 2000) -> str:
        try:
            return self.stderr_path.read_text(errors="replace")[-limit:].strip()
        except OSError:
            return ""
