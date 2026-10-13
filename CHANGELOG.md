# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- `main` only holds released code (development happens on `dev`), so installing from the
  repository without a version gets the latest release. Releases must be tagged on `main`.

## [0.2.0] - 2026-10-13

### Added

- `awa version`: show the installed version and whether a newer release exists.
- `awa versions`: list released versions, newest first.
- `awa update`: update to the latest release; `awa update --to v0.1.0` moves to a given
  release (asks before downgrading; `--yes` skips the question). Works for uv and pipx installs.
- Release process: version tags, this changelog, tests on every push and pull request, and
  GitHub Releases published automatically from a version tag.

### Changed

- The version number is defined only in `src/ai_web_assist/__init__.py`.

## [0.1.0] - 2026-10-13

### Added

- First release: run `awa` in a folder for a browser workspace with a file tree, a rendered
  viewer and a streaming chat with Claude Code; session resume and archive, per-project
  `.ai-web-assist/config.toml`, theme and font settings, resizable panels.

[Unreleased]: https://github.com/adiacov/ai-web-assist/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/adiacov/ai-web-assist/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adiacov/ai-web-assist/releases/tag/v0.1.0
