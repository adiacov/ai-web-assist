"""`awa version`, `awa versions` and `awa update`: check, list and switch released versions."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from ai_web_assist import releases
from ai_web_assist.releases import ReleaseError, Version, installed_version

COMMANDS = ("version", "versions", "update")


def detect_installer(prefix: str | None = None) -> str:
    """'uv' or 'pipx' when that tool made awa's environment, else 'other'."""
    env = Path(prefix or sys.prefix)
    if (env / "uv-receipt.toml").is_file():
        return "uv"
    if (env / "pipx_metadata.json").is_file():
        return "pipx"
    return "other"


def install_command(installer: str, version: Version) -> list[str]:
    source = f"git+{releases.REPO_URL}@{version.tag}"
    if installer == "uv":
        return ["uv", "tool", "install", "--force", source]
    return ["pipx", "install", "--force", source]


def _installed_with() -> str:
    installer = detect_installer()
    return f" (installed with {installer})" if installer != "other" else ""


def cmd_version(_args: argparse.Namespace) -> int:
    current = installed_version()
    print(f"ai-web-assist {current}{_installed_with()}")
    try:
        found = releases.fetch_releases()
    except ReleaseError as e:
        print(f"Could not check the latest release: {e}")
        return 0
    if not found:
        print("No releases are published yet.")
    elif found[0].version > current:
        print(f"Latest release: {found[0].version}. Run `awa update` to update.")
    elif found[0].version == current:
        print("You have the latest release.")
    else:
        print(f"This is newer than the latest release ({found[0].version}).")
    return 0


def cmd_versions(_args: argparse.Namespace) -> int:
    try:
        found = releases.fetch_releases()
    except ReleaseError as e:
        print(f"awa: could not list releases: {e}", file=sys.stderr)
        return 1
    if not found:
        print("No releases are published yet.")
        return 0
    current = installed_version()
    for r in found:
        mark = "*" if r.version == current else " "
        note = "   (installed)" if r.version == current else ""
        print(f"{mark} {str(r.version):<8} {r.date}{note}".rstrip())
    return 0


def _confirm(question: str) -> bool:
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _print_manual(target: Version) -> None:
    print("awa was not installed with uv or pipx, so it can't update itself. Run one of:")
    for installer in ("uv", "pipx"):
        print("  " + " ".join(install_command(installer, target)))


def _report_new_version(target: Version) -> None:
    probe = subprocess.run(
        [sys.executable, "-c", "import ai_web_assist; print(ai_web_assist.__version__)"],
        capture_output=True, text=True,
    )
    now = probe.stdout.strip() if probe.returncode == 0 else ""
    print(f"Now on {now or target}.")


def cmd_update(args: argparse.Namespace) -> int:
    wanted: Version | None = None
    if args.to is not None:
        wanted = Version.parse(args.to)
        if wanted is None:
            print(f"awa: not a version: {args.to} (expected X.Y.Z)", file=sys.stderr)
            return 2
    try:
        found = releases.fetch_releases()
    except ReleaseError as e:
        print(f"awa: could not list releases: {e}", file=sys.stderr)
        return 1
    if not found:
        print("awa: no releases are published yet.", file=sys.stderr)
        return 1
    available = {r.version for r in found}
    target = wanted or found[0].version
    if target not in available:
        print(f"awa: there is no release {target}. See `awa versions`.", file=sys.stderr)
        return 2

    current = installed_version()
    if target == current:
        print(f"Already on {current}.")
        return 0
    if target < current and not args.yes:
        if not sys.stdin.isatty():
            print(f"awa: downgrading from {current} to {target} needs --yes "
                  "when not run in a terminal.", file=sys.stderr)
            return 1
        if not _confirm(f"Downgrade from {current} to {target}?"):
            print("Cancelled.")
            return 1

    installer = detect_installer()
    if installer == "other" or not shutil.which(installer):
        _print_manual(target)
        return 1
    print(f"Updating {current} → {target} with {installer}…", flush=True)
    result = subprocess.run(install_command(installer, target))
    if result.returncode != 0:
        print(f"awa: the update failed (exit {result.returncode}).", file=sys.stderr)
        return 1
    _report_new_version(target)
    print("Restart any running awa servers to use the new version.")
    return 0


def _parser(command: str) -> argparse.ArgumentParser:
    if command == "version":
        p = argparse.ArgumentParser(prog="awa version",
                                    description="Show the installed version and the latest release.")
        p.set_defaults(run=cmd_version)
    elif command == "versions":
        p = argparse.ArgumentParser(prog="awa versions",
                                    description="List released versions, newest first.")
        p.set_defaults(run=cmd_versions)
    else:
        p = argparse.ArgumentParser(prog="awa update",
                                    description="Update to the latest release, or move to a given one.")
        p.add_argument("--to", metavar="VERSION", help="release to install, e.g. v0.1.0 (older = downgrade)")
        p.add_argument("-y", "--yes", action="store_true", help="do not ask before downgrading")
        p.set_defaults(run=cmd_update)
    return p


def run(command: str, argv: list[str]) -> int:
    args = _parser(command).parse_args(argv)
    return args.run(args)

