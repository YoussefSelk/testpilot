"""Dependency-free HTML reports."""

from html import escape

from testpilot.models import RunResult


def render_html(run: RunResult) -> str:
    rows: list[str] = []
    details: list[str] = []
    for repo in run.repositories:
        c = repo.counts
        rows.append(
            f"<tr><td>{escape(repo.name)}</td><td>{escape(repo.status)}</td>"
            f"<td>{c.tests}</td><td>{c.passed}</td><td>{c.failed}</td><td>{c.errors}</td>"
            f"<td>{c.skipped}</td><td>{repo.duration:.3f}s</td>"
            f"<td>{repo.exit_code if repo.exit_code is not None else 'unavailable'}</td>"
            f"<td>{'complete' if repo.results_complete else 'incomplete'}</td></tr>"
        )
        cases = "".join(
            f"<li><strong>{escape(c.classname)}::{escape(c.name)}</strong> "
            f"{escape(c.outcome)} ({c.duration:.3f}s)<pre>{escape(c.detail)}</pre></li>"
            for c in repo.cases
        )
        details.append(
            f"<section><h2>{escape(repo.name)}</h2><p>{escape(repo.issue)}</p><ul>{cases}</ul>"
            f"<details><summary>stdout</summary><pre>{escape(repo.stdout)}</pre></details>"
            f"<details><summary>stderr</summary><pre>{escape(repo.stderr)}</pre></details></section>"
        )
    counts = run.counts
    status = "PASSED" if run.success else "FAILED / INCOMPLETE"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>TestPilot report</title><style>
body{{font:16px system-ui,sans-serif;color:#172033;background:#f3f5f9;margin:2rem}}
main{{max-width:1200px;margin:auto}} section,header{{background:white;padding:1.5rem;
border-radius:12px;margin-bottom:1rem}}
table{{width:100%;border-collapse:collapse;background:white}}
th,td{{text-align:left;padding:.7rem;border-bottom:1px solid #dce2ec}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f7;padding:1rem}}
.table{{overflow:auto}} h1{{margin-top:0}} .status{{font-weight:bold}}
</style></head><body><main><header><h1>TestPilot</h1><p class="status">{status}</p>
<p>{escape(run.timestamp.isoformat())} · Environment: {escape(run.environment)} ·
Execution duration: {run.duration:.3f}s</p>
<p>{counts.tests} tests · {counts.passed} passed · {counts.failed} failed ·
{counts.errors} errors · {counts.skipped} skipped ·
Results: {"complete" if run.results_complete else "incomplete / unavailable"}</p></header>
<div class="table"><table><thead><tr><th>Repository</th><th>Status</th><th>Tests</th>
<th>Passed</th><th>Failed</th><th>Errors</th><th>Skipped</th><th>Duration</th>
<th>Exit code</th><th>Results</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
{"".join(details)}</main></body></html>"""
