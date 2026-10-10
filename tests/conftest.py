import sys
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def config_file(tmp_path: Path):
    def write(repositories=None, **settings):
        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        data = {
            "version": 1,
            "repositories": repositories
            or [
                {
                    "name": "backend",
                    "path": "repo",
                    "command": [sys.executable, "-c", "pass"],
                    "junit": "results.xml",
                }
            ],
            **settings,
        }
        path = tmp_path / "testpilot.yml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path

    return write
