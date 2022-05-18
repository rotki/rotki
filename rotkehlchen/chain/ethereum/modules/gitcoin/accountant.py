from typing import TYPE_CHECKING, Dict

from rotkehlchen.accounting.structures.base import (
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.chain.ethereum.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.ethereum.accounting.structures import TxEventSettings

from .constants import CPT_GITCOIN

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class GitcoinAccountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.DONATE, CPT_GITCOIN): TxEventSettings(  # noqa: E501
                taxable=True,
                # Do not count donation as expense
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='spend',
                take=1,
                multitake_treatment=None,
            ),
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.DONATE, CPT_GITCOIN): TxEventSettings(  # noqa: E501
                taxable=True,
                # Do not count donation as expense
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='acquisition',
                take=1,
                multitake_treatment=None,
            ),
        }
