import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirerWithDSProxy
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HasDSProxy(EthereumModule):
    """Implements the EthereumModule interface to properly query proxies on account addition"""

    def __init__(
            self,
            ethereum_inquirer: 'EvmNodeInquirerWithDSProxy',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        self.ethereum.proxies_inquirer.reset_last_query_ts()
        # Get the proxy of the account
        proxy_result = self.ethereum.proxies_inquirer.get_account_proxy(address)
        if proxy_result is None:
            return None

        # add it to the mapping
        self.ethereum.proxies_inquirer.add_mapping(address, proxy_result)
        return None

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        self.ethereum.proxies_inquirer.reset_last_query_ts()

    def deactivate(self) -> None:
        pass
