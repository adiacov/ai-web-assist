# Verification: 002 Release Process

Date: 2026-10-13. uv 0.9.26, pipx 1.4.3, Linux. Releases from GitHub (not local builds).

## Automated

- `uv run --group dev pytest -q` → `143 passed` (no network).
- CI workflow on GitHub: ubuntu-latest and macos-latest × Python 3.11 and 3.13, all green.
  (The first run failed: `astral-sh/setup-uv@v10` does not exist as a moving tag; pinned to v10.2.0.)

## Release workflow

- Tag `v0.2.0` → Release run green in 20 s; release `v0.2.0` published by github-actions with
  the 0.2.0 changelog section as notes and `ai_web_assist-0.2.0-py3-none-any.whl` +
  `ai_web_assist-0.2.0.tar.gz` attached.
- Tag `v0.2.1` on a 0.2.0 commit → run failed at "Check the tag matches the package version"
  (`Tag v0.2.1 does not match the package version 0.2.0`); no release created. Tag deleted.
- `v0.1.0` (commit 698ea44, before any workflow) published by hand with `gh release create`,
  files built from that commit.
- Fixed during release: notes for the oldest section included the changelog's link references;
  the extractor now stops at them, and the v0.1.0 notes were corrected.

## End to end (isolated `UV_TOOL_DIR`/`PIPX_HOME`, installs from GitHub)

uv, installed at `v0.2.0`:

```text
$ awa --version            → ai-web-assist 0.2.0
$ awa version              → ai-web-assist 0.2.0 (installed with uv) / You have the latest release.
$ awa versions             → * 0.2.0  2026-10-13  (installed) /   0.1.0  2026-10-13
$ awa update               → Already on 0.2.0.                        [exit 0]
$ awa update --to 9.9.9    → awa: there is no release 9.9.9. See `awa versions`.   [exit 2]
$ awa update --to v0.1.0 </dev/null
                           → awa: downgrading from 0.2.0 to 0.1.0 needs --yes when not run in a terminal. [exit 1]
in a terminal, answer n    → Downgrade from 0.2.0 to 0.1.0? [y/N] Cancelled.
in a terminal, answer y    → Updating 0.2.0 → 0.1.0 with uv… / Now on 0.1.0. / Restart any running awa servers…
$ awa --version            → ai-web-assist 0.1.0
$ uv tool install --force git+…@v0.2.0 ; awa --version → ai-web-assist 0.2.0
```

pipx, installed at `v0.2.0`:

```text
$ awa version                    → ai-web-assist 0.2.0 (installed with pipx) / You have the latest release.
$ awa update --to 0.1.0 --yes    → Updating 0.2.0 → 0.1.0 with pipx… / Now on 0.1.0. [exit 0]
$ awa --version                  → ai-web-assist 0.1.0
$ pipx install --force git+…@v0.2.0 ; awa --version → ai-web-assist 0.2.0
$ awa update                     → Already on 0.2.0.
```

Offline (`HTTPS_PROXY=http://127.0.0.1:9`):

```text
$ awa version   → ai-web-assist 0.2.0 (installed with uv) / Could not check the latest release: could not reach GitHub ([Errno 111] Connection refused)  [exit 0]
$ awa versions  → awa: could not list releases: could not reach GitHub (…)  [exit 1]
$ awa update    → awa: could not list releases: could not reach GitHub (…)  [exit 1]
```

Dev checkout (`uv run awa update --to 0.1.0 --yes`): prints "awa was not installed with uv or
pipx…" and both manual commands, exit 1, nothing changed.

The maintainer's own install was moved to v0.2.0: `uv tool list` → `ai-web-assist v0.2.0`.
