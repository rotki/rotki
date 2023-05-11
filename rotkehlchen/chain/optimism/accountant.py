from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregator
from rotkehlchen.user_messages import MessagesAggregator

from .constants import CPT_OPTIMISM

if TYPE_CHECKING:
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
            airdrops_list=[CPT_OPTIMISM],
        )
