"""TestPilot command-line interface."""

import signal
import threading
from enum import StrEnum
from pathlib import Path
from types import FrameType
from typing import Annotated, NoReturn

import typer
import yaml
from rich.console import Console
from rich.table import Table

from testpilot import __version__
from testpilot.config import ConfigError, load_config, resolve
from testpilot.models import RunResult
from testpilot.orchestrator import execute
from testpilot.reporting import write_reports
from testpilot.reporting.html_report import render_html
from testpilot.reporting.json_report import read_json, write_json
from testpilot.reporting.junit_report import write_junit

app = typer.Typer(
    help="Execute and aggregate tests across local repositories.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console(highlight=False)
ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="YAML configuration file.")]
EnvOption = Annotated[str | None, typer.Option("--env", help="Environment profile to apply.")]


class ReportFormat(StrEnum):
    html = "html"
    json = "json"
    junit = "junit"


def fail(message: str) -> NoReturn:
    console.print(f"Error: {message}", style="red", markup=False)
    raise typer.Exit(2)


def print_summary(result: RunResult) -> None:
    table = Table(title=f"TestPilot · {result.environment}")
    for column in (
        "Repository",
        "Status",
        "Tests",
        "Passed",
        "Failed",
        "Errors",
        "Skipped",
        "Time",
    ):
        table.add_column(column)
    for repo in result.repositories:
        c = repo.counts
        table.add_row(
            repo.name,
            repo.status,
            str(c.tests) if repo.cases else "unavailable",
            str(c.passed),
            str(c.failed),
            str(c.errors),
            str(c.skipped),
            f"{repo.duration:.3f}s",
        )
    console.print(table)
    console.print(
        f"{'PASSED' if result.success else 'FAILED / INCOMPLETE'} · {result.counts.tests} tests · "
        f"{result.duration:.3f}s · "
        f"Results {'complete' if result.results_complete else 'incomplete'}",
        markup=False,
    )
    for repo in result.repositories:
        if repo.issue:
            console.print(f"{repo.name}: {repo.issue}", markup=False)


@app.command()
def init(config: ConfigOption = Path("testpilot.yml")) -> None:
    """Create a starter configuration for tests in the current directory."""
    data = {
        "version": 1,
        "defaults": {"timeout": 300, "parallel": 2, "report_dir": "reports"},
        "profiles": {
            "local": {"env": {"APP_ENV": "local"}},
            "ci": {"env": {"APP_ENV": "test"}, "parallel": 4, "timeout": 600},
        },
        "repositories": [
            {
                "name": "current",
                "path": ".",
                "command": ["python", "-m", "pytest", "-q", "--junitxml=test-results.xml"],
                "junit": "test-results.xml",
            }
        ],
    }
    try:
        with config.open("x", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False)
    except OSError as exc:
        fail(f"Cannot create {config}: {exc.strerror}")
    console.print(
        f"Created {config}. Edit repository paths and commands before running.", markup=False
    )


@app.command()
def validate(config: ConfigOption = Path("testpilot.yml"), env: EnvOption = None) -> None:
    """Validate configuration, repository paths and JUnit output uniqueness."""
    try:
        settings = resolve(load_config(config), config, env)
    except (ConfigError, OSError, ValueError) as exc:
        fail(str(exc))
    console.print(f"Valid: {len(settings.repositories)} repositories ({settings.environment}).")


@app.command("list")
def list_repositories(config: ConfigOption = Path("testpilot.yml"), env: EnvOption = None) -> None:
    """Display configured repositories and their working directories."""
    try:
        settings = resolve(load_config(config), config, env)
    except (ConfigError, OSError, ValueError) as exc:
        fail(str(exc))
    table = Table(title="Configured repositories")
    for column in ("Repository", "Working directory", "Timeout", "JUnit"):
        table.add_column(column)
    for repo in settings.repositories:
        table.add_row(
            repo.name, str(repo.cwd), f"{repo.timeout:g}s", str(repo.junit or "unavailable")
        )
    console.print(table)


def interrupt_on_signal(signum: int, frame: FrameType | None) -> NoReturn:
    raise KeyboardInterrupt


@app.command()
def run(
    config: ConfigOption = Path("testpilot.yml"),
    env: EnvOption = None,
    parallel: Annotated[
        int | None, typer.Option(min=1, max=256, help="Worker count; 1 is sequential.")
    ] = None,
    repo: Annotated[
        list[str] | None, typer.Option(help="Repository name; repeat to select several.")
    ] = None,
    timeout: Annotated[
        float | None, typer.Option(min=0.001, help="Override every test timeout (seconds).")
    ] = None,
    report_dir: Annotated[
        str | None, typer.Option(help="Output directory, relative to config file.")
    ] = None,
) -> None:
    """Run tests and write JSON, HTML and aggregated JUnit reports."""
    try:
        settings = resolve(
            load_config(config),
            config,
            env,
            parallel=parallel,
            timeout=timeout,
            report_dir=report_dir,
            repo_names=repo,
        )
        # Fail before running tests when the destination cannot be created.
        settings.report_dir.mkdir(parents=True, exist_ok=True)
        previous = None
        if threading.current_thread() is threading.main_thread():
            previous = signal.signal(signal.SIGTERM, interrupt_on_signal)
        try:
            result = execute(settings)
        finally:
            if previous is not None:
                signal.signal(signal.SIGTERM, previous)
        directory = write_reports(result, settings.report_dir)
    except (ConfigError, OSError, ValueError) as exc:
        fail(str(exc))
    print_summary(result)
    console.print(f"Reports: {directory}", markup=False)
    if any(r.status == "interrupted" for r in result.repositories):
        raise typer.Exit(130)
    raise typer.Exit(0 if result.success else 1)


def discover_report(path: Path) -> Path:
    if path.is_file():
        return path
    if (path / "run.json").is_file():
        return path / "run.json"
    candidates = sorted(path.glob("*/run.json"))
    if not candidates:
        raise ValueError(f"No TestPilot run.json report found in {path}")
    return candidates[-1]


@app.command()
def report(
    input_path: Annotated[
        Path, typer.Option("--input", help="run.json, run directory or report root.")
    ] = Path("reports"),
    format: Annotated[
        ReportFormat, typer.Option("--format", help="Output format.")
    ] = ReportFormat.html,
    output: Annotated[
        Path | None, typer.Option(help="Destination file; defaults beside run.json.")
    ] = None,
) -> None:
    """Regenerate a report from the latest persisted run, preserving failure status."""
    try:
        source = discover_report(input_path)
        result = read_json(source)
        suffix = {ReportFormat.html: "html", ReportFormat.json: "json", ReportFormat.junit: "xml"}[
            format
        ]
        target = output or source.parent / f"report.{suffix}"
        if target.resolve() == source.resolve():
            raise ValueError("Report output cannot overwrite canonical run.json")
        if format == ReportFormat.html:
            target.write_text(render_html(result), encoding="utf-8")
        elif format == ReportFormat.json:
            write_json(result, target)
        else:
            write_junit(result, target)
    except (OSError, ValueError) as exc:
        fail(str(exc))
    console.print(f"Report: {target}", markup=False)
    raise typer.Exit(0 if result.success else 1)


@app.command()
def version() -> None:
    """Print the installed TestPilot version."""
    typer.echo(__version__)
