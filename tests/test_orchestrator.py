import sys
import threading

from testpilot.config import load_config, resolve
from testpilot.orchestrator import execute


def test_parallel_processes_overlap_and_preserve_order(config_file):
    path = config_file()
    base = path.parent
    repositories = []
    for name in ("second", "first"):
        directory = base / name
        directory.mkdir()
        # Rendezvous makes this fail if orchestration silently becomes sequential.
        code = (
            "import time; from pathlib import Path; "
            f"Path('../{name}.ready').touch(); "
            "deadline=time.monotonic()+5\n"
            "while len(list(Path('..').glob('*.ready'))) < 2:\n"
            " if time.monotonic()>deadline: raise SystemExit(9)\n"
            " time.sleep(0.02)\n"
            "Path('results.xml').write_text('<testsuite><testcase name=\"ok\"/></testsuite>')"
        )
        repositories.append(
            {
                "name": name,
                "path": name,
                "command": [sys.executable, "-c", code],
                "junit": "results.xml",
            }
        )
    path = config_file(repositories=repositories)
    run = execute(resolve(load_config(path), path, parallel=2))
    assert run.success
    assert [r.name for r in run.repositories] == ["second", "first"]
    assert run.counts.tests == 2
    assert run.counts.passed == 2


def test_sequential_aggregates_failures(config_file):
    path = config_file()
    repositories = []
    for name, body in (
        ("good", "<testcase name='a'/><testcase name='b'><skipped/></testcase>"),
        ("bad", "<testcase name='c'><failure>trace</failure></testcase>"),
    ):
        (path.parent / name).mkdir()
        xml = f"<testsuite>{body}</testsuite>"
        code = f"from pathlib import Path; Path('r.xml').write_text({xml!r})"
        repositories.append(
            {"name": name, "path": name, "command": [sys.executable, "-c", code], "junit": "r.xml"}
        )
    path = config_file(repositories=repositories)
    run = execute(resolve(load_config(path), path, parallel=1))
    assert not run.success
    assert run.counts.model_dump() == {
        "tests": 3,
        "passed": 1,
        "failed": 1,
        "errors": 0,
        "skipped": 1,
    }
    assert [r.status for r in run.repositories] == ["passed", "failed"]


def test_cancelled_run_includes_every_repository(config_file):
    path = config_file()
    cancel = threading.Event()
    cancel.set()
    run = execute(resolve(load_config(path), path), cancel)
    assert [r.status for r in run.repositories] == ["interrupted"]
    assert not run.success
