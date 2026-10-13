# AI Web Assist

Chat with [Claude Code](https://docs.claude.com/en/docs/claude-code) beside your project's files,
in a local browser workspace.

Run one command in any folder and a browser tab opens with three panes:

- **Files**: the project's file tree. A green dot marks files changed since you last looked.
- **Viewer**: rendered markdown (tables, highlighted code) and highlighted source files.
- **Chat**: Claude Code working in the same folder. Replies stream in live, and you can see
  which tools it used.

The files are the shared memory between you and Claude: it reads and writes them, you read them
here (or in your editor). The chat is just the remote control, so "New session" loses nothing.

## Requirements

- Python 3.11+ (installed for you by `uv` if needed)
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and logged in
  (`claude --version` works in your terminal)
- Linux or macOS

## Install

```bash
uv tool install git+https://github.com/adiacov/ai-web-assist
# or
pipx install git+https://github.com/adiacov/ai-web-assist
```

This installs two identical commands: `awa` and `ai-web-assist`.
Update with `uv tool upgrade ai-web-assist` (or `pipx upgrade ai-web-assist`).

## Usage

```bash
cd ~/my/project
awa                     # opens http://127.0.0.1:8765 in your browser

awa path/to/project     # open another folder
awa --port 9000         # first port to try (the next 19 are tried if it is busy)
awa --no-browser        # just print the URL
```

Stop it with Ctrl+C. You can run several projects at once; each gets its own port.

Tips:

- Press Enter to send; Shift+Enter adds a new line. **Stop** cancels the running reply.
- Paths in backticks (e.g. `docs/plan.md`) in chat replies and documents are links to the file.
- Link straight to a file: `http://127.0.0.1:8765/#docs/plan.md`.
- The gear icon sets the theme (system/light/dark) and font size. Drag the chat's left border,
  or the top of the message box, to resize them; double-click a border to reset it.

## Configuration (optional)

Create `.ai-web-assist/config.toml` in the project. Every key is optional:

```toml
title = "Spark Tutor"            # header and tab title (default: folder name)
include = ["course"]             # show only these folders (default: whole project)
exclude = ["*.log", "tmp"]       # extra names/globs to hide
permission_mode = "acceptEdits"  # acceptEdits | plan | manual | dontAsk | auto | bypassPermissions
allowed_tools = ["Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch", "Bash"]
model = ""                       # e.g. "sonnet"; empty = Claude Code's default
port = 8765
prompt = """
Extra instructions for Claude in this project, e.g. "Follow AGENTS.md".
"""
```

See [docs/config.example.toml](docs/config.example.toml) for comments on each key. A bad value
stops `awa` with a message that names the key.

Always hidden: dot-files and dot-folders, `.git`, `node_modules`, `target`, `dist`, `build`,
`__pycache__`, `.venv`, `venv`.

## Where things are stored

Everything lives in the project's `.ai-web-assist/` folder, as plain files:

| File | What |
|---|---|
| `config.toml` | your settings (commit it if you like) |
| `chat.json` | the current chat and Claude session id |
| `archive/chat-*.json` | earlier chats, kept when you click **New session** |
| `claude-stderr.log` | Claude's error output from the last reply |
| `.gitignore` | created automatically; ignores everything here (itself included) except `config.toml`, so `git status` stays clean |

Display settings (theme, font, panel sizes, last open file) are saved in your browser.

## Safety: read this

- **The chat can change your files and run commands.** By default it runs Claude Code with file
  edits auto-accepted (`acceptEdits`) and these tools allowed without asking: Read, Edit, Write,
  Glob, Grep, WebFetch, WebSearch and **Bash**. Use it in projects you have under version
  control, and review changes.
- To limit it, remove `"Bash"` from `allowed_tools`, or set `permission_mode = "plan"` for
  read-only answers. Nobody can answer permission prompts in this UI, so anything not allowed
  is refused.
- **Local, single-user only.** The server listens on `127.0.0.1` only, and has no login.
  Anyone who can use your computer's account can use the chat. Do not expose the port
  (no tunnels, no port forwarding).
- Basic browser protections: requests with a foreign `Host` header (DNS rebinding) or from
  other websites' pages are refused; the page forbids inline scripts, and rendered files are
  sanitized so they cannot run code.
- The file viewer serves only files inside the shown folders: no hidden files, no `..`, no
  symlinks pointing outside.

## Troubleshooting

| Problem | Fix |
|---|---|
| `the claude command was not found` | Install Claude Code and make sure `claude` is on your `PATH`. |
| An error in the chat, e.g. "not logged in" | Run `claude` once in a terminal to log in. Details are in `.ai-web-assist/claude-stderr.log`. |
| "The saved Claude session no longer exists" | Click **New session**. |
| A folder is missing from the tree | Check `include`/`exclude` in the config. Build and hidden folders are always hidden. |
| Tree shows "Showing the first 5000 files" | Use `include` to show only the folders you need. |

## Development

```bash
git clone https://github.com/adiacov/ai-web-assist && cd ai-web-assist
uv run --group dev pytest        # tests (use a fake `claude`; no network, no account needed)
uv run awa                       # run from the checkout
uv tool install --force --reinstall .   # install your local version
```

The runtime is Python standard library only. Front-end libraries (marked, DOMPurify, highlight.js)
are vendored in `src/ai_web_assist/static/vendor/` (see `LICENSES.md` there); there is no build
step. Design documents (spec, plan, decisions) live in `specs/`, made with
[Spec Kit](https://github.com/github/spec-kit).

## Not in this version (parked)

- Images in markdown that point to project files
- Editing files in the browser
- Several chats at once, or a view of background tasks
- A pinned "status" file or dashboard of progress data
- Access tokens for the local URL, or multi-user use
- Packaging as a Claude Code plugin

## License

MIT
