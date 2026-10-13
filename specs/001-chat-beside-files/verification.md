# Verification: 001 Chat Beside Your Files (MVP)

Date: 2026-10-13 · Claude Code 2.1.296 · uv 0.9.26 · Linux · Chrome (headless, driven over the
DevTools protocol) · Python 3.13 (uv tool env)

Browser checks were scripted: each scenario ran in the real page (clicks, typing, waits), and
the page's console was collected. **No console errors or exceptions occurred in any run.**

## 1. Automated tests (quickstart §1)

```
$ uv run --group dev pytest -q
108 passed in 6.8s
```

Covers config validation, the path guard (traversal, absolute, symlink escape, hidden, state
folder, include/exclude), tree limits, binary/large files, the stream parser (on a recorded
real run), state archive and corruption, CLI exit codes and port fallback, the HTTP API with
Host/Origin/JSON guards, and chat via a fake `claude`: streaming, stdin delivery, one reply at
a time, Stop killing the process group (including a child process), Claude failures, client
disconnect, resume, New session, and config wiring.

## 2. Install as a user would (quickstart §2)

```
$ uv tool install --force --reinstall .
Installed 2 executables: ai-web-assist, awa
$ awa --version            → ai-web-assist 0.1.0
$ ai-web-assist --version  → ai-web-assist 0.1.0
```

Vendored assets are present in the installed package (`static/vendor/*`).

## 3. Real project: `~/Documents/private/projects/learn-code/ai-path` (quickstart §3)

| Check | Evidence | Result |
|---|---|---|
| Starts on the default port | `AI Web Assist: ai-path → http://127.0.0.1:8765` | ✅ |
| Second instance falls back | demo folder: `→ http://127.0.0.1:8766` | ✅ |
| Tree | `AGENTS.md, CLAUDE.md, DECISIONS.md, LEARNING-PROCESS.md, PROFILE.md, ROLE-RESEARCH.md, STATUS.md, course/PLAN.md, sessions/…`; no `.git` | ✅ |
| Viewer | `STATUS.md`: headings + 1 table rendered; `ROLE-RESEARCH.md`, `course/PLAN.md` became file links | ✅ |
| Chat streams + tools | tool lines `Bash List top-level directories`, …; reply in one sentence | ✅ |
| Change marker | a file created outside the app got a green dot within one poll | ✅ |
| Open file refreshes in place | text appended externally appeared; scroll 1261 → 1261 | ✅ |
| Resume after restart | after Ctrl+C + restart: 2 messages shown; "what did I ask you before?" was answered correctly | ✅ |
| Git stays clean | `git status --short` empty while `.ai-web-assist/` exists (see §6) | ✅ |
| Clean-up | verification files and `.ai-web-assist/` removed afterwards; ai-path `git status` clean | ✅ |

Read-only prompts were used in ai-path. Edit flows were verified in a scratch demo project:

| Check (demo project, real Claude, model haiku via config) | Result |
|---|---|
| "Create notes/hello.md…" over the API: file created; NDJSON `tool`/`text`/`done` events | ✅ |
| UI chat "Append a line to notes/hello.md…": busy state, tool line, reply path `notes/hello.md` linked, green dot on the collapsed `notes/` folder | ✅ |
| Reload: 4 history messages; Claude recalled the appended text (resume) | ✅ |
| New session: chat cleared, `archive/chat-20261013-105038.json` written, history `session_id: null` | ✅ |
| Markdown: table, Python/Scala/TS highlighting, backticked path and relative `../README.md` link open in the viewer | ✅ |
| `<script>` and `onerror` in markdown were neutralised (sanitizer + CSP); no alert | ✅ |
| Settings: dark theme, large font and chat width kept after reload; double-click reset the width | ✅ |

## 4. Safety spot checks (quickstart §4, against the ai-path instance)

```
traversal ../../etc/passwd        404
.git/config                       404
.ai-web-assist/chat.json          404
Host: evil.example                403
POST text/plain                   403
POST with Origin evil.example     403
listen                            127.0.0.1:8765
```

## 5. Offline (quickstart §5)

`index.html`, `app.js`, `boot.js` and `app.css` reference no external origin. All scripts and
styles load from `/static/`, and the CSP `default-src 'self'` would block any other origin.

## 6. Change made during verification

`.ai-web-assist/.gitignore` originally un-ignored itself, so every project showed an untracked
`.ai-web-assist/` folder in `git status`. It now ignores everything except `config.toml`,
itself included. Spec FR-027, research R8, data-model, README and tests were updated.

## Known limitations (parked)

- Images in markdown that point to project files do not load (no raw-file endpoint).
- Folder paths in chat replies (e.g. `course/`) are not links; only files are.
- Reinstalling an unchanged version needs `uv tool install --force --reinstall .`
