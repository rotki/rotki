import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap import AMMSwapPlatform
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V1, CPT_UNISWAP_V2
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Uniswap(AMMSwapPlatform, EthereumModule):
    """Uniswap integration module

    * Uniswap subgraph:
    https://github.com/Uniswap/uniswap-v2-subgraph
    https://github.com/croco-finance/uniswap-v3-subgraph
    """
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            counterparties=[CPT_UNISWAP_V1, CPT_UNISWAP_V2],  # counterparties for ammswapinterface. uniswap v3 doesn't follow it.  # noqa: E501
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
