from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregator

from .constants import CPT_BASE

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator
    from .node_inquirer import BaseInquirer


class BaseAccountingAggregator(EVMAccountingAggregator):

    def __init__(
            self,
            node_inquirer: 'BaseInquirer',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            msg_aggregator=msg_aggregator,
            airdrops_list=[CPT_BASE],
        )
