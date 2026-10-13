import pytest

from ai_web_assist.config import DEFAULT_ALLOWED_TOOLS, ConfigError, load_config


def write_config(root, text):
    d = root / ".ai-web-assist"
    d.mkdir(exist_ok=True)
    (d / "config.toml").write_text(text)


def test_defaults_without_file(tmp_path):
    c = load_config(tmp_path)
    assert c.title == tmp_path.name
    assert c.include == ()
    assert c.exclude == ()
    assert c.permission_mode == "acceptEdits"
    assert c.allowed_tools == DEFAULT_ALLOWED_TOOLS
    assert c.model == ""
    assert c.port == 8765
    assert c.prompt == ""


def test_all_keys(tmp_path):
    write_config(tmp_path, """
title = "Spark Tutor"
include = ["course", "docs/notes"]
exclude = ["*.log", "tmp"]
permission_mode = "plan"
allowed_tools = ["Read", "Grep"]
model = "sonnet"
port = 9000
prompt = "Be brief."
""")
    c = load_config(tmp_path)
    assert c.title == "Spark Tutor"
    assert c.include == ("course", "docs/notes")
    assert c.exclude == ("*.log", "tmp")
    assert c.permission_mode == "plan"
    assert c.allowed_tools == ("Read", "Grep")
    assert c.model == "sonnet"
    assert c.port == 9000
    assert c.prompt == "Be brief."


def test_allowed_tools_as_string(tmp_path):
    write_config(tmp_path, 'allowed_tools = "Read  Edit,Write"')
    assert load_config(tmp_path).allowed_tools == ("Read", "Edit", "Write")


def test_include_trailing_slash_normalised(tmp_path):
    write_config(tmp_path, 'include = ["course/"]')
    assert load_config(tmp_path).include == ("course",)


@pytest.mark.parametrize("text, key", [
    ('foo = 1', "foo"),
    ('port = "80"', "port"),
    ('port = 0', "port"),
    ('port = 70000', "port"),
    ('port = true', "port"),
    ('include = "course"', "include"),
    ('include = [1]', "include"),
    ('include = ["../x"]', "include"),
    ('include = ["/etc"]', "include"),
    ('include = [".hidden"]', "include"),
    ('exclude = "x"', "exclude"),
    ('permission_mode = "yolo"', "permission_mode"),
    ('allowed_tools = []', "allowed_tools"),
    ('title = ""', "title"),
    ('title = 3', "title"),
    ('model = 1', "model"),
    ('prompt = 1', "prompt"),
])
def test_invalid_values(tmp_path, text, key):
    write_config(tmp_path, text)
    with pytest.raises(ConfigError) as e:
        load_config(tmp_path)
    assert f"'{key}'" in str(e.value)
    assert "config.toml" in str(e.value)


def test_invalid_toml(tmp_path):
    write_config(tmp_path, "title = ")
    with pytest.raises(ConfigError) as e:
        load_config(tmp_path)
    assert "config.toml" in str(e.value)
