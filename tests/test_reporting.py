import json
from datetime import UTC, datetime
from xml.etree import ElementTree

import pytest

from testpilot.junit import parse_junit
from testpilot.models import CaseResult, RepositoryResult, RunResult
from testpilot.reporting import write_reports
from testpilot.reporting.html_report import render_html
from testpilot.reporting.json_report import read_json


def result(status="passed"):
    return RunResult(
        run_id="sample",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        environment="ci",
        duration=1.2,
        repositories=[
            RepositoryResult(
                name="repo<script>",
                status=status,
                exit_code=0,
                results_complete=True,
                cases=[
                    CaseResult(
                        name="test<&>",
                        detail="<script>alert(1)</script>",
                        outcome="passed" if status == "passed" else "failed",
                    )
                ],
            )
        ],
    )


def test_json_html_and_junit_reports(tmp_path):
    run = result()
    directory = write_reports(run, tmp_path)
    data = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    assert data["success"] is True
    assert data["counts"]["tests"] == 1
    assert data["environment"] == "ci"
    assert read_json(directory / "run.json").success
    assert (directory / "report.html").exists()
    cases = parse_junit(directory / "junit.xml")
    assert len(cases) == 1 and cases[0].name == "test<&>"


def test_html_escapes_all_untrusted_content():
    html = render_html(result("failed"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "FAILED" in html
    assert "test&lt;&amp;&gt;" in html


def test_missing_results_emit_synthetic_junit_error(tmp_path):
    run = result()
    run.repositories[0].status = "incomplete"
    run.repositories[0].results_complete = False
    run.repositories[0].issue = "Report unavailable"
    directory = write_reports(run, tmp_path)
    root = ElementTree.parse(directory / "junit.xml").getroot()
    assert int(root.get("errors")) == 1
    assert len(root.findall(".//error")) == 1
    assert not read_json(directory / "run.json").success


def test_report_success_is_recomputed_from_evidence(tmp_path):
    run = result("failed")
    directory = write_reports(run, tmp_path)
    path = directory / "run.json"
    data = json.loads(path.read_text())
    data["success"] = True
    data["counts"] = {"tests": 100, "passed": 100}
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = read_json(path)
    assert not loaded.success
    assert loaded.counts.failed == 1


def test_malformed_json_and_duplicate_run_directory(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        read_json(path)
    run = result()
    write_reports(run, tmp_path)
    with pytest.raises(FileExistsError):
        write_reports(run, tmp_path)
