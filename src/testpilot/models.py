"""Configuration contracts and persisted execution results."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

PositiveSeconds = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Duration = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Workers = Annotated[int, Field(ge=1, le=256)]
Outcome = Literal["passed", "failed", "error", "skipped"]
Status = Literal["passed", "failed", "error", "timeout", "interrupted", "incomplete"]


class EnvironmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("env")
    @classmethod
    def valid_environment(cls, value: dict[str, str]) -> dict[str, str]:
        for key, item in value.items():
            if not key or "=" in key or "\0" in key or "\0" in item:
                raise ValueError("Environment names/values cannot contain NUL or invalid names")
        return value


class Defaults(EnvironmentModel):
    timeout: PositiveSeconds = 300
    parallel: Workers = 2
    report_dir: str = Field(default="reports", min_length=1)


class Profile(EnvironmentModel):
    timeout: PositiveSeconds | None = None
    parallel: Workers | None = None
    report_dir: str | None = Field(default=None, min_length=1)


class Repository(EnvironmentModel):
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    path: str = Field(min_length=1)
    command: list[str] = Field(min_length=1)
    working_dir: str | None = Field(default=None, min_length=1)
    timeout: PositiveSeconds | None = None
    junit: str | None = Field(default=None, min_length=1)

    @field_validator("command")
    @classmethod
    def valid_command(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or "\0" in item for item in value):
            raise ValueError("Command must contain nonempty arguments without NUL")
        return value


class Configuration(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    version: Literal[1]
    defaults: Defaults = Field(default_factory=Defaults)
    profiles: dict[str, Profile] = Field(default_factory=dict)
    repositories: list[Repository] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        names = [repo.name for repo in self.repositories]
        if len(names) != len(set(names)):
            raise ValueError("Repository names must be unique")
        return self


@dataclass
class ResolvedRepository:
    name: str
    path: Path
    cwd: Path
    command: list[str]
    timeout: float
    env: dict[str, str]
    junit: Path | None


@dataclass
class Settings:
    environment: str
    parallel: int
    report_dir: Path
    repositories: list[ResolvedRepository]


class CaseResult(BaseModel):
    name: str
    classname: str = ""
    duration: Duration = 0
    outcome: Outcome = "passed"
    detail: str = ""


class Counts(BaseModel):
    tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0


def count_cases(cases: list[CaseResult]) -> Counts:
    return Counts(
        tests=len(cases),
        passed=sum(c.outcome == "passed" for c in cases),
        failed=sum(c.outcome == "failed" for c in cases),
        errors=sum(c.outcome == "error" for c in cases),
        skipped=sum(c.outcome == "skipped" for c in cases),
    )


class RepositoryResult(BaseModel):
    name: str
    status: Status
    exit_code: int | None = None
    duration: Duration = 0
    stdout: str = ""
    stderr: str = ""
    issue: str = ""
    results_complete: bool = False
    cases: list[CaseResult] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def counts(self) -> Counts:
        return count_cases(self.cases)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success(self) -> bool:
        return (
            self.status == "passed"
            and self.exit_code == 0
            and self.results_complete
            and bool(self.cases)
            and all(c.outcome in ("passed", "skipped") for c in self.cases)
        )


class RunResult(BaseModel):
    schema_version: Literal[1] = 1
    run_id: str
    timestamp: datetime
    environment: str
    duration: Duration
    repositories: list[RepositoryResult]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def counts(self) -> Counts:
        return count_cases([case for repo in self.repositories for case in repo.cases])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success(self) -> bool:
        return bool(self.repositories) and all(repo.success for repo in self.repositories)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def results_complete(self) -> bool:
        return bool(self.repositories) and all(r.results_complete for r in self.repositories)
