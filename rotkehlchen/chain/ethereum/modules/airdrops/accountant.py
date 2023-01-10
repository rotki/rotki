from typing import TYPE_CHECKING

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures.base import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings

from .constants import AIRDROPS_LIST

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class AirdropsAccountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        airdrops_taxable = LedgerActionType.AIRDROP in pot.settings.taxable_ledger_actions
        return {
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, counterparty): TxEventSettings(  # noqa: E501
                taxable=airdrops_taxable,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
                multitake_treatment=None,
            )
            for counterparty in AIRDROPS_LIST
        }
