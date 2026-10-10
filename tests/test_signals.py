import os
import signal
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group behavior")
@pytest.mark.parametrize("interruption", [signal.SIGINT, signal.SIGTERM])
def test_signal_writes_interrupted_report(tmp_path, interruption):
    import yaml

    repo = tmp_path / "repo"
    repo.mkdir()
    config = tmp_path / "testpilot.yml"
    config.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repositories": [
                    {
                        "name": "sleep",
                        "path": "repo",
                        "command": [
                            sys.executable,
                            "-c",
                            "import time; from pathlib import Path; "
                            "Path('ready').touch(); time.sleep(30)",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.Popen(
        [sys.executable, "-m", "testpilot", "run", "-c", str(config)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while not (repo / "ready").exists() and proc.poll() is None:
            assert time.monotonic() < deadline, "Test subprocess never became ready"
            time.sleep(0.02)
        assert proc.poll() is None
        proc.send_signal(interruption)
        proc.communicate(timeout=10)
        assert proc.returncode == 130
        assert list((tmp_path / "reports").glob("*/run.json"))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
