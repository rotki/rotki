from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

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
            airdrops_list: list[CounterpartyDetails],
    ) -> None:
        super().__init__(node_inquirer=node_inquirer, msg_aggregator=msg_aggregator)
        self.airdrops_list = airdrops_list

    def event_settings(self, pot: 'AccountingPot') -> dict[int, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, protocol.identifier): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                accounting_treatment=None,
            )
            for protocol in self.airdrops_list
        }
