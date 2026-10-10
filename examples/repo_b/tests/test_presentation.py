import os

import pytest
from presentation import stock_label


@pytest.mark.parametrize("units,expected", [(0, "Out of stock"), (3, "3 available")])
def test_stock_label(units, expected):
    assert stock_label(units) == expected


def test_profile_environment():
    assert os.environ.get("APP_ENV", "local") in {"local", "test", "development", "staging"}
    if os.environ.get("TESTPILOT_DEMO_FAIL") == "1":
        pytest.fail("Intentional failure to demonstrate TestPilot exit status and reporting")


@pytest.mark.skip(reason="External service excluded from the offline demonstration")
def test_external_service():
    pass
