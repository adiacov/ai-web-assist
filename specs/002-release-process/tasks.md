# Tasks: Release Process, Update and Downgrade

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md)

Format: `[ID] [P?] [Story] Description` — `[P]` = can run in parallel (different files).

## Phase 1: Setup / Foundational

- [x] T001 [US1] Make the version dynamic: `pyproject.toml` `dynamic = ["version"]` +
  `[tool.hatch.version]` pointing at `src/ai_web_assist/__init__.py`; refresh `uv.lock`
- [x] T002 [P] [US1] Tag `v0.1.0` on `698ea44`

## Phase 2: User Story 3 — see versions (releases module)

- [x] T003 [P] [US3] Tests for Version parsing/ordering and release JSON filtering in `tests/test_releases.py`
- [x] T004 [US3] `src/ai_web_assist/releases.py`: `Version`, `Release`, `parse_releases`,
  `fetch_releases` (urllib, timeout, `ReleaseError`)
- [x] T005 [US3] `awa version` and `awa versions` in `src/ai_web_assist/update.py`

## Phase 3: User Story 2 — update / downgrade

- [x] T006 [P] [US2] Tests in `tests/test_update.py`: installer detection, commands, decisions
  (unknown, same, upgrade, downgrade with/without `--yes`, no tty, other installer, failure,
  offline)
- [x] T007 [US2] `awa update [--to] [--yes]` in `src/ai_web_assist/update.py`
- [x] T008 [US2] Route `version` / `versions` / `update` in `src/ai_web_assist/cli.py`; routing
  tests in `tests/test_cli.py` (incl. `./version` opens the folder)

## Phase 4: User Story 4 — maintainer release

- [x] T009 [P] [US4] `.github/workflows/ci.yml`: tests on push and pull_request
- [x] T010 [P] [US4] `.github/workflows/release.yml`: on `v*` tag: check tag = version, test,
  build, `gh release create` with changelog notes and dist files

## Phase 5: User Story 5 — docs

- [x] T011 [P] [US5] `CHANGELOG.md` (Keep a Changelog) with 0.1.0 and 0.2.0
- [x] T012 [US5] README: "Versions and updates" section (install a version, update, downgrade,
  check version, folder named `version`, releasing), fix the old update line, add PyPI to Parked

## Phase 6: Release and verification

- [x] T013 Full test suite passes
- [x] T014 Verify `--force` reinstall at a different tag with uv and pipx (isolated dirs)
- [x] T015 Merge to main, push main and `v0.1.0`; publish the v0.1.0 GitHub Release by hand
- [x] T016 Bump to 0.2.0, tag `v0.2.0`, push; check the release workflow and the release
- [x] T017 End-to-end per [quickstart.md](quickstart.md) with uv and pipx; evidence in `verification.md`
- [x] T018 Reinstall the user's own awa at `v0.2.0`

## Dependencies

T001 → T004 → T005 → T007 → T008. T003/T006 before their implementations. T009–T012 independent.
T013–T014 before T015 → T016 → T017 → T018.
