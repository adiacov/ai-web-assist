# Data Model: Release Process, Update and Downgrade

No stored data. In-memory types only.

## Version

- `major`, `minor`, `patch`: non-negative ints; ordered as a tuple.
- Parsed from `X.Y.Z` or `vX.Y.Z` (surrounding whitespace ignored). Anything else (e.g. `1.0`,
  `v1.0.0-rc1`, `test`) is invalid.
- `tag` → `vX.Y.Z`; `str()` → `X.Y.Z`.

## Release

- `version`: Version
- `date`: `YYYY-MM-DD` (from `published_at`, may be empty)
- Built from GitHub release JSON; drafts, pre-releases and non-version tags are dropped.
  List sorted newest first; latest = first.

## Installation

- `installer`: `uv` | `pipx` | `other`
- `version`: Version of the running awa (`__version__`)

## Update decision

Inputs: installed version, target version, list of released versions.

| Condition | Result |
|---|---|
| target not in releases | refuse: unknown version (exit 2) |
| target == installed | "already on X", nothing changes (exit 0) |
| target > installed | upgrade, no question |
| target < installed | downgrade: ask unless `--yes`; refuse if stdin is not a terminal (exit 1) |
| installer is `other` or its command is missing | print the manual commands (exit 1) |
