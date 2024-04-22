from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.accounting.thegraph.accountant import ThegraphCommonAccountant

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class ThegraphAccountant(ThegraphCommonAccountant):

    def __init__(
            self,
            node_inquirer: 'ArbitrumOneInquirer',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            msg_aggregator=msg_aggregator,
        )
