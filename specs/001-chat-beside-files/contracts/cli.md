# Contract: Command line

```
awa [PATH] [--port N] [--no-browser] [--version] [--help]
ai-web-assist …   # identical
```

| Argument | Default | Meaning |
|---|---|---|
| `PATH` | current folder | project folder to open; must exist and be a directory |
| `--port N` | config `port`, else 8765 | first port to try; the next 19 ports are tried if it is busy |
| `--no-browser` | off | do not open a browser tab |
| `--version` | | print `ai-web-assist <version>` and exit |

Behaviour:

1. Resolve `PATH`, load config (exit code **2** with `config error: <file>: <message>` on a bad config).
2. Check that `claude` is on PATH (exit code **1** with an install hint if not).
3. Ensure `.ai-web-assist/.gitignore` exists.
4. Bind `127.0.0.1:<port>` (exit code **1** if no free port in the range).
5. Print `AI Web Assist: <title> → http://127.0.0.1:<port>  (Ctrl+C to stop)`.
6. Open the browser unless `--no-browser`.
7. Ctrl+C stops the server (and any running Claude process) and exits with code 0.
