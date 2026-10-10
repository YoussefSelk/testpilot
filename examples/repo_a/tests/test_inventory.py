import pytest
from inventory import available_units


@pytest.mark.parametrize("stock,reserved,expected", [(10, 3, 7), (0, 0, 0), (5, 5, 0)])
def test_available_units(stock, reserved, expected):
    assert available_units(stock, reserved) == expected


def test_overbooking_rejected():
    with pytest.raises(ValueError):
        available_units(3, 4)
