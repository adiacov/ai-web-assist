---
description: "Task list for 001-chat-beside-files (MVP)"
---

# Tasks: Chat Beside Your Files (MVP)

**Input**: Design documents from `/specs/001-chat-beside-files/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution Principle V requires pytest coverage for path safety, tree
filtering, config loading and stream parsing, with a fake `claude` for chat tests.

**Organization**: Tasks are grouped by user story; each story phase ends in a commit.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create `pyproject.toml` (hatchling build backend; name `ai-web-assist`; version `0.1.0`; `requires-python = ">=3.11"`; no dependencies; `[project.scripts]` `awa` and `ai-web-assist` → `ai_web_assist.cli:main`; `[dependency-groups] dev = ["pytest>=8"]`; pytest `testpaths = ["tests"]`)
- [X] T002 [P] Create package skeleton `src/ai_web_assist/__init__.py` (`__version__ = "0.1.0"`) and `src/ai_web_assist/__main__.py` (calls `cli.main()`)
- [X] T003 [P] Extend `.gitignore` with `.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`
- [X] T004 [P] Vendor front-end libs into `src/ai_web_assist/static/vendor/`: `marked.umd.js` (marked 18.0.14), `purify.min.js` (dompurify 3.4.16), `highlight.min.js` + `scala.min.js` + `dockerfile.min.js` + `github.min.css` + `github-dark.min.css` (@highlightjs/cdn-assets 11.12.0), and a `LICENSES.md` naming each version and license
- [X] T005 [P] Add `LICENSE` (MIT) at the repo root

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T006 [P] Write `tests/test_config.py`: defaults when the file is missing; every key parsed; unknown key → `ConfigError` naming the key; wrong types (`port` not an int or out of 1–65535, `include` not a list of str, bad `permission_mode` not in `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan`); `include` entries containing `..`, starting with `/` or `.` are rejected; `allowed_tools` given as str or list; invalid TOML → `ConfigError` containing the file path
- [X] T007 Implement `src/ai_web_assist/config.py`: frozen `Config` dataclass (title, include, exclude, permission_mode, allowed_tools: tuple[str], model, port, prompt), `DEFAULT_ALLOWED_TOOLS`, `PERMISSION_MODES`, `load_config(root: Path) -> Config` reading `root/.ai-web-assist/config.toml`; title defaults to `root.name`
- [X] T008 [P] Write `tests/test_files.py`: tree excludes hidden, `.git`, `.ai-web-assist`, `node_modules`, `target`, `dist`, `build`, `__pycache__`, `.venv`, `venv`, and configured globs; `include` limits the tree; tree is sorted and capped (`limit` param) with `truncated`; symlink to outside is skipped; `resolve()` refuses `..`, absolute paths, hidden segments, the state dir, excluded names, paths outside `include`, and symlink escapes; `read_file` reports binary (NUL in the first 8 KB) and truncates at 1 MB
- [X] T009 Implement `src/ai_web_assist/files.py`: `Workspace(root, config)` with `resolve(rel) -> Path | None`, `list_tree(limit=5000) -> (list[dict], bool)`, `read_file(rel) -> dict | None`, `relpath(abs_or_rel_str) -> str` (project-relative when inside root), `workspace_id` (sha256(str(root))[:12]); `BUILTIN_EXCLUDES`
- [X] T010 [P] Write `tests/test_state.py`: load of missing file → empty state; append + reload; atomic save leaves no `.tmp`; archive moves to `archive/chat-YYYYMMDD-HHMMSS.json` and is never overwritten (suffix if same second); corrupt `chat.json` → renamed to `chat.corrupt-<ts>.json` + empty state; `ensure_state_dir` writes `.gitignore` with `*`, `!.gitignore`, `!config.toml` and does not overwrite an existing one
- [X] T011 Implement `src/ai_web_assist/state.py`: `ensure_state_dir(root)`, `ChatStore(state_dir)` with `load()`, `set_session(id)`, `append(role, text, tools=None)`, `archive()`, `stderr_path`; internal lock for writes

**Checkpoint**: `uv run --group dev pytest` green → commit `feat: config, workspace path guard and chat state`

---

## Phase 3: User Story 1 - Open any folder as a readable workspace (P1) 🎯 MVP

**Goal**: `awa` in any folder opens a browser on a tree + rendered viewer.

**Independent Test**: run `awa --no-browser` in a temp folder with md/code files; `GET /api/tree` lists them; the page renders markdown and code.

- [ ] T012 [P] [US1] Write `tests/test_server.py` (part 1) with a `server` fixture in `tests/conftest.py` (temp project, `make_server(workspace, port=0)` in a thread): `GET /` returns HTML with the escaped title; `/static/app.js` served with JS content type; `/static/../config.py` → 404; `/api/config` fields; `/api/tree`; `/api/file` ok/404 for traversal and hidden; a bad `Host` header → 403; POST without JSON content type → 403; a mismatched `Origin` → 403
- [ ] T013 [US1] Implement `src/ai_web_assist/server.py`: `make_server(workspace, store, runner_factory, port) -> ThreadingHTTPServer` bound to `127.0.0.1`; `Handler` with Host/Origin/content-type guards (research R5), routes `/`, `/static/*`, `/api/config`, `/api/tree`, `/api/file`, `/api/history` per `contracts/http-api.md`; quiet logging
- [ ] T014 [P] [US1] Create `src/ai_web_assist/static/index.html`: three-pane shell from the old UI (aside tree with title + settings gear, main viewer, chat section), `{{TITLE}}` in `<title>` and `<h1>`, vendored scripts/styles only, pre-paint theme/font script
- [ ] T015 [P] [US1] Create `src/ai_web_assist/static/app.css`: port the old styles (CSS variables for light/dark, panes, tree, markdown, chat, resizers, responsive breakpoint) plus `.notice` for binary/truncated/empty messages and nested tree indentation
- [ ] T016 [US1] Create `src/ai_web_assist/static/app.js` (viewer part): storage helpers prefixed with `workspace_id`; tree rendering grouped by folder with fold state; seen-mtime change markers with a first-visit baseline (research R7); `openFile` with markdown via marked + DOMPurify, other text highlighted by extension, binary/truncated notices; `linkify` (backticked existing paths → links, `http` links → new tab); default file README.md → first .md → first file; 2 s polling refresh keeping scroll
- [ ] T017 [P] [US1] Write `tests/test_cli.py`: `parse_args` defaults; `--port` overrides config; `find_free_port` skips a busy port (bind a socket in the test); a missing `claude` → exit 1 with a message; a bad config → exit 2; `--version`
- [ ] T018 [US1] Implement `src/ai_web_assist/cli.py`: argparse (`path`, `--port`, `--no-browser`, `--version`), load config (exit 2 on `ConfigError`), `shutil.which("claude")` check (exit 1), `ensure_state_dir`, bind the first free port among 20 (exit 1 if none), print the banner from `contracts/cli.md`, open the browser via `threading.Timer`, `serve_forever` with clean Ctrl+C (stops the runner)

**Checkpoint**: tests green; manual `uv run awa` shows tree + viewer → commit `feat(us1): workspace server, tree and viewer UI`

---

## Phase 4: User Story 2 - Chat with Claude beside the files (P1)

**Goal**: Stream Claude replies with tool lines; one reply at a time; Stop; change markers.

**Independent Test**: with the fake claude, `POST /api/chat` streams text/tool/done events and saves history; a second concurrent POST → 409; stop kills the process.

- [ ] T019 [P] [US2] Add `tests/fixtures/stream_basic.jsonl` (recorded from a real run, paths anonymised; includes init, thinking, tool_use Read, text deltas across two text blocks, result) and `tests/fixtures/fake_claude.py` (prints the JSONL named by `FAKE_CLAUDE_STREAM`, sleeps `FAKE_CLAUDE_DELAY` between lines, writes argv + stdin to `FAKE_CLAUDE_RECORD`, exits with `FAKE_CLAUDE_EXIT`, writes `FAKE_CLAUDE_STDERR` to stderr); a conftest fixture puts an executable `claude` wrapper on `PATH`
- [ ] T020 [P] [US2] Write `tests/test_claude.py`: `build_command` includes the required flags, `--resume` only when a session exists, `--model` only when set, and no message in argv; `StreamParser` yields text chunks, `\n\n` between text blocks, tool events with project-relative summaries, error on `is_error`, captures `session_id`, ignores sub-agent (`parent_tool_use_id` set) and unknown events, tolerates non-JSON lines; `tool_summary` key priority and 160-char cap
- [ ] T021 [US2] Implement `src/ai_web_assist/prompt.py`: `GENERIC_PROMPT` (per plan Implementation Notes) and `build_prompt(config) -> str` appending `"\n\nProject instructions:\n" + config.prompt` when set
- [ ] T022 [US2] Implement `src/ai_web_assist/claude.py`: `build_command(config, session_id, system_prompt)`, `tool_summary(name, input, workspace)`, `StreamParser(workspace)` with `feed(event) -> list[dict]`, `session_id`, `text`, `tools`; `ClaudeRunner(workspace, cwd)` with `start(message, session_id, stderr_path)` (stdin write + close, `start_new_session=True`), `lines()`, `stop()` (killpg SIGTERM → SIGKILL after 5 s), `wait()`
- [ ] T023 [US2] Write `tests/test_server.py` (part 2, chat): stream events in order ending with `done`; user + assistant messages persisted with tools; the message is received on stdin; empty message → 400; concurrent chat → 409; `/api/stop` ends a slow fake run; a non-zero exit with stderr → error event; a client disconnect mid-stream still saves the reply
- [ ] T024 [US2] Add chat routes to `src/ai_web_assist/server.py`: `POST /api/chat` (non-blocking lock, NDJSON streaming, `BrokenPipe`-tolerant emit, save on finish), `POST /api/stop`
- [ ] T025 [US2] Add the chat UI to `src/ai_web_assist/static/app.js`: message rendering (user plain, assistant markdown + tool lines, error), NDJSON reader, busy state + status text, Enter to send / Shift+Enter for a newline, Stop button, refresh the tree after the reply, linkify paths in replies, show "still working" from history on load

**Checkpoint**: tests green; manual chat with real claude works → commit `feat(us2): streaming chat with Claude Code`

---

## Phase 5: User Story 3 - Continue where I left off (P2)

**Goal**: History and session resume across reloads/restarts; New session archives.

**Independent Test**: after a chat, a new server on the same project returns the same history and passes `--resume <id>`; `/api/new` archives.

- [ ] T026 [P] [US3] Write `tests/test_server.py` (part 3): `/api/history` after a chat returns messages + `session_id`; the next chat passes `--resume <id>` to claude (via the fake record); `/api/new` archives `chat.json` and the next chat has no `--resume`; `/api/new` while busy → 409; a restarted server (new instance, same project) returns the same history
- [ ] T027 [US3] Add `POST /api/new` to `src/ai_web_assist/server.py` and make sure the `session_id` from the init event is saved as soon as it arrives
- [ ] T028 [US3] Add to `src/ai_web_assist/static/app.js`: load history on start (render tools), a New session button with confirm, disabled while busy

**Checkpoint**: tests green → commit `feat(us3): session resume and new-session archive`

---

## Phase 6: User Story 4 - Per-project configuration (P2)

**Goal**: The config file controls title, shown folders, Claude settings, extra prompt.

**Independent Test**: config with title + `include` + `exclude` + `prompt`; `/api/config` title, the tree limited, and claude argv contains the prompt text and the configured flags.

- [ ] T029 [P] [US4] Write `tests/test_server.py` (part 4, config): the configured title in `/` and `/api/config`; `include`/`exclude` applied to the tree and file access; `permission_mode`, `allowed_tools`, `model`, and the extra prompt appear in the fake claude argv
- [ ] T030 [US4] Wire config end to end in `src/ai_web_assist/cli.py` and `src/ai_web_assist/server.py` (config port as the default; the `--port` override) and fix any gaps found by T029
- [ ] T031 [P] [US4] Add an example config `docs/config.example.toml` mirroring `contracts/config.md`

**Checkpoint**: tests green → commit `feat(us4): per-project config`

---

## Phase 7: User Story 5 - Personal display settings (P3)

**Goal**: Theme, font size, resizable chat and input, persisted per browser.

**Independent Test**: manual: change settings, reload, the settings persist; double-click resets.

- [ ] T032 [US5] Add the settings popover logic to `src/ai_web_assist/static/app.js` (theme system/light/dark with hljs stylesheet switching, font small/medium/large, chat width resizer, input height resizer, double-click reset, Escape/outside click closes) using global (non-workspace) storage keys

**Checkpoint**: commit `feat(us5): display settings`

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T033 [P] Write `README.md`: what it is, requirements, install (`uv tool install git+…`, `pipx`), usage (`awa [PATH] [--port] [--no-browser]`), config (link to the example), state folder and git, safety (edits auto-accepted, Bash allowed, loopback-only plus Host/Origin guards, single user, `permission_mode = "manual"`/`plan` for read-only), troubleshooting, development (tests), Parked list
- [ ] T034 Run quickstart.md §1–§2: `uv run --group dev pytest -q`; `uv tool install --force .`; `awa --version`; `ai-web-assist --version`; record the output
- [ ] T035 Run quickstart.md §3–§5 in `~/Documents/private/projects/learn-code/ai-path/` (do not commit anything there; remove test files created by the chat afterwards); record evidence in `specs/001-chat-beside-files/verification.md`
- [ ] T036 Mark the tasks done in this file; final commit `docs: verification evidence and README`

---

## Dependencies & Execution Order

- Setup (T001–T005) → Foundational (T006–T011) → US1 (T012–T018) → US2 (T019–T025) → US3 (T026–T028) → US4 (T029–T031) → US5 (T032) → Polish (T033–T036).
- US2 depends on US1 (server + UI shell). US3 depends on US2 (chat). US4 depends on the Foundational config plus US1/US2 wiring. US5 depends only on the US1 UI shell.
- Within each phase, tests marked [P] are written before the implementation they cover.

## Parallel Opportunities

- Setup: T002, T003, T004, T005 together after T001.
- Foundational: the test files T006, T008, T010 together; then T007, T009, T011 (different files).
- US1: T012, T014, T015, T017 in parallel; T013 → T016 → T018.
- US2: T019, T020 in parallel; then T021 → T022 → T023 → T024 → T025.

## Implementation Strategy

1. MVP slice = Setup + Foundational + US1 + US2: a readable workspace plus chat. This is already
   useful.
2. Add US3 (resume) and US4 (config): needed for real use in ai-path.
3. US5 is comfort; Polish delivers the README and verification evidence (constitution V).
4. Commit at every checkpoint.
