"""Aggregate testcase evidence with explicit execution errors for CI consumers."""

import re
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

from testpilot.models import RunResult


def xml_text(value: str) -> str:
    return re.sub(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]", "", value)


def write_junit(run: RunResult, path: Path) -> None:
    root = Element("testsuites", {"name": "TestPilot", "time": f"{run.duration:.6f}"})
    total_tests = total_errors = 0
    for repo in run.repositories:
        synthetic = not repo.results_complete or (
            not repo.success and repo.counts.failed == 0 and repo.counts.errors == 0
        )
        counts = repo.counts
        tests = counts.tests + int(synthetic)
        errors = counts.errors + int(synthetic)
        total_tests += tests
        total_errors += errors
        suite = SubElement(
            root,
            "testsuite",
            {
                "name": xml_text(repo.name),
                "tests": str(tests),
                "failures": str(counts.failed),
                "errors": str(errors),
                "skipped": str(counts.skipped),
                "time": f"{repo.duration:.6f}",
                "timestamp": run.timestamp.isoformat(),
            },
        )
        properties = SubElement(suite, "properties")
        for name, value in (
            ("environment", run.environment),
            ("status", repo.status),
            ("results_complete", str(repo.results_complete).lower()),
        ):
            SubElement(properties, "property", {"name": name, "value": xml_text(value)})
        for case in repo.cases:
            node = SubElement(
                suite,
                "testcase",
                {
                    "name": xml_text(case.name),
                    "classname": xml_text(case.classname),
                    "time": f"{case.duration:.6f}",
                },
            )
            if case.outcome != "passed":
                tag = {"failed": "failure", "error": "error", "skipped": "skipped"}[case.outcome]
                SubElement(node, tag).text = xml_text(case.detail)
        if synthetic:
            node = SubElement(
                suite,
                "testcase",
                {
                    "name": "__testpilot_execution__",
                    "classname": "testpilot.execution",
                    "time": "0",
                },
            )
            SubElement(
                node, "error", {"message": xml_text(repo.issue or repo.status)}
            ).text = "TestPilot could not verify a complete successful execution."
    root.set("tests", str(total_tests))
    root.set("failures", str(run.counts.failed))
    root.set("errors", str(total_errors))
    root.set("skipped", str(run.counts.skipped))
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
