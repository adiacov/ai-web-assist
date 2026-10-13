import subprocess
import sys
from types import SimpleNamespace

import pytest

from ai_web_assist import releases, update
from ai_web_assist.releases import Release, ReleaseError, Version

V = Version.parse


@pytest.fixture
def env(monkeypatch):
    """Installed 0.2.0 via uv, releases 0.1.0..0.3.0, installer runs recorded, terminal stdin."""
    state = SimpleNamespace(
        installed=V("0.2.0"), releases=[Release(V(t)) for t in ("0.3.0", "0.2.0", "0.1.0")],
        installer="uv", which=True, runs=[], run_code=0, answer="y", tty=True, error=None,
    )

    def fetch():
        if state.error:
            raise ReleaseError(state.error)
        return state.releases

    def run(cmd, **kw):
        if cmd[0] == sys.executable:
            return subprocess.CompletedProcess(cmd, 0, stdout="9.9.9\n")
        state.runs.append(cmd)
        return subprocess.CompletedProcess(cmd, state.run_code)

    monkeypatch.setattr(update, "installed_version", lambda: state.installed)
    monkeypatch.setattr(releases, "fetch_releases", fetch)
    monkeypatch.setattr(update, "detect_installer", lambda prefix=None: state.installer)
    monkeypatch.setattr(update.shutil, "which", lambda name: f"/bin/{name}" if state.which else None)
    monkeypatch.setattr(update.subprocess, "run", run)
    monkeypatch.setattr("builtins.input", lambda prompt: state.answer)
    monkeypatch.setattr(update.sys.stdin, "isatty", lambda: state.tty, raising=False)
    return state


def test_detect_installer(tmp_path):
    assert update.detect_installer(str(tmp_path)) == "other"
    (tmp_path / "pipx_metadata.json").write_text("{}")
    assert update.detect_installer(str(tmp_path)) == "pipx"
    (tmp_path / "uv-receipt.toml").write_text("")
    assert update.detect_installer(str(tmp_path)) == "uv"


def test_install_commands():
    url = "git+https://github.com/adiacov/ai-web-assist@v0.1.0"
    assert update.install_command("uv", V("0.1.0")) == ["uv", "tool", "install", "--force", url]
    assert update.install_command("pipx", V("0.1.0")) == ["pipx", "install", "--force", url]


def test_update_to_latest(env, capsys):
    assert update.run("update", []) == 0
    assert env.runs == [update.install_command("uv", V("0.3.0"))]
    out = capsys.readouterr().out
    assert "Updating 0.2.0 → 0.3.0 with uv" in out and "Restart any running awa servers" in out


def test_update_with_pipx(env):
    env.installer = "pipx"
    assert update.run("update", ["--to", "0.3.0"]) == 0
    assert env.runs == [update.install_command("pipx", V("0.3.0"))]


def test_already_latest(env, capsys):
    env.installed = V("0.3.0")
    assert update.run("update", []) == 0
    assert env.runs == [] and "Already on 0.3.0." in capsys.readouterr().out


def test_downgrade_confirmed(env, capsys):
    assert update.run("update", ["--to", "v0.1.0"]) == 0
    assert env.runs == [update.install_command("uv", V("0.1.0"))]


def test_downgrade_cancelled(env, capsys):
    env.answer = "n"
    assert update.run("update", ["--to", "0.1.0"]) == 1
    assert env.runs == [] and "Cancelled." in capsys.readouterr().out


def test_downgrade_without_terminal_needs_yes(env, capsys):
    env.tty = False
    assert update.run("update", ["--to", "0.1.0"]) == 1
    assert env.runs == [] and "needs --yes" in capsys.readouterr().err
    assert update.run("update", ["--to", "0.1.0", "--yes"]) == 0
    assert env.runs == [update.install_command("uv", V("0.1.0"))]


def test_dev_install_newer_than_latest_counts_as_downgrade(env):
    env.installed, env.tty = V("0.4.0"), False
    assert update.run("update", []) == 1 and env.runs == []


@pytest.mark.parametrize("to, code, text", [("9.9.9", 2, "there is no release 9.9.9"),
                                            ("latest", 2, "not a version: latest")])
def test_bad_target(env, capsys, to, code, text):
    assert update.run("update", ["--to", to]) == code
    assert env.runs == [] and text in capsys.readouterr().err


@pytest.mark.parametrize("installer, which", [("other", True), ("uv", False)])
def test_manual_commands_when_not_self_updatable(env, capsys, installer, which):
    env.installer, env.which = installer, which
    assert update.run("update", []) == 1
    out = capsys.readouterr().out
    assert env.runs == []
    assert "uv tool install --force git+https://github.com/adiacov/ai-web-assist@v0.3.0" in out
    assert "pipx install --force" in out


def test_installer_failure(env, capsys):
    env.run_code = 3
    assert update.run("update", []) == 1
    assert "the update failed (exit 3)" in capsys.readouterr().err


def test_update_offline(env, capsys):
    env.error = "could not reach GitHub (timed out)"
    assert update.run("update", []) == 1
    assert "could not list releases: could not reach GitHub" in capsys.readouterr().err


def test_version_shows_update(env, capsys):
    assert update.run("version", []) == 0
    out = capsys.readouterr().out
    assert "ai-web-assist 0.2.0 (installed with uv)" in out and "Latest release: 0.3.0" in out


@pytest.mark.parametrize("installed, text", [("0.3.0", "You have the latest release."),
                                             ("0.4.0", "newer than the latest release (0.3.0)")])
def test_version_states(env, capsys, installed, text):
    env.installed = V(installed)
    assert update.run("version", []) == 0 and text in capsys.readouterr().out


def test_version_offline_still_shows_installed(env, capsys):
    env.error, env.installer = "could not reach GitHub (timed out)", "other"
    assert update.run("version", []) == 0
    out = capsys.readouterr().out
    assert out.startswith("ai-web-assist 0.2.0\n") and "Could not check the latest release" in out


def test_versions_lists_newest_first(env, capsys):
    assert update.run("versions", []) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [l.split()[0] for l in lines] == ["0.3.0", "*", "0.1.0"]
    assert lines[1].startswith("* 0.2.0") and lines[1].endswith("(installed)")


def test_versions_offline(env, capsys):
    env.error = "boom"
    assert update.run("versions", []) == 1
    assert "could not list releases: boom" in capsys.readouterr().err
