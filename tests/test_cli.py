import json
import sys

import pytest
from typer.testing import CliRunner

from testpilot.cli import app

runner = CliRunner()


def test_help_and_version():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("init", "validate", "list", "run", "report", "version"):
        assert command in result.stdout
    assert runner.invoke(app, ["version"]).stdout.strip() == "0.1.0"


def test_init_validates_and_refuses_overwrite(tmp_path):
    path = tmp_path / "new.yml"
    assert runner.invoke(app, ["init", "-c", str(path)]).exit_code == 0
    assert runner.invoke(app, ["validate", "-c", str(path), "--env", "local"]).exit_code == 0
    previous = path.read_bytes()
    assert runner.invoke(app, ["init", "-c", str(path)]).exit_code == 2
    assert path.read_bytes() == previous


def test_list_and_invalid_config(config_file, tmp_path):
    path = config_file()
    result = runner.invoke(app, ["list", "-c", str(path)])
    assert result.exit_code == 0
    assert "backend" in result.stdout
    assert runner.invoke(app, ["validate", "-c", str(tmp_path / "missing")]).exit_code == 2
    assert runner.invoke(app, ["run", "-c", str(path), "--repo", "unknown"]).exit_code == 2
    assert runner.invoke(app, ["run", "-c", str(path), "--parallel", "0"]).exit_code == 2


@pytest.mark.parametrize("outcome,expected", [("", 0), ("<failure>bad</failure>", 1)])
def test_run_reports_and_exit_status(config_file, outcome, expected):
    xml = f'<testsuite><testcase name="demo">{outcome}</testcase></testsuite>'
    path = config_file(
        repositories=[
            {
                "name": "demo",
                "path": "repo",
                "command": [
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; Path('r.xml').write_text({xml!r})",
                ],
                "junit": "r.xml",
            }
        ],
        profiles={"ci": {"parallel": 2}},
    )
    result = runner.invoke(app, ["run", "-c", str(path), "--env", "ci", "--parallel", "1"])
    assert result.exit_code == expected, result.stdout
    reports = path.parent / "reports"
    canonical = list(reports.glob("*/run.json"))
    assert len(canonical) == 1
    assert json.loads(canonical[0].read_text())["success"] == (expected == 0)
    for fmt in ("html", "json", "junit"):
        output = path.parent / f"export.{fmt}"
        result = runner.invoke(
            app, ["report", "--input", str(reports), "--format", fmt, "--output", str(output)]
        )
        assert result.exit_code == expected, result.stdout
        assert output.is_file()


def test_missing_report_is_nonzero(config_file):
    path = config_file()
    result = runner.invoke(app, ["run", "-c", str(path)])
    assert result.exit_code == 1
    assert "incomplete" in result.stdout


def test_report_bad_input_and_format(tmp_path):
    assert runner.invoke(app, ["report", "--input", str(tmp_path)]).exit_code == 2
    assert runner.invoke(app, ["report", "--format", "pdf"]).exit_code == 2
    invalid = tmp_path / "run.json"
    invalid.write_text("{", encoding="utf-8")
    assert runner.invoke(app, ["report", "--input", str(invalid)]).exit_code == 2


def test_cli_filters_repositories(config_file):
    path = config_file(
        repositories=[
            {"name": "one", "path": "repo", "command": [sys.executable, "-c", "pass"]},
            {"name": "two", "path": "repo", "command": [sys.executable, "-c", "pass"]},
        ]
    )
    runner.invoke(app, ["run", "-c", str(path), "--repo", "two"])
    data = json.loads(next((path.parent / "reports").glob("*/run.json")).read_text())
    assert [r["name"] for r in data["repositories"]] == ["two"]
