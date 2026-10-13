import socket

import pytest

from ai_web_assist import __version__, cli


def test_parse_args_defaults():
    a = cli.parse_args([])
    assert a.path == "." and a.port is None and a.no_browser is False


def test_parse_args_all():
    a = cli.parse_args(["/tmp", "--port", "9001", "--no-browser"])
    assert (a.path, a.port, a.no_browser) == ("/tmp", 9001, True)


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.parse_args(["--version"])
    assert e.value.code == 0
    assert f"ai-web-assist {__version__}" in capsys.readouterr().out


def test_bind_skips_busy_port():
    busy = socket.socket()
    busy.bind(("127.0.0.1", 0))
    busy.listen()
    port = busy.getsockname()[1]
    try:
        srv = cli.bind_first_free(lambda p: _Server(p), port, attempts=5)
        assert srv.port != port
    finally:
        busy.close()


def test_bind_gives_up():
    def always_busy(p):
        raise OSError(98, "Address already in use")
    with pytest.raises(OSError):
        cli.bind_first_free(always_busy, 9000, attempts=3)


class _Server:
    def __init__(self, port):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", port))
        self.port = port
        self.sock.close()


def test_missing_claude(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli.main([str(tmp_path), "--no-browser"]) == 1
    assert "claude" in capsys.readouterr().err


def test_bad_config(tmp_path, capsys):
    (tmp_path / ".ai-web-assist").mkdir()
    (tmp_path / ".ai-web-assist" / "config.toml").write_text("port = 'x'")
    assert cli.main([str(tmp_path), "--no-browser"]) == 2
    err = capsys.readouterr().err
    assert "config error" in err and "'port'" in err


def test_missing_folder(tmp_path, capsys):
    assert cli.main([str(tmp_path / "nope"), "--no-browser"]) == 2
    assert "not a folder" in capsys.readouterr().err


def test_port_precedence(tmp_path):
    (tmp_path / ".ai-web-assist").mkdir()
    (tmp_path / ".ai-web-assist" / "config.toml").write_text("port = 9100")
    from ai_web_assist.config import load_config
    config = load_config(tmp_path)
    assert cli.choose_port(None, config) == 9100
    assert cli.choose_port(9200, config) == 9200


@pytest.mark.parametrize("argv", [["version"], ["versions"], ["update", "--to", "0.1.0", "--yes"]])
def test_subcommands_are_routed(monkeypatch, argv):
    seen = []
    monkeypatch.setattr(cli, "run_command", lambda name, rest: seen.append((name, rest)) or 0)
    assert cli.main(argv) == 0
    assert seen == [(argv[0], argv[1:])]


def test_folder_named_like_a_command_opens_with_a_path(monkeypatch, tmp_path):
    (tmp_path / "version").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "run_command", lambda *a: pytest.fail("routed to a subcommand"))
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)  # stop before starting a server
    assert cli.main(["./version"]) == 1
