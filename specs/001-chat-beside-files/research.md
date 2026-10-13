# Research: Chat Beside Your Files (MVP)

Date: 2026-10-13. Facts below were checked against the installed tools or live registries,
not from memory.

## R1. Claude Code CLI integration

- **Decision**: Run `claude -p --output-format stream-json --verbose --include-partial-messages
  --permission-mode <mode> --allowedTools "<tools>" --append-system-prompt <prompt>
  [--model <m>] [--resume <session_id>]` in the project folder. Send the user's message on
  **stdin** (then close stdin) instead of as a positional argument.
- **Evidence**: `claude --help` on Claude Code 2.1.296 lists all these flags; permission
  modes are `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan`. A probe run piping
  the prompt on stdin produced a normal stream-json run (exit 0, 45 events), and a follow-up
  `--resume <id>` with stdin input returned the same `session_id` and remembered the file it
  had read.
- **Event shapes observed** (used by the parser and recorded as a test fixture):
  - `{"type":"system","subtype":"init","session_id":…}`: session id to persist.
  - `{"type":"stream_event","parent_tool_use_id":null,"event":{"type":"content_block_delta",
    "delta":{"type":"text_delta","text":…}}}`: live text.
  - `{"type":"stream_event","event":{"type":"content_block_start","content_block":{"type":"text"}}}`:
    a new text block starts (insert a paragraph break if text already exists).
  - `{"type":"assistant","parent_tool_use_id":null,"message":{"content":[{"type":"tool_use",
    "name":"Read","input":{"file_path":…}}]}}`: tool use with full input.
  - `{"type":"result","subtype":"success","is_error":false,…}`: end; `is_error:true` → show error.
  - Other types (`system/hook_*`, `system/status`, `rate_limit_event`, `user`, thinking blocks)
    are ignored. Events with a non-null `parent_tool_use_id` come from sub-agents and are ignored.
- **Rationale**: stdin avoids argv issues (messages starting with `-`, very long messages,
  the variadic `--allowedTools` swallowing a trailing positional). Stream-json gives live
  text plus tool calls.
- **Alternatives**: Claude Agent SDK (Python) adds a third-party runtime dependency, which
  violates Principle I. `--input-format stream-json` (a long-lived process) is more complex,
  and one process per message is enough.

## R2. Stopping a running reply

- **Decision**: Start Claude with `start_new_session=True` and stop it with
  `os.killpg(pgid, SIGTERM)`, escalating to `SIGKILL` after 5 s.
- **Rationale**: Claude spawns child processes (e.g. Bash tools). Terminating only the parent
  can leave orphans. A process group stops them all.
- **Alternatives**: `proc.terminate()` (old code) can leave children running.

## R3. Packaging and install

- **Decision**: A `pyproject.toml` with a hatchling build backend and src layout
  (`src/ai_web_assist/`). It declares two `[project.scripts]` entries, `awa` and
  `ai-web-assist`, both pointing at `ai_web_assist.cli:main`. `requires-python = ">=3.11"`, with
  no runtime dependencies. Install with
  `uv tool install git+https://github.com/<user>/ai-web-assist` (uv 0.9.26 installed) or
  `pipx install git+https://github.com/<user>/ai-web-assist` (pipx 1.4.3 installed).
- **Rationale**: Hatchling puts every file under the package directory into the wheel, so
  `static/` and the vendored libraries ship without extra config. Both installers create an
  isolated environment and put both commands on PATH.
- **Alternatives**: setuptools needs `package-data` configuration. A single-file zipapp is
  harder to update and has no standard install path.

## R4. Front-end libraries (vendored)

- **Decision**: Vendor pinned copies under `src/ai_web_assist/static/vendor/`:
  - `marked` **18.0.14** (`lib/marked.umd.js`), released 2026-09-22
  - `dompurify` **3.4.16** (`dist/purify.min.js`), released 2026-09-23
  - `highlight.js` **11.12.0** via `@highlightjs/cdn-assets` (`highlight.min.js`, the common
    bundle, plus `languages/scala.min.js`, `languages/dockerfile.min.js`, and
    `styles/github.min.css` / `styles/github-dark.min.css`), released 2026-08-12
  - Each library's license notice is kept next to the files.
