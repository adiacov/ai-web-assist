# Quickstart: validate the release process

Prerequisites: uv, pipx, network access, releases v0.1.0 and v0.2.0 published.

1. Tests: `uv run --group dev pytest` → all pass, no network used.
2. Pinned install (isolated):
   `UV_TOOL_DIR=$T/tools UV_TOOL_BIN_DIR=$T/bin uv tool install git+https://github.com/adiacov/ai-web-assist@v0.2.0`
   → `$T/bin/awa --version` prints `ai-web-assist 0.2.0`.
3. `awa version` → installed 0.2.0 with uv, "You have the latest release."
4. `awa versions` → 0.2.0 and 0.1.0, 0.2.0 marked installed.
5. `awa update --to v0.1.0` → asks to confirm; `y` → `Now on 0.1.0`.
6. Back up with plain uv (0.1.0 has no `update`): `uv tool install --force git+…@v0.2.0`.
7. `awa update --to 9.9.9` → "there is no release 9.9.9", exit 2.
8. Repeat 2–5 with pipx (`PIPX_HOME=$T/pipx PIPX_BIN_DIR=$T/pbin pipx install …`).
9. Offline (`HTTPS_PROXY=http://127.0.0.1:9`): `awa version` shows the installed version and
   "Could not check…", exit 0; `awa update` exits 1 with a one-line message.
10. Release: push tag `vX.Y.Z` → workflow green, release has notes and wheel + sdist.
    A mismatching tag fails the "check tag" step.

See [contracts/cli.md](contracts/cli.md) for exact messages.
