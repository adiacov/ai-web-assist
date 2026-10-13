"""`awa` / `ai-web-assist`: open a folder as a browser workspace with a Claude Code chat."""

from __future__ import annotations

import argparse
import shutil
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Callable, TypeVar

from ai_web_assist import __version__
from ai_web_assist.config import Config, ConfigError, load_config
from ai_web_assist.files import Workspace
from ai_web_assist.server import App, make_server
from ai_web_assist.state import ChatStore, ensure_state_dir

PORT_ATTEMPTS = 20
T = TypeVar("T")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="awa",
        description="Open a folder as a local browser workspace: file tree, rendered viewer, "
                    "and a chat with Claude Code that reads and writes the same files.",
    )
    p.add_argument("path", nargs="?", default=".", help="project folder (default: current folder)")
    p.add_argument("--port", type=int, help="first port to try (default: config 'port' or 8765)")
    p.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    p.add_argument("--version", action="version", version=f"ai-web-assist {__version__}")
    return p.parse_args(argv)


def choose_port(cli_port: int | None, config: Config) -> int:
    return cli_port if cli_port is not None else config.port


def bind_first_free(factory: Callable[[int], T], port: int, attempts: int = PORT_ATTEMPTS) -> T:
    """Call factory(port), moving to the next port while the current one is busy."""
    last_error: OSError | None = None
    for candidate in range(port, min(port + attempts, 65536)):
        try:
            return factory(candidate)
        except OSError as e:
            last_error = e
    raise last_error or OSError(f"no usable port from {port}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"awa: {args.path} is not a folder", file=sys.stderr)
        return 2
    root = root.resolve()
    try:
        config = load_config(root)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    if not shutil.which("claude"):
        print("awa: the `claude` command (Claude Code CLI) was not found on PATH.\n"
              "Install it from https://docs.claude.com/en/docs/claude-code and log in first.", file=sys.stderr)
        return 1

    workspace = Workspace(root, config)
    app = App(workspace, ChatStore(ensure_state_dir(workspace.root)))
    first = choose_port(args.port, config)
    try:
        srv = bind_first_free(lambda p: make_server(app, p), first)
    except OSError as e:
        print(f"awa: no free port in {first}-{first + PORT_ATTEMPTS - 1}: {e}", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{srv.server_address[1]}"
    print(f"AI Web Assist: {config.title} → {url}  (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping…")
    finally:
        app.shutdown()
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
