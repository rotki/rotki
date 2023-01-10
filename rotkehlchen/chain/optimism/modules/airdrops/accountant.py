from typing import TYPE_CHECKING

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures.base import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.ethereum.accounting.structures import TxEventSettings

from .constants import CPT_OPTIMISM

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class AirdropsAccountant(ModuleAccountantInterface):
    # TODO: This is essentially same as airdrops accountant for ethereum.
    # Shouldn't we try to abstract it?
    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        airdrops_taxable = LedgerActionType.AIRDROP in pot.settings.taxable_ledger_actions
        return {
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, CPT_OPTIMISM): TxEventSettings(  # noqa: E501
                taxable=airdrops_taxable,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
                multitake_treatment=None,
            ),
        }