- **Evidence**: npm registry and jsDelivr file listings checked 2026-10-13. The common bundle
  contains: bash, c, cpp, csharp, css, diff, go, graphql, ini (aliased as toml), java,
  javascript, json, kotlin, less, lua, makefile, markdown, objectivec, perl, php, plaintext,
  python, r, ruby, rust, scss, shell, sql, swift, typescript, vbnet, wasm, xml (html), yaml.
  Together with scala and dockerfile, this covers every language FR-009 requires.
- **Rationale**: The UI works offline, nothing is fetched from third parties, and versions are
  reproducible (Principle I). Versions are at least 3 weeks old as a supply-chain precaution.
  Total size is about 200 KB.
- **Alternatives**: CDN (old approach): needs internet, and third-party requests on every load.

## R5. Local-server safety (beyond binding to loopback)

- **Decision**: Bind `127.0.0.1` only, and add two cheap checks:
  1. **Host header allow-list**: accept only `127.0.0.1:<port>` and `localhost:<port>`.
     This blocks DNS-rebinding attacks, where a malicious website points its own domain at
     127.0.0.1 and then calls the API.
  2. **State-changing requests** (`POST`) must carry `Content-Type: application/json`, and if
     an `Origin` header is present it must match the server's own origin. A cross-site page
     then cannot send a "simple" request that runs the chat without a CORS preflight, and
     the server never answers preflights.
- **Rationale**: The chat can run Bash. Loopback binding alone does not stop a browser tab
  on another site from reaching the server. These checks are about 15 lines of code.
- **Alternatives**: a per-launch random token in the URL is stronger, but it makes URLs
  unbookmarkable. Parked as a post-MVP option.

## R6. Path safety and tree listing

- **Decision**: All file paths in the API are **project-relative** (e.g. `docs/plan.md`), even
  when `include` limits the shown folders. Resolution: reject absolute paths and empty paths;
  `resolve()` the joined path and require it to be inside the project root; reject any part
  that starts with `.` or matches an exclude name; when `include` is set, require the path to
  be under one of the included folders. The tree uses `os.walk(followlinks=False)` and applies
  the same check to every entry, so symlinks pointing outside are skipped.
- **Rationale**: Project-relative paths match how Claude refers to files, so links in chat
  replies just work. The old code needed a `course/` prefix-stripping hack for this.

## R7. Per-browser settings when several projects share a port

- **Decision**: Browser storage keys for per-project items (last opened file, seen mtimes,
  folded folders) are prefixed with a workspace id: a short hash of the project's absolute
  path, served by `/api/config`. Theme, font and sizes stay global.
- **Rationale**: Browser storage is per origin (`127.0.0.1:8765`). Without a prefix, two
  projects opened on the same port would mix their "seen" markers.
- **Change-marker baseline**: on the first visit to a workspace, every current file counts as
  seen. Only files created or modified afterwards get the green dot. (The old code marked
  everything on first load.)

## R8. Chat state persistence

- **Decision**: `.ai-web-assist/chat.json` holds `{session_id, messages[]}`, written atomically
  (temp file + `os.replace`). New session moves it to
  `.ai-web-assist/archive/chat-YYYYMMDD-HHMMSS.json`. Claude's stderr from the last run goes to
  `.ai-web-assist/claude-stderr.log`. On first run the app creates
  `.ai-web-assist/.gitignore` containing `*`, `!.gitignore`, `!config.toml`. A corrupt
  `chat.json` is renamed to `chat.corrupt-<ts>.json` and the app starts with empty state.
- **Rationale**: plain inspectable files (Principle III). Archives are never deleted.

## R9. Configuration

- **Decision**: `tomllib` (stdlib, 3.11+) reads `.ai-web-assist/config.toml` into a frozen
  dataclass. Allowed keys: `title` (str), `include` (list[str]), `exclude` (list[str]),
  `permission_mode` (one of the CLI's choices), `allowed_tools` (list[str] or str), `model` (str),
  `port` (int, 1–65535), `prompt` (str). An unknown key or wrong type raises `ConfigError` with
  the key name, and the CLI exits with code 2.
- **Alternatives**: environment variables (old Makefile approach) are kept out of the MVP. The
  config file is per project and can be committed.
