import os
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group behavior")
def test_sigint_writes_interrupted_report(tmp_path):
    # Full CLI signal test added after CLI implementation; fixtures require no services.
    import signal

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
                        "command": [sys.executable, "-c", "import time; time.sleep(30)"],
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
        time.sleep(1)
        proc.send_signal(signal.SIGINT)
        proc.communicate(timeout=10)
        assert proc.returncode == 130
        assert list((tmp_path / "reports").glob("*/run.json"))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
