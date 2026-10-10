"""Validated JSON report persistence."""

from pathlib import Path

from pydantic import ValidationError

from testpilot.models import RunResult


def write_json(run: RunResult, path: Path) -> None:
    path.write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> RunResult:
    try:
        # Computed counts/success are ignored on input and derived again from evidence.
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError:
        raise ValueError("Invalid TestPilot JSON report") from None
