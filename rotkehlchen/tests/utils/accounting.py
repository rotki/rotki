"""
Accounting test utilities

This utilities file has been temporarily removed as part of the ProcessedAccountingEvent removal.
The utilities need to be completely rewritten to work with the new system where
history events are decorated with accounting information rather than creating
separate ProcessedAccountingEvent objects.

TODO: Rewrite utilities to work with HistoryEventWithAccounting and new accounting system
"""
from typing import Any

from rotkehlchen.fval import FVal


# Stub functions for compatibility
def accounting_history_process(*args, **kwargs) -> None:
    """Stub for accounting_history_process - needs reimplementation"""


def check_pnls_and_csv(*args, **kwargs) -> None:
    """Stub for check_pnls_and_csv - needs reimplementation"""


def assert_pnl_totals_close(*args, **kwargs) -> None:
    """Stub for assert_pnl_totals_close - needs reimplementation"""


def get_calculated_asset_amount(*args, **kwargs) -> FVal:
    """Stub for get_calculated_asset_amount - needs reimplementation"""
    return FVal(0)


# Stub data for compatibility
history1: list[Any] = []
