"""Consolidated report output."""

from pathlib import Path

from testpilot.models import RunResult
from testpilot.reporting.html_report import render_html
from testpilot.reporting.json_report import write_json
from testpilot.reporting.junit_report import write_junit


def write_reports(run: RunResult, report_dir: Path) -> Path:
    # run_id is created by the orchestrator; persisted input is never used here.
    directory = report_dir / run.run_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "report.html").write_text(render_html(run), encoding="utf-8")
    write_junit(run, directory / "junit.xml")
    # JSON is written last so discovery only sees runs whose artifacts were generated.
    write_json(run, directory / "run.json")
    return directory
