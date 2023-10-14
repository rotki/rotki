from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.airdrops.constants import ETHEREUM_AIRDROPS_LIST
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregator

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator

    from .node_inquirer import EthereumInquirer


class EthereumAccountingAggregator(EVMAccountingAggregator):

    def __init__(
            self,
            node_inquirer: 'EthereumInquirer',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            msg_aggregator=msg_aggregator,
            airdrops_list=ETHEREUM_AIRDROPS_LIST,
        )
