from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


@dataclass
class AccountingData:
    """Accounting data for a single history event"""
    total_amount_before: FVal
    cost_basis_before: FVal | None
    is_taxable: bool
    pnl_taxable: FVal
    pnl_free: FVal
    settings_hash: str


@dataclass
class HistoryEventWithAccounting:
    """History event with accounting data overlay"""
    event: 'HistoryBaseEntry'
    accounting_data: AccountingData | None  # None if not calculated yet