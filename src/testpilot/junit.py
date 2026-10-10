"""Hardened JUnit XML parsing."""

import math
from pathlib import Path
from xml.etree.ElementTree import Element, ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from testpilot.models import CaseResult, Outcome, count_cases


class JUnitError(ValueError):
    pass


def case_result(node: Element) -> CaseResult:
    duration = float(node.get("time", "0"))
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("Test duration must be finite and nonnegative")
    outcome: Outcome = "passed"
    details: list[str] = []
    outcomes: list[tuple[str, Outcome]] = [
        ("error", "error"),
        ("failure", "failed"),
        ("skipped", "skipped"),
    ]
    for tag, status in outcomes:
        elements = node.findall(tag)
        if elements:
            outcome = status
            for item in elements:
                details.append("\n".join(filter(None, [item.get("message", ""), item.text or ""])))
            break
    return CaseResult(
        name=node.get("name", "unnamed"),
        classname=node.get("classname", ""),
        duration=duration,
        outcome=outcome,
        detail="\n".join(details),
    )


def parse_junit(path: Path) -> list[CaseResult]:
    try:
        # Forbid DTDs and entities, including unused declarations.
        root = ElementTree.parse(
            path, forbid_dtd=True, forbid_entities=True, forbid_external=True
        ).getroot()
        if root is None or root.tag not in ("testsuite", "testsuites"):
            raise ValueError("Expected testsuite or testsuites root")
        cases = [case_result(node) for node in root.iter("testcase")]
        for suite in root.iter():
            if suite.tag not in ("testsuite", "testsuites"):
                continue
            counts = count_cases([case_result(n) for n in suite.iter("testcase")])
            expected = {
                "tests": counts.tests,
                "failures": counts.failed,
                "errors": counts.errors,
                "skipped": counts.skipped,
            }
            for attribute, actual in expected.items():
                declared = suite.get(attribute)
                if declared is not None and int(declared) != actual:
                    raise ValueError(f"Declared {attribute} differs from testcase elements")
        return cases
    except OSError as exc:
        raise JUnitError(f"Cannot read JUnit report: {exc.strerror}") from None
    except (ParseError, DefusedXmlException, ValueError, LookupError) as exc:
        raise JUnitError(f"Invalid JUnit report: {exc}") from None
