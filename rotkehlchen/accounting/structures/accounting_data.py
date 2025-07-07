from dataclasses import dataclass

from rotkehlchen.fval import FVal


@dataclass
class AccountingData:
    """Accounting data for a single history event"""
    total_amount_before: FVal
    cost_basis_before: FVal | None
    is_taxable: bool
    pnl_taxable: FVal
    pnl_free: FVal
    settings_hash: str
