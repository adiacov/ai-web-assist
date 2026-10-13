# Quickstart & Validation: Chat Beside Your Files (MVP)

Prerequisites: `uv` (or `pipx`), and Claude Code installed and logged in (`claude --version`).

## 1. Automated tests (from the repo)

```bash
uv run --group dev pytest -q
```

Expected: all tests pass. They cover config, path safety, tree, stream parsing, state, and
the HTTP API with a fake `claude`.

## 2. Install as a user would

```bash
uv tool install --force .            # local checkout
# or, once published:
uv tool install git+https://github.com/<user>/ai-web-assist
awa --version && ai-web-assist --version
```

Expected: both print `ai-web-assist 0.1.0`.

## 3. Run in another project

```bash
cd ~/Documents/private/projects/learn-code/ai-path
awa
```

Expected:

| Check | Expected outcome | Spec |
|---|---|---|
| Browser opens | title = folder name; tree lists files; no `.git` or hidden folders | US1, FR-006 |
| Open a `.md` file | tables and highlighted code render | FR-009 |
| Click a backticked path in a doc | that file opens | FR-011 |
| Send "list the top-level folders" | reply streams; tool lines (e.g. `Glob`) appear | US2, FR-015 |
| Send "create tmp-awa-test.md with one line" | the file appears with a green dot within about 2 s | FR-008 |
| Edit the open file in another editor | the viewer refreshes and keeps its scroll position | FR-012 |
| Ctrl+C, run `awa` again, reload | history is shown; "what file did you create?" is answered correctly | US3, FR-018 |
| New session → confirm | chat clears; `.ai-web-assist/archive/chat-*.json` exists | FR-020 |
| `cat .ai-web-assist/.gitignore` | `*`, `!.gitignore`, `!config.toml` | FR-027 |
| Second `awa` in another folder | uses port 8766 | FR-004 |

## 4. Safety spot checks

```bash
curl -s 'http://127.0.0.1:8765/api/file?path=../../etc/passwd'      # → 404
curl -s 'http://127.0.0.1:8765/api/file?path=.git/config'           # → 404
curl -s -H 'Host: evil.example' http://127.0.0.1:8765/api/tree       # → 403
curl -s -X POST -H 'Content-Type: text/plain' -d '{"message":"hi"}' \
     http://127.0.0.1:8765/api/chat                                  # → 403
ss -ltn | grep 8765                                                  # → 127.0.0.1:8765 only
```

## 5. Offline check

Disconnect the network (or block it in the browser's devtools) and reload: markdown still
renders and code is highlighted (no external requests appear in the Network tab).
