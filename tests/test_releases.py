import io
import json
import urllib.error

import pytest

from ai_web_assist import __version__, releases
from ai_web_assist.releases import Release, ReleaseError, Version


def test_parse_versions():
    assert Version.parse("v1.2.3") == Version(1, 2, 3)
    assert Version.parse(" 0.10.0\n") == Version(0, 10, 0)
    for bad in ("1.2", "v1.2.3-rc1", "test", "", "1.2.3.4", "vv1.2.3"):
        assert Version.parse(bad) is None, bad


def test_version_order_and_text():
    assert Version(0, 10, 0) > Version(0, 9, 9) > Version(0, 9, 1)
    assert str(Version(1, 0, 2)) == "1.0.2" and Version(1, 0, 2).tag == "v1.0.2"


def test_installed_version_matches_package():
    assert str(releases.installed_version()) == __version__


def test_parse_releases_filters_and_sorts():
    data = [
        {"tag_name": "v0.1.0", "published_at": "2026-10-13T10:00:00Z"},
        {"tag_name": "v0.10.0", "published_at": "2026-12-01T10:00:00Z"},
        {"tag_name": "v0.2.0", "draft": True},
        {"tag_name": "v0.3.0", "prerelease": True},
        {"tag_name": "v0.4.0-rc1"},
        {"tag_name": "nightly"},
        {"tag_name": "v0.9.0", "published_at": None},
    ]
    assert releases.parse_releases(data) == [
        Release(Version(0, 10, 0), "2026-12-01"),
        Release(Version(0, 9, 0), ""),
        Release(Version(0, 1, 0), "2026-10-13"),
    ]


def test_parse_releases_rejects_non_list():
    with pytest.raises(ReleaseError):
        releases.parse_releases({"message": "Not Found"})


def test_fetch_uses_api_url():
    seen = []
    def get(url):
        seen.append(url)
        return [{"tag_name": "v1.0.0"}]
    assert releases.fetch_releases(get) == [Release(Version(1, 0, 0))]
    assert seen == [releases.RELEASES_API]


@pytest.mark.parametrize("error, text", [
    (urllib.error.URLError("Name or service not known"), "could not reach GitHub"),
    (urllib.error.HTTPError(releases.RELEASES_API, 403, "Forbidden", {}, io.BytesIO()), "rate limit"),
    (TimeoutError("timed out"), "could not reach GitHub"),
    (json.JSONDecodeError("bad", "x", 0), "unreadable"),
])
def test_fetch_errors_become_release_error(error, text):
    def get(url):
        raise error
    with pytest.raises(ReleaseError, match=text):
        releases.fetch_releases(get)
