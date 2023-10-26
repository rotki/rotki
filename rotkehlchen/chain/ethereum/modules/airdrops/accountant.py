from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.accounting.airdrop import BaseAirdropsAccountant
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class AirdropsAccountant(BaseAirdropsAccountant):

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            msg_aggregator: 'MessagesAggregator',
            airdrops_list: list[CounterpartyDetails],
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            msg_aggregator=msg_aggregator,
            airdrops_list=airdrops_list,
        )
