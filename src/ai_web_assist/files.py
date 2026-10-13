"""The shown project folder: path guard, file tree and file reading."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path

from ai_web_assist.config import STATE_DIR_NAME, Config

# Never shown, on top of hidden names (leading dot) and the project's own excludes.
BUILTIN_EXCLUDES = frozenset({
    ".git", STATE_DIR_NAME, "node_modules", "target", "dist", "build", "__pycache__", ".venv", "venv",
})
MAX_FILES = 5000
MAX_FILE_BYTES = 1024 * 1024
BINARY_SNIFF_BYTES = 8192


class Workspace:
    """A project folder opened by the app. All paths it hands out are project-relative."""

    def __init__(self, root: Path, config: Config):
        self.root = root.resolve()
        self.config = config
        self.workspace_id = hashlib.sha256(str(self.root).encode()).hexdigest()[:12]

    def is_excluded(self, name: str) -> bool:
        return (name.startswith(".") or name in BUILTIN_EXCLUDES
                or any(fnmatch.fnmatch(name, pat) for pat in self.config.exclude))

    def _allowed_parts(self, parts: tuple[str, ...]) -> bool:
        if not parts or any(p in ("", ".", "..") or self.is_excluded(p) for p in parts):
            return False
        if self.config.include:
            rel = "/".join(parts)
            return any(rel == inc or rel.startswith(inc + "/") for inc in self.config.include)
        return True

    def resolve(self, rel: str) -> Path | None:
        """Return the absolute path of a shown file, or None if it is missing or not allowed."""
        if not rel or rel.startswith("/") or "\\" in rel or "\0" in rel:
            return None
        if not self._allowed_parts(tuple(rel.split("/"))):
            return None
        try:
            path = (self.root / rel).resolve()
            real_parts = path.relative_to(self.root).parts  # symlink target must stay inside
        except (OSError, ValueError):
            return None
        if not self._allowed_parts(real_parts) or not path.is_file():
            return None
        return path

    def list_tree(self, limit: int = MAX_FILES) -> tuple[list[dict], bool]:
        """List shown files as [{path, mtime}] sorted by path; the flag tells if it was cut at `limit`."""
        starts = [self.root / inc for inc in self.config.include] if self.config.include else [self.root]
        out: list[dict] = []
        for start in starts:
            if not start.is_dir() or start.is_symlink():
                continue
            for dirpath, dirnames, filenames in os.walk(start):
                dirnames[:] = sorted(d for d in dirnames if not self.is_excluded(d))
                base = Path(dirpath)
                for name in sorted(filenames):
                    if self.is_excluded(name):
                        continue
                    path = base / name
                    rel = path.relative_to(self.root).as_posix()
                    if path.is_symlink() and self.resolve(rel) is None:
                        continue
                    try:
                        mtime = path.stat().st_mtime
                    except OSError:
                        continue
                    out.append({"path": rel, "mtime": mtime})
                    if len(out) > limit:
                        out.sort(key=lambda f: f["path"])
                        return out[:limit], True
        out.sort(key=lambda f: f["path"])
        return out, False

    def read_file(self, rel: str) -> dict | None:
        path = self.resolve(rel)
        if path is None:
            return None
        try:
            with path.open("rb") as f:
                data = f.read(MAX_FILE_BYTES + 1)
            mtime = path.stat().st_mtime
        except OSError:
            return None
        binary = b"\0" in data[:BINARY_SNIFF_BYTES]
        truncated = len(data) > MAX_FILE_BYTES
        content = "" if binary else data[:MAX_FILE_BYTES].decode("utf-8", errors="replace")
        return {"path": rel, "content": content, "mtime": mtime, "binary": binary, "truncated": truncated}

    def relpath(self, value: str) -> str:
        """Make an absolute path inside the project project-relative; leave anything else as is."""
        if not os.path.isabs(value):
            return value
        try:
            return Path(value).resolve().relative_to(self.root).as_posix()
        except (OSError, ValueError):
            return value
