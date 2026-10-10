"""Small backend inventory example, independent of TestPilot."""


def available_units(stock: int, reserved: int) -> int:
    if stock < 0 or reserved < 0 or reserved > stock:
        raise ValueError("Invalid stock reservation")
    return stock - reserved
