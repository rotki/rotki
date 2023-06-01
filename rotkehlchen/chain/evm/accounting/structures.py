from collections.abc import Iterator
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional, Protocol

from rotkehlchen.accounting.structures.evm_event import EvmEvent

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class HistoryBaseEntriesAccountantCallback(Protocol):
    """Type of a Submodule's accountant callback"""
    def __call__(
            self,
            pot: 'AccountingPot',
            event: 'EvmEvent',
            other_events: Iterator['EvmEvent'],
    ) -> None:
        """
        Callback to be called by the accounting module.
        If the callback expects more than 1 events, it is supposed to iterate over the
        `other_events` iterator to get them.
        Note that events consumed by the callback from the iterator will not be re-processed later.
        """


class TxAccountingTreatment(Enum):
    SWAP = 0


class BaseEventSettins:
    """Settings for history base entry accounting"""
    def __init__(
            self,
            taxable: bool,
            count_entire_amount_spend: bool,
            count_cost_basis_pnl: bool,
            method: Literal['acquisition', 'spend'],
            accounting_treatment: Optional[TxAccountingTreatment] = None,
    ):
        self.taxable = taxable
        self.count_entire_amount_spend = count_entire_amount_spend
        self.count_cost_basis_pnl = count_cost_basis_pnl
        self.method = method
        self.accounting_treatment = accounting_treatment


class TxEventSettings(BaseEventSettins):
    """Settings for history base entry accounting"""
    def __init__(
            self,
            taxable: bool,
            count_entire_amount_spend: bool,
            count_cost_basis_pnl: bool,
            method: Literal['acquisition', 'spend'],
            accounting_treatment: Optional[TxAccountingTreatment] = None,
            accountant_cb: Optional[HistoryBaseEntriesAccountantCallback] = None,
    ):
        super().__init__(
            taxable=taxable,
            count_entire_amount_spend=count_entire_amount_spend,
            count_cost_basis_pnl=count_cost_basis_pnl,
            method=method,
            accounting_treatment=accounting_treatment,
        )
        self.accountant_cb = accountant_cb
