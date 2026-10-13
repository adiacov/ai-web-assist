"""Chat state kept as plain files in the project's `.ai-web-assist/` folder."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from ai_web_assist.config import STATE_DIR_NAME

GITIGNORE = "# Created by ai-web-assist: keep chat state out of git, allow committing config.toml.\n*\n!config.toml\n"


def ensure_state_dir(root: Path) -> Path:
    """Create the state folder with a .gitignore that keeps chat state out of git but not the config."""
    state_dir = root / STATE_DIR_NAME
    state_dir.mkdir(exist_ok=True)
    gitignore = state_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(GITIGNORE)
    return state_dir


def _empty() -> dict:
    return {"session_id": None, "messages": []}


class ChatStore:
    """The current chat (`chat.json`) plus archived sessions (`archive/chat-<time>.json`)."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.path = state_dir / "chat.json"
        self.stderr_path = state_dir / "claude-stderr.log"
        self._lock = threading.Lock()

    def load(self) -> dict:
        with self._lock:
            return self._load()

    def set_session(self, session_id: str) -> None:
        with self._lock:
            st = self._load()
            st["session_id"] = session_id
            self._save(st)

    def append(self, role: str, text: str, tools: list[dict] | None = None) -> None:
        with self._lock:
            st = self._load()
            st["messages"].append({"role": role, "text": text, "tools": tools or [], "ts": time.time()})
            self._save(st)

    def archive(self) -> Path | None:
        """Move the current chat to the archive; the next message starts a new Claude session."""
        with self._lock:
            if not self.path.exists():
                return None
            archive_dir = self.state_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            target = archive_dir / f"chat-{stamp}.json"
            n = 1
            while target.exists():
                target = archive_dir / f"chat-{stamp}-{n}.json"
                n += 1
            self.path.replace(target)
            return target

    def _load(self) -> dict:
        try:
            st = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(st, dict) or not isinstance(st.get("messages"), list):
                raise ValueError("unexpected shape")
            st.setdefault("session_id", None)
            return st
        except FileNotFoundError:
            return _empty()
        except (OSError, ValueError):
            # keep the broken file for the user to inspect, start clean
            self.path.replace(self.state_dir / f"chat.corrupt-{int(time.time() * 1000)}.json")
            return _empty()

    def _save(self, st: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)
