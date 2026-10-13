# Feature Specification: Chat Beside Your Files (MVP)

**Feature Branch**: `001-chat-beside-files`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "MVP of AI Web Assist: a generic, installable local 'chat beside your files' workspace. Install once from GitHub, run `awa` (or `ai-web-assist`) in any project folder, and a browser opens on that folder: a file tree, a rendered viewer and a chat with Claude Code that reads and writes the same files." (full description in the conversation that created this spec; the source brief is `.dev/APP-IDEA.md` §8.3)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open any folder as a readable workspace (Priority: P1)

A user who finds the terminal hard to read goes into any project folder, runs one command,
and a browser tab opens showing that folder's files in a tree. Clicking a markdown file shows
it rendered (headings, tables, code blocks with syntax colours); clicking another text file
shows it as highlighted code.

**Why this priority**: Without the workspace, nothing else exists. Reading files comfortably
already beats the terminal on its own.

**Independent Test**: Install the app, run the command in a folder with markdown and code
files, and check that the tree lists them and the viewer renders them.

**Acceptance Scenarios**:

1. **Given** the app is installed, **When** the user runs `awa` in a folder, **Then** a browser
   tab opens on a workspace titled after that folder and listing its files.
2. **Given** the folder has hidden folders, `.git`, and build or dependency folders
   (e.g. `node_modules`, `target`, `dist`, `build`, `__pycache__`, `.venv`), **When** the tree loads,
   **Then** those are not shown.
3. **Given** a markdown file with a table and fenced code in several languages, **When** the user
   opens it, **Then** the table is rendered and each code block is syntax-highlighted.
4. **Given** a markdown file mentions another file as an inline code path (e.g. `docs/plan.md`),
   **When** that file exists, **Then** the path is a link that opens it in the viewer.
5. **Given** a markdown file contains a web link, **When** the user clicks it, **Then** it opens in
   a new browser tab.
6. **Given** the user runs `ai-web-assist` instead of `awa`, **Then** the behaviour is identical.

---

### User Story 2 - Chat with Claude beside the files (Priority: P1)

The user types a message in the chat panel. Claude Code works in the same folder, the reply
streams in live, and the tools it used (e.g. "Edit docs/plan.md") are listed above the reply.
Files that Claude changes get a green dot in the tree; the open file refreshes in place.

**Why this priority**: This is the core value: an AI that shares the files the user is reading.

**Independent Test**: Send "create notes/hello.md with a greeting"; the reply streams, the tool
line appears, the file shows up in the tree with a green dot, and opening it shows the greeting.

**Acceptance Scenarios**:

1. **Given** the workspace is open, **When** the user sends a message, **Then** the reply text
   appears progressively while Claude works, and a "working" status is visible until it finishes.
2. **Given** Claude edits or creates files, **When** the reply finishes (or while it runs),
   **Then** changed files not currently open show a green dot within about 2 seconds, and a
   collapsed folder containing them shows the dot too.
3. **Given** the open file is changed (by Claude or by an external editor), **Then** the viewer
   refreshes it within about 2 seconds without losing the scroll position.
4. **Given** a reply is running, **When** the user clicks Stop, **Then** the reply ends and the
   chat is ready for the next message.
5. **Given** a reply is running, **When** the user tries to send another message (from any tab),
   **Then** it is refused with a clear "still working" message.
6. **Given** Claude's reply mentions a file path in backticks, **Then** the path links to that file.

---

### User Story 3 - Continue where I left off (Priority: P2)

The conversation is one ongoing Claude session. Each new message continues it, and so does
restarting the app or reloading the page: the chat history is shown again and Claude still
remembers the context. "New session" starts fresh: the old chat log is archived, project
files are untouched.

**Why this priority**: Long-running work (learning, research, planning) spans days.

**Independent Test**: Tell Claude a fact, restart the app, ask about the fact; Claude recalls it
and the earlier messages are visible. Click New session; history clears, the archive exists,
and Claude no longer has the context.

**Acceptance Scenarios**:

1. **Given** earlier messages, **When** the user reloads the page or restarts the app, **Then**
   the previous messages (with their tool lines) are shown and the next message continues the
   same Claude session.
2. **Given** a session exists, **When** the user clicks New session and confirms, **Then** the chat
   panel is cleared, the previous log is kept as an archive file, and the next message starts a
   new Claude session.
3. **Given** a reply is running, **Then** New session is unavailable.
4. **Given** the browser tab is closed mid-reply, **Then** Claude finishes the reply, and the reply
   is in the history next time the page loads.

---

### User Story 4 - Per-project configuration (Priority: P2)

A project can ship an optional `.ai-web-assist/config.toml` to set the workspace title, which
folders are shown, extra exclusions, how much Claude may do without asking (permission mode,
allowed tools), the model, the port, and extra instructions for Claude. Without the file,
sensible defaults apply.

