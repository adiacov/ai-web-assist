# Contract: `.ai-web-assist/config.toml`

All keys are optional. Field types and defaults are listed in [data-model.md](../data-model.md#config-ai-web-assistconfigtoml-optional).

```toml
# .ai-web-assist/config.toml
title = "Spark Tutor"
include = ["course"]                 # show only these folders (project-relative)
exclude = ["*.log", "tmp"]           # extra names/globs to hide (added to built-ins)
permission_mode = "acceptEdits"      # acceptEdits | auto | bypassPermissions | manual | dontAsk | plan
allowed_tools = ["Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch", "Bash"]
model = ""                           # empty = Claude Code's default
port = 8765
prompt = """
Follow the protocol in AGENTS.md. Copy the user's chat answers into the current session file.
"""
```

Errors (the app exits with code 2):

- invalid TOML → `config error: <path>: <tomllib message>`
- unknown key → `config error: <path>: unknown key 'foo'`
- wrong type or value → `config error: <path>: 'port' must be an integer between 1 and 65535`
