from typing import TYPE_CHECKING

from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.types import ExternalService, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


class ArbitrumOneEtherscan(Etherscan):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            chain=SupportedBlockchain.ARBITRUM_ONE,
            base_url='arbiscan.io',
            service=ExternalService.ARBITRUM_ONE_ETHERSCAN,
        )