**Why this priority**: Different projects need different views (e.g. a course shows only
`course/`) and different levels of trust.

**Independent Test**: Add a config with a title, `include = ["docs"]` and an extra exclude; restart;
the title changes and only `docs/` is shown minus the excluded entries.

**Acceptance Scenarios**:

1. **Given** no config file, **When** the app starts, **Then** it uses the defaults and the title is
   the folder name.
2. **Given** a config with `include` folders, **Then** only those folders' files are shown and
   reachable.
3. **Given** a config with an invalid value or malformed syntax, **When** the app starts, **Then** it
   exits with a clear message naming the file and the problem.
4. **Given** extra prompt text in the config, **Then** Claude receives it in addition to the
   generic workspace instructions.
5. **Given** the app has run once in a project, **Then** `.ai-web-assist/` contains a `.gitignore`
   that ignores chat state but not the config file.

---

### User Story 5 - Personal display settings (Priority: P3)

The user picks a theme (system, light, dark) and a font size, and drags to resize the chat
panel and the message box. The choices persist in that browser.

**Why this priority**: Comfort for long reading sessions; carried over from the existing tool.

**Independent Test**: Change theme, font size and widths; reload; settings are kept.

**Acceptance Scenarios**:

1. **Given** the user picks Dark, **When** the page reloads, **Then** it is dark from the first paint.
2. **Given** the chat panel was resized, **When** the user double-clicks the border, **Then** the
   default width is restored.

---

### Edge Cases

- The chosen port is in use → the app picks the next free port and prints the URL it used.
- The Claude CLI is not installed or not on PATH → the app refuses to start with a clear message.
- Claude exits with an error (not logged in, bad model name) → the error text is shown in the chat.
- A requested path uses `..`, an absolute path, a symlink pointing outside the shown root, a
  hidden file, or the `.ai-web-assist/` folder → it is refused as "not found".
- A binary file is opened → the viewer says it is a binary file instead of showing garbage.
- A very large text file (over 1 MB) → only the first 1 MB is shown, with a notice.
- A very large folder (tens of thousands of files) → the tree lists at most 5,000 files and
  says it was truncated.
- The project folder has no files to show → the viewer explains that the folder is empty.
- A user message starting with `-` or containing quotes/newlines → passed to Claude unchanged.
- The previously opened file was deleted → the viewer falls back to the first file.
- The page is opened in two tabs → both show the same history; only one reply runs at a time.
- The stored chat state file is corrupted → the app starts with an empty history instead of crashing.

## Requirements *(mandatory)*

### Functional Requirements

**Launching**

- **FR-001**: The app MUST be installable once from its GitHub repository with a single command
  and expose two equivalent commands, `awa` and `ai-web-assist`.
- **FR-002**: The command MUST accept an optional folder argument (default: the current folder),
  `--port`, and `--no-browser`; it MUST open the default browser on the workspace unless
  `--no-browser` is given, and print the URL.
- **FR-003**: The app MUST listen on the local loopback address only (`127.0.0.1`).
- **FR-004**: If the port is busy, the app MUST try the following ports (up to 20) and report
  the one used.
- **FR-005**: The app MUST check that the Claude Code CLI is available at start-up and exit with
  a clear message if not.

**File tree and viewer**

- **FR-006**: The tree MUST list files under the shown root, excluding hidden entries, `.git`,
  the app's state folder, and default build/dependency folders (`node_modules`, `target`,
  `dist`, `build`, `__pycache__`, `.venv`, `venv`), plus any configured excludes.
- **FR-007**: The tree MUST group files by folder with collapsible folders; collapse state
  persists per browser.
- **FR-008**: The tree MUST show a change marker on files modified since the user last viewed
  them, and on collapsed folders containing such files; the tree refreshes about every 2 seconds.
- **FR-009**: The viewer MUST render markdown (including tables and fenced code) with
  syntax highlighting for common languages (at least Python, JavaScript/TypeScript, Java,
  Scala, Kotlin, Go, Rust, C/C++, C#, SQL, Bash/shell, YAML, JSON, TOML, HTML/XML, CSS,
  Markdown, Dockerfile), and show other text files as highlighted code chosen by file extension.
- **FR-010**: Rendered content MUST be sanitized so that file content cannot run scripts in
  the page.
- **FR-011**: Inline code spans naming an existing shown file MUST become links that open it;
  web links MUST open in a new tab.
- **FR-012**: The viewer MUST remember the last opened file per browser and refresh it in
  place when it changes on disk, keeping scroll position.
- **FR-013**: Binary files MUST be reported as binary; text files larger than 1 MB MUST be
  truncated with a notice; the tree MUST cap at 5,000 files with a truncation notice.
- **FR-014**: File access MUST be refused for any path outside the shown root (including via
  symlinks), any hidden path segment, and the app's state folder.

**Chat**

