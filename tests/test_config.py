import sys

import pytest

from testpilot.config import ConfigError, load_config, resolve


def test_profile_and_cli_precedence(config_file, monkeypatch):
    monkeypatch.setenv("TP_VALUE", "host")
    path = config_file(
        defaults={"timeout": 10, "parallel": 1, "env": {"TP_VALUE": "global", "GLOBAL": "yes"}},
        profiles={
            "ci": {
                "timeout": 20,
                "parallel": 2,
                "report_dir": "ci-reports",
                "env": {"TP_VALUE": "profile"},
            }
        },
    )
    config = load_config(path)
    config.repositories[0].env = {"TP_VALUE": "repo"}
    config.repositories[0].timeout = 30
    settings = resolve(config, path, "ci", parallel=3, timeout=40, report_dir="override")
    assert settings.parallel == 3
    assert settings.report_dir == path.parent / "override"
    assert settings.repositories[0].timeout == 40
    assert settings.repositories[0].env["TP_VALUE"] == "repo"
    assert settings.repositories[0].env["GLOBAL"] == "yes"
    assert settings.repositories[0].cwd == path.parent / "repo"
    assert settings.repositories[0].junit == path.parent / "repo" / "results.xml"


@pytest.mark.parametrize(
    "settings",
    [
        {"version": 2},
        {"defaults": {"parallel": 0}},
        {"defaults": {"timeout": -1}},
        {"defaults": {"timeout": float("inf")}},
        {"unknown": True},
    ],
)
def test_invalid_settings(config_file, settings):
    with pytest.raises(ConfigError):
        load_config(config_file(**settings))


@pytest.mark.parametrize(
    "change",
    [
        {"name": "../bad"},
        {"command": "python -m pytest"},
        {"command": []},
        {"command": ["python", ""]},
        {"env": {"BAD=KEY": "x"}},
        {"env": {"KEY": "bad\x00value"}},
    ],
)
def test_invalid_repository(config_file, change):
    repo = {"name": "repo", "path": "repo", "command": [sys.executable, "-c", "pass"]}
    with pytest.raises(ConfigError):
        load_config(config_file(repositories=[{**repo, **change}]))


def test_duplicate_names_and_report_paths(config_file):
    repo = {"name": "first", "path": "repo", "command": [sys.executable], "junit": "r.xml"}
    with pytest.raises(ConfigError):
        load_config(config_file(repositories=[repo, repo]))
    path = config_file(repositories=[repo, {**repo, "name": "second"}])
    with pytest.raises(ConfigError, match="JUnit"):
        resolve(load_config(path), path)


def test_relative_working_directory(config_file):
    path = config_file()
    subdir = path.parent / "repo" / "sub"
    subdir.mkdir()
    config = load_config(path)
    config.repositories[0].working_dir = "sub"
    settings = resolve(config, path)
    assert settings.repositories[0].cwd == subdir
    assert settings.repositories[0].junit == subdir / "results.xml"


def test_missing_paths_and_unknown_profile(config_file):
    path = config_file()
    config = load_config(path)
    with pytest.raises(ConfigError, match="profile"):
        resolve(config, path, "unknown")
    config.repositories[0].path = "missing"
    with pytest.raises(ConfigError, match="directory"):
        resolve(config, path)


def test_bad_yaml(tmp_path):
    path = tmp_path / "bad.yml"
    path.write_text("repositories: [", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "absent.yml")
