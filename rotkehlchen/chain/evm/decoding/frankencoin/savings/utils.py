"""Pure conversion helpers for Frankencoin savings positions."""

from rotkehlchen.fval import FVal


def savings_position_to_zchf(
        position_units: int,
        conversion_rate: int,
) -> FVal:
    """Convert contract accounting units into currently redeemable ZCHF.

    TODO: Implement this from the savings contract's exact units, decimals and
    interest-accrual formula. Keeping it separate makes the math easy to unit test.
    """
    raise NotImplementedError
