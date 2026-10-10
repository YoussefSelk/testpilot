"""Run the same quality gates and offline demonstration in every CI provider."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    (root / "reports").mkdir(exist_ok=True)
    commands = [
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
        ["mypy"],
        [
            "pytest",
            "--junitxml=reports/unit-tests.xml",
            "--cov=testpilot",
            "--cov-report=term-missing",
            "--cov-report=xml:reports/coverage.xml",
        ],
        ["testpilot", "validate", "-c", "testpilot.yml", "--env", "ci"],
        ["testpilot", "run", "-c", "testpilot.yml", "--env", "ci", "--parallel", "4"],
    ]
    for command in commands:
        print(f"Checking: {' '.join(command)}", flush=True)
        result = subprocess.run([sys.executable, "-m", *command], cwd=root, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
