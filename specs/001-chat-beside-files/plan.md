# Implementation Plan: Chat Beside Your Files (MVP)

**Branch**: `001-chat-beside-files` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-chat-beside-files/spec.md`

## Summary

Generalise the Spark tutor web UI (`learn-code/spark/spark-concepts/webapp`) into an installable
Python package, `ai-web-assist`, with the commands `awa` and `ai-web-assist`. A stdlib HTTP server
bound to 127.0.0.1 serves a three-pane UI (tree, viewer, chat) for any project folder. The
chat runs `claude -p` in stream-json mode with `--resume`, and the message goes in on stdin.
Configuration and state live in the project's `.ai-web-assist/` folder. Front-end libraries are
vendored. The work refactors the old single-file server into small, testable modules and
hardens it: Host and Origin guards, process-group stop, and a project-relative path model.

## Technical Context

**Language/Version**: Python ≥ 3.11 (dev machine: 3.12.3); vanilla JavaScript (ES2020) and CSS, no build step

**Primary Dependencies**: none at runtime (stdlib: `http.server`, `tomllib`, `subprocess`, `argparse`,
`json`, `hashlib`, `webbrowser`); vendored front end: marked 18.0.14, DOMPurify 3.4.16,
highlight.js 11.12.0. External program: Claude Code CLI (2.1.296 verified)

**Storage**: plain files in `<project>/.ai-web-assist/` (JSON chat state, archives, log)

**Testing**: pytest (dev dependency group, run with `uv run --group dev pytest`); a fake `claude`
script on `PATH` replays recorded stream-json

**Target Platform**: Linux and macOS desktop, any modern browser

**Project Type**: CLI-launched local web app (single Python package)

**Performance Goals**: workspace opens in under 3 s; tree poll in under 100 ms for 5,000 files; first text chunk shown as soon as Claude emits it

**Constraints**: offline-capable UI; loopback only; no runtime third-party dependencies; time-box 1–2 days

**Scale/Scope**: single user; at most 5,000 files listed; files up to 1 MB rendered; about 6 Python modules plus 3 static files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|---|---|---|---|
| I. Stdlib-Only Runtime | No runtime deps; vendored, pinned front end; no CDN | ✅ | ✅ R3, R4: hatchling is build-time only; vendor/ is pinned |
| II. Local-First & Safe | 127.0.0.1 only; path guard incl. symlinks/hidden/state dir; README safety | ✅ | ✅ R5 adds Host/Origin guards; R6 path model; FR-032 README |
| III. Files Are Source of Truth | All state in `.ai-web-assist/`; archive, never delete | ✅ | ✅ R8; data-model state layout |
| IV. Simplicity & Time-Box | Small modules; no build step; Parked list | ✅ | ✅ 6 modules; vanilla JS; parked items in spec Assumptions |
| V. Tested Core | pytest for path safety, tree, config, stream parsing; fake claude | ✅ | ✅ tests/ layout below; recorded fixture from a real run (R1) |

No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-chat-beside-files/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config.md
│   └── http-api.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml                 # hatchling; scripts awa + ai-web-assist; dev group: pytest
README.md
LICENSE
src/ai_web_assist/
├── __init__.py                # __version__
├── __main__.py                # python -m ai_web_assist
├── cli.py                     # argparse, port selection, claude check, browser open
├── config.py                  # Config dataclass, load_config(), ConfigError
├── files.py                   # Workspace path guard, list_tree(), read_file()
├── state.py                   # ChatStore: load/save/append/archive, ensure_state_dir()
├── claude.py                  # build_command(), StreamParser, tool_summary(), ClaudeRunner (process group)
├── prompt.py                  # generic UI prompt + config extra
├── server.py                  # Handler routes, guards, NDJSON chat streaming, make_server()
└── static/
    ├── index.html             # shell; {{TITLE}} placeholder
    ├── app.css
    ├── app.js
    └── vendor/                # marked, purify, highlight + scala, dockerfile, github(-dark).css, LICENSES
tests/
├── conftest.py                # tmp project fixture, fake claude on PATH, running server fixture
├── fixtures/
│   ├── fake_claude.py         # replays a JSONL file; records argv + stdin
│   └── stream_basic.jsonl     # recorded from a real run (paths anonymised)
├── test_config.py
├── test_files.py
├── test_state.py
├── test_claude.py
├── test_server.py
└── test_cli.py
```

**Structure Decision**: a single Python package in src layout. The UI is static files inside
the package, served by the same process. Tests mirror the modules. `server.py` holds only
HTTP glue; logic lives in `files`, `state` and `claude`, so it can be unit-tested without
sockets.

## Implementation Notes

- **Threading**: `ThreadingHTTPServer`; a module-level `threading.Lock` per server instance
  guards "one reply at a time" (non-blocking acquire, 409 when busy). State writes take a
  separate lock.
- **Chat flow**: acquire lock → append user message → spawn Claude (`stdin=PIPE`, write,
  close; `stdout=PIPE` text, line-buffered; stderr → log file; `cwd=root`;
  `start_new_session=True`) → for each stdout line: `StreamParser.feed()` → emit UI events,
  ignoring `BrokenPipe` → on exit, emit an error with the stderr tail if needed → append the
  assistant message → `done`.
- **UI**: port of the old `index.html`, split into html/css/js. Changes: title from server;
  storage keys prefixed with `workspace_id`; full nested paths in the tree grouped by
  folder; change-marker baseline on first visit; default file = `README.md` → first `.md` →
  first file; binary/truncated notices; language picked from the file extension for
  non-markdown files; an empty-folder message.
- **Generic prompt** (`prompt.py`): user sees only chat text + rendered files, not tool output;
  reference files as project-relative paths in backticks (they become links); full
  `https://` markdown links; keep chat replies short and put long content in files; config
  `prompt` appended under "Project instructions:".

## Complexity Tracking

No constitution violations.
