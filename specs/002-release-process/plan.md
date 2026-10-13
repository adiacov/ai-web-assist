# Implementation Plan: Release Process, Update and Downgrade

**Branch**: `002-release-process` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-release-process/spec.md`

## Summary

Make releases real, named points (`vX.Y.Z` tags with GitHub Releases), keep the version in one
place, and add `awa version`, `awa versions` and `awa update [--to VERSION] [--yes]`. The update
command finds the installer from markers in awa's own environment (uv's `uv-receipt.toml`, pipx's
`pipx_metadata.json`) and runs `uv tool install --force git+…@vX.Y.Z` or
`pipx install --force git+…@vX.Y.Z`. Releases are read from the GitHub REST API with `urllib`.
A GitHub Actions workflow tests every push/PR; a tag push checks the tag against the version,
tests, builds and publishes the release with `gh release create`.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: none at runtime (stdlib: `argparse`, `urllib.request`, `json`,
`subprocess`). Build: hatchling (dynamic version). CI: GitHub Actions, `astral-sh/setup-uv@v10.2.0` (no moving major tag is published),
`actions/checkout@v7`, preinstalled `gh` CLI.

**Storage**: N/A (no new state files)

**Testing**: pytest; network and subprocess calls injected/faked, no network in tests

**Target Platform**: Linux, macOS

**Project Type**: CLI + local web app (single project)

**Performance Goals**: release check finishes within ~10 s timeout

**Constraints**: stdlib-only runtime; unauthenticated GitHub API (60 requests/hour/IP is plenty)

**Scale/Scope**: 3 subcommands, 2 new modules, 1 workflow, CHANGELOG, README section

## Constitution Check

| Principle | Status |
|---|---|
| I. Stdlib-only runtime | Pass: urllib + subprocess; hatchling is build-time only |
| II. Local-first & safe | Pass: only outbound HTTPS GET to api.github.com on explicit commands; the server is unchanged. Update runs only the user's own installer, never with a shell |
| III. Files are source of truth | Pass: no new state |
| IV. Simplicity | Pass: two small modules (`releases.py`, `update.py`); PyPI parked |
| V. Tested core | Pass: unit tests for version parsing/ordering, routing, installer detection, update decisions, offline errors; end-to-end verification with real uv and pipx installs recorded in `verification.md` |

Re-checked after design: no violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-release-process/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli.md
├── tasks.md
└── verification.md      # evidence, written during implementation
```

### Source Code (repository root)

```text
pyproject.toml                    # version now dynamic, read from __init__.py
CHANGELOG.md                      # new, Keep a Changelog
README.md                         # new "Versions and updates" section, Parked list
.github/workflows/ci.yml          # tests on push / pull_request
.github/workflows/release.yml     # on tag v*: check, test, build, publish
src/ai_web_assist/
├── __init__.py                   # __version__: the single source
├── cli.py                        # routes subcommands before the folder parser
├── releases.py                   # Version parsing/ordering, fetch releases from GitHub
└── update.py                     # installer detection, version/versions/update commands
tests/
├── test_cli.py                   # + routing tests
├── test_releases.py              # new
└── test_update.py                # new
```

**Structure Decision**: single project, extending the existing package with two modules.
