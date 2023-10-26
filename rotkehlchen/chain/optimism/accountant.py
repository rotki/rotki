from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregator
from rotkehlchen.chain.optimism.modules.airdrops.decoder import AirdropsDecoder

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator

    from .node_inquirer import OptimismInquirer


class OptimismAccountingAggregator(EVMAccountingAggregator):

    def __init__(
            self,
            node_inquirer: 'OptimismInquirer',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            msg_aggregator=msg_aggregator,
            modules_path='rotkehlchen.chain.optimism.modules',
            airdrops_list=AirdropsDecoder.counterparties(),
        )
