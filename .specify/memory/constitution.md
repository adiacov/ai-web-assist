# AI Web Assist Constitution

AI Web Assist (package `ai-web-assist`, commands `awa` and `ai-web-assist`) is a small,
installable local app: run one command in any project folder and get a browser workspace
with the folder's files (tree + rendered viewer) next to a chat with Claude Code, which
reads and writes the same files.

## Core Principles

### I. Stdlib-Only Runtime

- The runtime MUST depend only on the Python standard library (Python >= 3.11).
- Front-end libraries (markdown renderer, HTML sanitizer, syntax highlighter) MUST be
  vendored into the package at pinned versions. The UI MUST NOT load anything from a CDN
  or any other network origin at runtime.
- Development-only tools (e.g. pytest) are allowed and MUST NOT be runtime requirements.

Rationale: a one-line install (`uv tool install git+…` or `pipx`) that works offline and
never breaks because of a dependency upgrade.

### II. Local-First & Safe by Default

- The HTTP server MUST bind to `127.0.0.1` only. Binding to other interfaces is out of scope.
- File endpoints MUST resolve paths and refuse anything outside the shown root, including
  symlink escapes, `..` traversal, and hidden (dot) files or folders.
- The app's own state folder (`.ai-web-assist/`) MUST NOT be exposed through the file API.
- The README MUST state plainly that the chat can edit files and run commands in the
  project, and that the app is for single-user local use only.

Rationale: the chat runs Claude Code with edits auto-accepted; the surrounding app must not
widen that blast radius.

### III. Files Are the Source of Truth

- The chat is a remote control; the project's files are the shared memory between user
  and Claude.
- All app state (session id, chat log, archives, config) MUST be plain files in the
  project's `.ai-web-assist/` folder. No hidden server-side or global state.
- Starting a new chat session MUST NOT delete project files or prior chat logs (archive,
  don't destroy).

Rationale: everything the assistant knows is inspectable, editable, and versionable.

### IV. Simplicity & Time-Box

- The MVP is time-boxed to about 1–2 days of work. Features beyond the MVP brief MUST be
  recorded in a Parked list instead of being built.
- Prefer the smallest design that works (YAGNI). Minimal, clean UI; no build step for the
  front end.
- Code MUST be split into small, single-purpose modules with clear names; no module grows
  into a grab bag.

Rationale: this is a side tool; its value is in being used, not polished.

### V. Tested Core

- Server logic MUST have automated pytest coverage: path safety, tree filtering, config
  loading, and Claude stream-event parsing.
- Chat endpoints MUST be testable without the real Claude CLI, using a fake `claude`
  executable that emits recorded stream-json output.
- Each release-ready milestone MUST be verified end-to-end (install as a user would, run in
  another folder) with evidence: commands and their output.

Rationale: the parts most likely to break silently (security checks, CLI output format)
are the ones that must be pinned by tests.

## Technical Constraints

- Packaging: standard `pyproject.toml` package exposing two console scripts, `awa` and
  `ai-web-assist`, pointing at the same entry point.
- Integration with Claude Code is via its CLI in print mode (`claude -p` with
  `--output-format stream-json` and `--resume`). Flags MUST be checked against the
  installed CLI's `--help` or current official docs, not memory.
- Per-project configuration is optional; with no config the app MUST work with sensible
  defaults.

## Development Workflow

- Spec-Driven Development with Spec Kit: constitution → specify → clarify → plan →
  tasks → analyze → implement. Specs and plans live in `specs/NNN-feature/`.
- Commit small and often at logical milestones using Conventional Commits
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Tests MUST pass before each commit that touches code.

## Governance

- This constitution overrides ad-hoc practice. Plans MUST include a Constitution Check
  and justify any deviation in their Complexity Tracking section.
- Amendments: edit this file, bump the version, update the Last Amended date, and commit
  with a `docs: amend constitution` message.
- Versioning: MAJOR for removing or redefining a principle; MINOR for adding a principle
  or materially expanding guidance; PATCH for wording fixes.

**Version**: 1.0.0 | **Ratified**: 2026-10-13 | **Last Amended**: 2026-10-13