- **FR-015**: Sending a message MUST run Claude Code in the project folder, stream the reply
  text to the page as it arrives, and list each tool Claude uses with a short summary
  (file path relative to the project, command, URL or search query).
- **FR-016**: Only one reply MAY run at a time across all tabs; extra sends MUST be refused
  with a clear message.
- **FR-017**: Stop MUST end the running reply.
- **FR-018**: The app MUST keep one ongoing Claude session per project and resume it for every
  message, across page reloads and app restarts.
- **FR-019**: The chat history (user messages, reply text, tool lines, timestamps) MUST be
  saved in the project's state folder and shown again on page load.
- **FR-020**: New session MUST archive the current chat log (never delete it) and start a new
  Claude session on the next message; it MUST be unavailable while a reply runs.
- **FR-021**: If the browser disconnects mid-reply, Claude MUST be allowed to finish and the
  reply MUST be saved to history.
- **FR-022**: Errors from Claude (non-zero exit, error result) MUST be shown in the chat.
- **FR-023**: Claude MUST receive generic workspace instructions: the user sees only chat text
  and files (not tool output); refer to files as project-relative paths in backticks; write
  web links as full `https://` markdown links; keep chat replies short and put long content
  in files. Project-configured extra text MUST be appended.

**Configuration and state**

- **FR-024**: The app MUST read an optional `.ai-web-assist/config.toml` with: `title`,
  `include` (folders to show), `exclude` (extra names to hide), `permission_mode`,
  `allowed_tools`, `model`, `port`, `prompt` (extra instructions). Unknown keys or wrong value
  types MUST stop start-up with a message naming the key.
- **FR-025**: Command-line `--port` MUST override the config `port`.
- **FR-026**: Defaults MUST be: title = folder name; shown = whole folder; permission mode =
  `acceptEdits`; allowed tools = Read, Edit, Write, Glob, Grep, WebFetch, WebSearch, Bash;
  model = Claude's default; port = 8765.
- **FR-027**: All chat state MUST live in `.ai-web-assist/` in the project; the app MUST create a
  `.gitignore` there that ignores everything except `config.toml` (including itself, so an unconfigured project's `git status` stays clean).
- **FR-028**: The UI MUST work with no internet connection (no assets loaded from other origins).

**Display settings**

- **FR-029**: Theme (system/light/dark) and font size (small/medium/large) MUST be selectable
  and persisted per browser, applied before first paint.
- **FR-030**: The chat panel width and message box height MUST be resizable by dragging,
  persisted per browser, and reset by double-click.
- **FR-031**: The workspace title (from config or folder name) MUST appear in the page header
  and the browser tab title.

**Documentation**

- **FR-032**: A README MUST cover install, usage, configuration (with an example config), and
  safety (the chat can edit files and run commands; local single-user use only).

### Key Entities

- **Workspace**: one project folder opened by the app; has a title, a shown root (or include
  list), exclusion rules, and Claude settings.
- **Config**: optional per-project settings file; overrides workspace defaults.
- **Chat state**: the current Claude session identifier plus the ordered list of messages.
- **Message**: role (user, assistant), text, list of tool uses (name + short summary), timestamp.
- **Archive**: a closed chat state, kept as a timestamped file when a new session starts.
- **File entry**: project-relative path and last-modified time, as listed in the tree.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a fresh machine with Claude Code already installed, a user can install the
  app and open a workspace in a new folder in under 2 minutes using only the README.
- **SC-002**: The workspace opens in the browser within 3 seconds of running the command.
- **SC-003**: The first words of a chat reply appear while Claude is still working, not only
  at the end.
- **SC-004**: A file changed by Claude or an external editor is marked in the tree, or refreshed
  in the viewer if open, within 3 seconds.
- **SC-005**: After restarting the app, 100% of earlier messages are shown and Claude answers a
  question that depends on earlier context correctly.
- **SC-006**: 0 of the path-escape attempts in the test suite (traversal, absolute, symlink,
  hidden, state folder) return file content.
- **SC-007**: With networking disabled, the workspace still renders markdown and highlights code.
- **SC-008**: The app works unchanged in at least two different real project folders
  (this repository and `~/Documents/private/projects/learn-code/ai-path/`).

## Assumptions

- Single user, on their own machine; no login. Anyone who can reach `127.0.0.1` on that machine
  can use the chat; this is acceptable and documented.
- Claude Code is installed and logged in separately; the app does not manage Claude accounts.
- Target OS is Linux and macOS. Windows
  may work but is not verified for the MVP.
- Shown folder content is mostly text (markdown and source code).
- Tree refresh by polling every ~2 s is acceptable for folders up to 5,000 files.
- The chat log in `.ai-web-assist/` is kept for the user's reference only; it is not shown as a
  project file and is not deduplicated against any project-specific session notes.
- Out of scope (Parked): multi-user use, in-browser editing, dashboards or structured progress
  data, a Claude Code plugin, multiple parallel chats, background-task views, pinned status file.
