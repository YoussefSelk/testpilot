# TestPilot implementation plan

The user-provided task is the binding specification. Execute inline without
approval pauses, as explicitly requested. The workspace is empty; implement on
main for the requested initial publication. No unrelated work is present.

1. Configuration (`models.py`, `config.py`, `tests/test_config.py`): test YAML,
   profile precedence, paths, command validation and output collisions; implement
   validated resolved settings. Verify focused pytest tests.
2. Execution (`runner.py`, `orchestrator.py`, runner/orchestrator tests): test real
   subprocess success, failures, deadlines, cancellation and concurrent overlap;
   implement process-group cleanup and ordered parallel results.
3. Results (`junit.py`, `aggregation.py`, reporting modules and their tests): test
   XML shapes, security, count consistency, missing/stale data and escaping;
   implement durable JSON, HTML and aggregate XML.
4. CLI (`cli.py`, `__main__.py`, CLI tests): verify all commands, init overwrite
   protection, filtering, profiles, predictable errors and exit statuses.
5. Delivery: runnable example repositories, README, MIT license, GitHub Actions,
   GitLab CI, Jenkins and non-root Docker. Run full pytest, Ruff, mypy, package
   build and actual CLI demos. Build/run Docker if its engine is available.
6. Review acceptance criteria, commit, create the public GitHub repository and
   push main without force. Verify remote commit and report external CI status.
