# Contract: Local HTTP API

Base: `http://127.0.0.1:<port>`. JSON unless noted. Errors: `{"error": "<message>"}`.

**Guards on every request**: the `Host` header must be `127.0.0.1:<port>` or `localhost:<port>`,
otherwise **403**. **POST** additionally requires `Content-Type: application/json`, and an
`Origin` header, if present, equal to `http://<host header>`. Otherwise **403**.

| Method & path | Request | Response |
|---|---|---|
| `GET /` | | `index.html` with the HTML-escaped title substituted |
| `GET /static/<path>` | | packaged static file (css/js/vendor); **404** if missing or outside the static dir |
| `GET /api/config` | | `{title, workspace_id, version, project_name}` |
| `GET /api/tree` | | `{files: [{path, mtime}], truncated}` (see data-model) |
| `GET /api/file?path=<rel>` | | `{path, content, mtime, binary, truncated}`; **404** if the path is refused or missing |
| `GET /api/history` | | `{session_id, messages: Message[], busy: bool}` |
| `POST /api/chat` | `{"message": str}` | **200** `application/x-ndjson` stream (below); **400** if the message is empty; **409** if a reply is already running |
| `POST /api/stop` | `{}` | `{"ok": true}` (stops the running reply, if any) |
| `POST /api/new` | `{}` | `{"ok": true}`; **409** `{"error": "busy"}` while a reply runs |

## Chat stream events (one JSON object per line)

| Event | Meaning |
|---|---|
| `{"t":"text","v":"…"}` | text chunk to append to the reply |
| `{"t":"tool","name":"Edit","summary":"docs/plan.md"}` | a tool was used |
| `{"t":"error","v":"…"}` | an error to show (Claude error result, non-zero exit with stderr tail) |
| `{"t":"done"}` | the reply is finished and saved to history |

If the client disconnects, the server keeps reading until Claude exits and then saves the
reply (FR-021).
