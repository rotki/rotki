import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.optimism_superchain.etherscan import OptimismSuperchainEtherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExternalService, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseEtherscan(OptimismSuperchainEtherscan):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            chain=SupportedBlockchain.BASE,
            base_url='basescan.org',
            service=ExternalService.BASE_ETHERSCAN,
        )
