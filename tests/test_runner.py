import sys
import threading
import time

import pytest

from testpilot.config import load_config, resolve
from testpilot.runner import run_repository


def make_repo(config_file, code, timeout=5, junit=True):
    path = config_file(
        repositories=[
            {
                "name": "demo",
                "path": "repo",
                "command": [sys.executable, "-c", code],
                "timeout": timeout,
                **({"junit": "results.xml"} if junit else {}),
                "env": {"TP_ENV": "works"},
            }
        ]
    )
    return resolve(load_config(path), path).repositories[0]


GOOD_XML = '<testsuite tests="1"><testcase name="ok"/></testsuite>'
WRITE_XML = f"from pathlib import Path; Path('results.xml').write_text({GOOD_XML!r}); "


def test_real_subprocess_output_environment_and_report(config_file):
    repo = make_repo(
        config_file,
        WRITE_XML + "import os,sys; print(os.environ['TP_ENV']); print('err',file=sys.stderr)",
    )
    result = run_repository(repo, threading.Event())
    assert result.success
    assert result.status == "passed"
    assert result.stdout.strip() == "works"
    assert result.stderr.strip() == "err"
    assert result.exit_code == 0
    assert result.duration > 0


def test_nonzero_cannot_pass_even_with_passing_junit(config_file):
    result = run_repository(
        make_repo(config_file, WRITE_XML + "raise SystemExit(7)"), threading.Event()
    )
    assert result.status == "failed"
    assert result.exit_code == 7
    assert not result.success


def test_junit_failure_cannot_pass_with_zero_exit(config_file):
    xml = '<testsuite><testcase name="bad"><failure message="no"/></testcase></testsuite>'
    repo = make_repo(
        config_file, f"from pathlib import Path; Path('results.xml').write_text({xml!r})"
    )
    result = run_repository(repo, threading.Event())
    assert result.status == "failed"
    assert not result.success


@pytest.mark.parametrize(
    "junit,code",
    [
        (True, "pass"),
        (False, "pass"),
        (True, "from pathlib import Path; Path('results.xml').write_text('<broken')"),
    ],
)
def test_unavailable_reports_fail(config_file, junit, code):
    repo = make_repo(config_file, code, junit=junit)
    result = run_repository(repo, threading.Event())
    assert result.status == "incomplete"
    assert not result.success
    assert result.issue


def test_stale_report_is_not_reused(config_file):
    repo = make_repo(config_file, "pass")
    repo.junit.write_text(GOOD_XML, encoding="utf-8")
    result = run_repository(repo, threading.Event())
    assert result.status == "incomplete"
    assert not result.cases


def test_timeout_captures_output(config_file):
    repo = make_repo(config_file, "import time; print('started',flush=True); time.sleep(30)", 0.4)
    result = run_repository(repo, threading.Event())
    assert result.status == "timeout"
    assert "started" in result.stdout
    assert result.duration < 8


def test_missing_executable(config_file):
    repo = make_repo(config_file, "pass")
    repo.command = ["testpilot-nonexistent-executable-12345"]
    result = run_repository(repo, threading.Event())
    assert result.status == "error"
    assert result.exit_code is None
    assert result.issue


def test_cancellation_stops_running_process(config_file):
    repo = make_repo(config_file, "import time; time.sleep(30)")
    cancel = threading.Event()
    timer = threading.Timer(0.3, cancel.set)
    timer.start()
    try:
        result = run_repository(repo, cancel)
    finally:
        timer.cancel()
    assert result.status == "interrupted"
    assert result.duration < 8


def test_timeout_cleans_descendants(config_file, tmp_path):
    marker = tmp_path / "leaked"
    child = f"import time; from pathlib import Path; time.sleep(1.5); Path({str(marker)!r}).touch()"
    code = (
        f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "time.sleep(30)"
    )
    result = run_repository(make_repo(config_file, code, 0.5), threading.Event())
    assert result.status == "timeout"
    time.sleep(1.7)
    assert not marker.exists(), "descendant survived timeout"
