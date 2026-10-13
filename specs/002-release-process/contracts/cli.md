# CLI Contract: version commands

Existing usage is unchanged: `awa [PATH] [--port N] [--no-browser]`, `awa --version`.
The first argument `version`, `versions` or `update` selects a subcommand; `awa ./version`
opens a folder named `version`.

## `awa version`

```text
ai-web-assist 0.1.0 (installed with uv)
Latest release: 0.2.0. Run `awa update` to update.
```

Other second lines: `You have the latest release.` /
`This is newer than the latest release (0.2.0).` /
`Could not check the latest release: <reason>`. Exit 0 always.

## `awa versions`

```text
  0.2.0  2026-10-13
* 0.1.0  2026-10-13   (installed)
```

Newest first. Exit 0; exit 1 with `awa: could not list releases: <reason>` on error.

## `awa update [--to VERSION] [--yes]`

- `VERSION`: `X.Y.Z` or `vX.Y.Z`. Default: latest release.
- `--yes` / `-y`: no confirmation for downgrades.

Flow and messages:

| Case | Output | Exit |
|---|---|---|
| network error | `awa: could not list releases: <reason>` | 1 |
| invalid VERSION | `awa: not a version: VERSION (expected X.Y.Z)` | 2 |
| unknown VERSION | `awa: there is no release X.Y.Z. See \`awa versions\`.` | 2 |
| already there | `Already on X.Y.Z.` | 0 |
| downgrade, no tty, no --yes | `awa: downgrading from A to B needs --yes when not run in a terminal.` | 1 |
| downgrade, answer not y | `Downgrade from A to B? [y/N]` then `Cancelled.` | 1 |
| installer other / missing | `awa was not installed with uv or pipx, so it can't update itself. Run one of:` + both commands | 1 |
| installer fails | installer's own output, then `awa: the update failed (exit N).` | 1 |
| success | `Updating A → B with uv…`, installer output, `Now on B.`, `Restart any running awa servers to use the new version.` | 0 |

Commands run (no shell):

```text
uv tool install --force git+https://github.com/adiacov/ai-web-assist@vX.Y.Z
pipx install --force git+https://github.com/adiacov/ai-web-assist@vX.Y.Z
```
