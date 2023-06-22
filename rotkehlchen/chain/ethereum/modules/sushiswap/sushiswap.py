import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Sushiswap(AMMSwapPlatform, EthereumModule):
    """Sushiswap integration module

    * Sushiswap subgraph:
    https://github.com/sushiswap/sushiswap-subgraph
    """
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            counterparties=[CPT_SUSHISWAP_V2],
            ethereum_inquirer=ethereum_inquirer,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )

    def deactivate(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass
