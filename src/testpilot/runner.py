"""Subprocess execution with cancellation and process cleanup."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from testpilot.junit import JUnitError, parse_junit
from testpilot.models import RepositoryResult, ResolvedRepository, Status


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    """Kill the owned process group/tree and reap its direct child."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()


def run_repository(repo: ResolvedRepository, cancel: threading.Event) -> RepositoryResult:
    started = time.monotonic()
    result = RepositoryResult(name=repo.name, status="interrupted")
    if cancel.is_set():
        result.issue = "Execution cancelled before starting"
        return result
    process: subprocess.Popen[bytes] | None = None
    try:
        if repo.junit:
            repo.junit.parent.mkdir(parents=True, exist_ok=True)
            repo.junit.unlink(missing_ok=True)
        command = repo.command.copy()
        # Windows searches the parent application's directory before PATH. Resolve
        # bare executables explicitly so activated virtual environments are honored.
        executable = (
            shutil.which(command[0], path=repo.env.get("PATH"))
            if not os.path.dirname(command[0])
            else None
        )
        if executable:
            command[0] = executable
        # Windows may implicitly execute batch files through a shell; reject them.
        if os.name == "nt":
            if command[0].lower().endswith((".cmd", ".bat")):
                raise ValueError("Windows batch commands must be replaced with a direct executable")
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(
                command,
                cwd=repo.cwd,
                env=repo.env,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=os.name != "nt",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            status: Status | None = None
            deadline = time.monotonic() + repo.timeout
            while True:
                if cancel.is_set():
                    status = "interrupted"
                    result.issue = "Execution interrupted"
                    terminate_tree(process)
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status = "timeout"
                    result.issue = f"Execution exceeded timeout ({repo.timeout:g}s)"
                    terminate_tree(process)
                    break
                try:
                    process.wait(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            result.exit_code = process.returncode
            stdout.seek(0)
            stderr.seek(0)
            result.stdout = stdout.read().decode("utf-8", errors="replace")
            result.stderr = stderr.read().decode("utf-8", errors="replace")
        if repo.junit:
            try:
                result.cases = parse_junit(repo.junit)
                result.results_complete = bool(result.cases) and status is None
                if not result.cases:
                    result.issue = result.issue or "JUnit report contains no testcases"
            except JUnitError as exc:
                result.issue = result.issue or str(exc)
        else:
            result.issue = result.issue or "No JUnit output configured; test results unavailable"
        if status:
            result.status = status
        elif result.exit_code != 0 or result.counts.failed or result.counts.errors:
            result.status = "failed"
            if result.exit_code != 0:
                result.issue = result.issue or f"Test command exited with status {result.exit_code}"
        elif not result.results_complete:
            result.status = "incomplete"
        else:
            result.status = "passed"
    except (OSError, ValueError) as exc:
        result.status = "error"
        result.issue = f"Cannot execute repository: {type(exc).__name__}: {exc}"
    finally:
        if process is not None and process.poll() is None:
            terminate_tree(process)
        result.duration = time.monotonic() - started
    return result
