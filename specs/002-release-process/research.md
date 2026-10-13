# Research: Release Process, Update and Downgrade

Checked on 2026-10-13 against the installed tools (uv 0.9.26, pipx 1.4.3, gh 2.45) and the
GitHub releases of the Actions used.

## Single version source

- **Decision**: `__version__` in `src/ai_web_assist/__init__.py`; `pyproject.toml` declares
  `dynamic = ["version"]` with `[tool.hatch.version] path = "src/ai_web_assist/__init__.py"`.
- **Rationale**: works the same in an installed wheel and in a dev checkout, and needs no
  `importlib.metadata` lookup at runtime.
- **Alternatives**: version in pyproject read via `importlib.metadata` (fails in an uninstalled
  checkout); deriving the version from git tags (hatch-vcs: extra build dependency, odd dev versions).

## Where releases come from

- **Decision**: `GET https://api.github.com/repos/adiacov/ai-web-assist/releases?per_page=100`,
  keep entries that are not drafts or pre-releases and whose `tag_name` is `vX.Y.Z`.
- **Rationale**: a Release exists only when the release workflow succeeded, so it's a tested
  version; tags alone may be half-done.
- **Alternatives**: `/tags` (no dates, includes failed releases); `git ls-remote` (needs git).
- Headers: `Accept: application/vnd.github+json`, a `User-Agent` (required by GitHub), timeout 10 s.
  Errors (`URLError`, `HTTPError` incl. 403 rate limit, timeouts, bad JSON) become one
  `ReleaseError` with a short message.

## Detecting the installer

- **Decision**: look at `sys.prefix` (awa's own virtual environment):
  `uv-receipt.toml` present → uv; `pipx_metadata.json` present → pipx; otherwise "other".
- **Rationale**: verified locally: uv tool environments contain `uv-receipt.toml`
  (`~/.local/share/uv/tools/ai-web-assist/uv-receipt.toml`); pipx venvs contain
  `pipx_metadata.json`. This identifies the tool that really installed awa even when both exist.
- If the tool's command is not on `PATH`, fall back to printing the manual command.

## Reinstall command

- **Decision**: uv: `uv tool install --force git+https://github.com/adiacov/ai-web-assist@vX.Y.Z`;
  pipx: `pipx install --force git+https://github.com/adiacov/ai-web-assist@vX.Y.Z`.
  Run with `subprocess.run(list)` (no shell), output streamed to the terminal.
- **Rationale**: both tools accept a git URL with `@ref`; `--force` replaces the existing
  install (verified during implementation, see verification.md). Pinning to the tag also means
  a later `uv tool upgrade` stays on that tag, which is what a downgrade should do.
- Replacing the running environment is safe on Linux/macOS: the running process already loaded
  its modules. After the install, awa reports the new version by running the installed command's
  `--version`.

## Running servers

- **Decision**: always print "Restart any running awa servers to use the new version" after a
  successful update. No process detection.
- **Rationale**: the spec allows best effort; detection (ps parsing) is platform specific and
  adds little.

## Subcommand routing

- **Decision**: in `cli.main`, if `argv[0]` is `version`, `versions` or `update`, parse with that
  subcommand's parser; otherwise use the existing folder parser unchanged. `awa ./version` opens
  the folder.
- **Alternatives**: argparse subparsers (would break `awa path` as positional).

## CI / release workflow

- **Decision**: `actions/checkout@v7`, `astral-sh/setup-uv@v10`, `uv run --group dev pytest`,
  `uv build`; publish with the runner's preinstalled `gh release create` and `GITHUB_TOKEN`
  (`permissions: contents: write`). Release notes: the `## [X.Y.Z]` section of CHANGELOG.md,
  extracted with awk. Tag/version check compares `${GITHUB_REF_NAME#v}` with `__version__`.
- **Alternatives**: `softprops/action-gh-release` (extra third-party action, not needed).

## Release v0.1.0

- `v0.1.0` tags commit `698ea44` (the MVP on main). That commit has no workflow, so its GitHub
  Release is created once by hand with `gh release create` from a local build. This feature ships
  as `v0.2.0` through the new workflow.
- Note: downgrading to 0.1.0 gives a version without `awa update`; moving back up then needs the
  plain uv/pipx command. The README says so.
