"""Optional per-project settings from `.ai-web-assist/config.toml`."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

STATE_DIR_NAME = ".ai-web-assist"
CONFIG_FILE_NAME = "config.toml"

DEFAULT_PORT = 8765
DEFAULT_PERMISSION_MODE = "acceptEdits"
DEFAULT_ALLOWED_TOOLS = ("Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch", "Bash")
# Choices accepted by `claude --permission-mode` (checked against Claude Code 2.1.296).
PERMISSION_MODES = ("acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan")


class ConfigError(Exception):
    """Raised when the config file is unreadable or has an invalid value."""


@dataclass(frozen=True)
class Config:
    title: str = ""
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    permission_mode: str = DEFAULT_PERMISSION_MODE
    allowed_tools: tuple[str, ...] = DEFAULT_ALLOWED_TOOLS
    model: str = ""
    port: int = DEFAULT_PORT
    prompt: str = ""


def config_path(root: Path) -> Path:
    return root / STATE_DIR_NAME / CONFIG_FILE_NAME


def load_config(root: Path) -> Config:
    """Read the project's config file; return defaults when it does not exist."""
    path = config_path(root)
    if not path.is_file():
        return Config(title=root.name)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        raise ConfigError(f"{path}: {e}") from e
    try:
        return _parse(raw, default_title=root.name)
    except ValueError as e:
        raise ConfigError(f"{path}: {e}") from e


def _parse(raw: dict, default_title: str) -> Config:
    unknown = sorted(set(raw) - set(Config.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown key '{unknown[0]}'")
    values: dict = {}
    if "title" in raw:
        values["title"] = _non_empty_str(raw, "title")
    if "include" in raw:
        values["include"] = tuple(_include_entry(p) for p in _str_list(raw, "include"))
    if "exclude" in raw:
        values["exclude"] = tuple(_str_list(raw, "exclude"))
    if "permission_mode" in raw:
        mode = raw["permission_mode"]
        if mode not in PERMISSION_MODES:
            raise ValueError(f"'permission_mode' must be one of: {', '.join(PERMISSION_MODES)}")
        values["permission_mode"] = mode
    if "allowed_tools" in raw:
        values["allowed_tools"] = _tools(raw["allowed_tools"])
    if "model" in raw:
        values["model"] = _str(raw, "model")
    if "port" in raw:
        port = raw["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("'port' must be an integer between 1 and 65535")
        values["port"] = port
    if "prompt" in raw:
        values["prompt"] = _str(raw, "prompt")
    values.setdefault("title", default_title)
    return Config(**values)


def _str(raw: dict, key: str) -> str:
    if not isinstance(raw[key], str):
        raise ValueError(f"'{key}' must be a string")
    return raw[key]


def _non_empty_str(raw: dict, key: str) -> str:
    value = _str(raw, key).strip()
    if not value:
        raise ValueError(f"'{key}' must not be empty")
    return value


def _str_list(raw: dict, key: str) -> list[str]:
    value = raw[key]
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ValueError(f"'{key}' must be a list of non-empty strings")
    return [v.strip() for v in value]


def _include_entry(entry: str) -> str:
    parts = entry.strip("/").split("/") if not entry.startswith("/") else [""]
    if any(p in ("", "..") or p.startswith(".") for p in parts):
        raise ValueError(f"'include' entry {entry!r} must be a project-relative folder without '..' or hidden parts")
    return "/".join(parts)


def _tools(value) -> tuple[str, ...]:
    if isinstance(value, str):
        tools = [t for t in re.split(r"[\s,]+", value) if t]
    elif isinstance(value, list) and all(isinstance(t, str) for t in value):
        tools = [t.strip() for t in value if t.strip()]
    else:
        raise ValueError("'allowed_tools' must be a string or a list of strings")
    if not tools:
        raise ValueError("'allowed_tools' must not be empty")
    return tuple(tools)
