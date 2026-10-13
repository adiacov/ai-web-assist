"""Released versions of awa, read from the GitHub releases of the repository."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

from ai_web_assist import __version__

REPO = "adiacov/ai-web-assist"
REPO_URL = f"https://github.com/{REPO}"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases?per_page=100"
TIMEOUT = 10

_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


class ReleaseError(Exception):
    """The list of releases could not be fetched or read."""


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Version | None:
        """`X.Y.Z` or `vX.Y.Z`; anything else (pre-releases included) gives None."""
        m = _VERSION_RE.fullmatch(text.strip())
        return cls(*map(int, m.groups())) if m else None

    @property
    def tag(self) -> str:
        return f"v{self}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Release:
    version: Version
    date: str = ""


def installed_version() -> Version:
    v = Version.parse(__version__)
    assert v is not None, f"bad __version__ {__version__!r}"
    return v


def parse_releases(data: object) -> list[Release]:
    """Published, non-pre-release `vX.Y.Z` releases from the GitHub API JSON, newest first."""
    if not isinstance(data, list):
        raise ReleaseError("unexpected answer from GitHub")
    found: dict[Version, Release] = {}
    for item in data:
        if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):
            continue
        v = Version.parse(str(item.get("tag_name", "")))
        if v:
            found[v] = Release(v, str(item.get("published_at") or "")[:10])
    return sorted(found.values(), key=lambda r: r.version, reverse=True)


def _get_json(url: str) -> object:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"ai-web-assist/{__version__}",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def fetch_releases(get_json: Callable[[str], object] = _get_json) -> list[Release]:
    try:
        return parse_releases(get_json(RELEASES_API))
    except urllib.error.HTTPError as e:
        hint = " (GitHub rate limit; try again later)" if e.code in (403, 429) else ""
        raise ReleaseError(f"GitHub answered {e.code} {e.reason}{hint}") from e
    except urllib.error.URLError as e:
        raise ReleaseError(f"could not reach GitHub ({e.reason})") from e
    except (TimeoutError, OSError) as e:
        raise ReleaseError(f"could not reach GitHub ({e})") from e
    except ValueError as e:
        raise ReleaseError("unreadable answer from GitHub") from e
