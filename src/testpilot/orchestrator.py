"""Ordered parallel test orchestration."""

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from uuid import uuid4

from testpilot.models import RepositoryResult, ResolvedRepository, RunResult, Settings
from testpilot.runner import run_repository


def execute(settings: Settings, cancel: threading.Event | None = None) -> RunResult:
    cancellation = cancel if cancel is not None else threading.Event()
    started = time.monotonic()
    timestamp = datetime.now(UTC)
    results: dict[str, RepositoryResult] = {}
    pool = ThreadPoolExecutor(max_workers=settings.parallel, thread_name_prefix="testpilot")
    futures: dict[Future[RepositoryResult], ResolvedRepository] = {}
    try:
        for repo in settings.repositories:
            future = pool.submit(run_repository, repo, cancellation)
            futures[future] = repo
        for future in as_completed(futures):
            repo = futures[future]
            results[repo.name] = future.result()
    except KeyboardInterrupt:
        cancellation.set()
    finally:
        # Every worker sees cancellation; pending workers return without spawning.
        pool.shutdown(wait=True)
    for future, repo in futures.items():
        if repo.name not in results:
            results[repo.name] = future.result()
    return RunResult(
        run_id=f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        timestamp=timestamp,
        environment=settings.environment,
        duration=time.monotonic() - started,
        repositories=[
            results.get(repo.name)
            or RepositoryResult(
                name=repo.name, status="interrupted", issue="Execution cancelled before submission"
            )
            for repo in settings.repositories
        ],
    )
