from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType

from .interfaces import ModuleAccountantInterface
from .structures import TxEventSettings

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class BaseAirdropsAccountant(ModuleAccountantInterface):

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            msg_aggregator: 'MessagesAggregator',
            airdrops_list: list[str],
    ) -> None:
        super().__init__(node_inquirer=node_inquirer, msg_aggregator=msg_aggregator)
        self.airdrops_list = airdrops_list

    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, protocol): TxEventSettings(  # noqa: E501
                taxable=False,  # this used to depend on ledger actions. Needs https://github.com/rotki/rotki/issues/4341  # noqa: E501
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                accounting_treatment=None,
            )
            for protocol in self.airdrops_list
        }
