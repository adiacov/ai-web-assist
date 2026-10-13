# Data Model: Chat Beside Your Files (MVP)

All data are plain files. Nothing is kept in memory longer than one request, apart from
the running Claude process handle.

## Config (`.ai-web-assist/config.toml`, optional)

| Field | Type | Default | Validation |
|---|---|---|---|
| `title` | str | project folder name | non-empty |
| `include` | list[str] | `[]` (= whole project) | relative paths, no `..`, no leading `/` or `.` |
| `exclude` | list[str] | `[]` | names or glob patterns matched against each path segment |
| `permission_mode` | str | `acceptEdits` | one of `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan` |
| `allowed_tools` | list[str] \| str | `Read Edit Write Glob Grep WebFetch WebSearch Bash` | non-empty strings |
| `model` | str | `""` (Claude's default) | — |
| `port` | int | `8765` | 1–65535 |
| `prompt` | str | `""` | appended to the generic UI prompt |

Unknown keys → error. The built-in excludes (`.git`, `node_modules`, `target`, `dist`, `build`,
`__pycache__`, `.venv`, `venv`, and every name starting with `.`) always apply on top of
`exclude`.

## Workspace (runtime, derived)

- `root`: absolute, resolved project path
- `config`: Config
- `state_dir`: `root/.ai-web-assist`
- `workspace_id`: first 12 hex chars of the SHA-256 of `str(root)` (prefix for browser storage keys)

## File entry (tree item)

| Field | Type | Notes |
|---|---|---|
| `path` | str | project-relative, `/`-separated |
| `mtime` | float | seconds since epoch |

Tree response: `{files: FileEntry[], truncated: bool}`, sorted by path, at most 5,000 entries.

## File content

| Field | Type | Notes |
|---|---|---|
| `path` | str | as requested |
| `content` | str | UTF-8 (invalid bytes replaced); `""` if binary |
| `mtime` | float | |
| `binary` | bool | true if a NUL byte appears in the first 8 KB |
| `truncated` | bool | true if the file is larger than 1 MB; content holds the first 1 MB |

## Chat state (`.ai-web-assist/chat.json`)

```json
{ "session_id": "uuid or null", "messages": [Message, ...] }
```

**Message**

| Field | Type | Notes |
|---|---|---|
| `role` | `"user"` \| `"assistant"` \| `"error"` | |
| `text` | str | for assistant: the full reply text |
| `tools` | ToolUse[] | assistant only; may be empty |
| `ts` | float | seconds since epoch |

**ToolUse**: `{name: str, summary: str}`. `summary` is at most 160 chars: a project-relative
file path, command, URL, query, pattern or description.

### State transitions

```
(no chat.json) ──send──▶ running ──init event──▶ session_id saved
running ──result / exit / stop──▶ idle (assistant message appended)
idle ──send──▶ running (with --resume session_id)
idle ──new session──▶ chat.json moved to archive/chat-<ts>.json ──▶ (no chat.json)
running ──new session──▶ refused (409)
```

## Archive

`.ai-web-assist/archive/chat-YYYYMMDD-HHMMSS.json`: the same shape as the chat state. Never
deleted by the app.

## State folder layout

```
.ai-web-assist/
├── .gitignore          # "*", "!.gitignore", "!config.toml" (created on first run)
├── config.toml         # optional, user-owned, committable
├── chat.json           # current session
├── claude-stderr.log   # stderr of the last Claude run
└── archive/            # closed sessions
```
