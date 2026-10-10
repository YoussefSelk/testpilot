from pathlib import Path

import pytest

from testpilot.junit import JUnitError, parse_junit


def write_xml(tmp_path: Path, xml: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(xml, encoding="utf-8")
    return path


@pytest.mark.parametrize("wrapper", ["testsuite", "testsuites"])
def test_outcomes_and_details(tmp_path, wrapper):
    suite = """<testsuite tests="4" failures="1" errors="1" skipped="1">
      <testcase name="ok" classname="Unit" time="0.5"/>
      <testcase name="fail"><failure message="wrong">trace</failure></testcase>
      <testcase name="error"><error message="oops">stack</error></testcase>
      <testcase name="skip"><skipped message="later"/></testcase>
    </testsuite>"""
    xml = suite if wrapper == "testsuite" else f"<testsuites>{suite}</testsuites>"
    cases = parse_junit(write_xml(tmp_path, xml))
    assert [c.outcome for c in cases] == ["passed", "failed", "error", "skipped"]
    assert cases[0].classname == "Unit"
    assert cases[0].duration == 0.5
    assert "wrong" in cases[1].detail and "trace" in cases[1].detail


def test_nested_suites_count_once(tmp_path):
    xml = """<testsuites tests="2"><testsuite tests="2">
      <testcase name="a"/><testsuite tests="1"><testcase name="b"/></testsuite>
    </testsuite></testsuites>"""
    assert len(parse_junit(write_xml(tmp_path, xml))) == 2


@pytest.mark.parametrize(
    "xml",
    [
        "<testsuite>",
        "<random/>",
        "<testsuite tests='2'><testcase name='a'/></testsuite>",
        "<testsuite><testcase time='NaN'/></testsuite>",
        "<testsuite failures='1'><testcase name='a'/></testsuite>",
        "<testsuite tests='-1'/>",
        '<!DOCTYPE x [<!ENTITY a "expanded">]><testsuite><testcase name="&a;"/></testsuite>',
    ],
)
def test_malformed_unsafe_or_inconsistent(tmp_path, xml):
    with pytest.raises(JUnitError):
        parse_junit(write_xml(tmp_path, xml))


def test_missing_report(tmp_path):
    with pytest.raises(JUnitError, match="Cannot read"):
        parse_junit(tmp_path / "missing.xml")
