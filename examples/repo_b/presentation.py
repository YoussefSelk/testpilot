"""Small presentation-layer example, independent of TestPilot."""


def stock_label(units: int) -> str:
    if units < 0:
        raise ValueError("Units cannot be negative")
    return "Out of stock" if units == 0 else f"{units} available"
