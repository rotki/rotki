from typing import Optional, TYPE_CHECKING

from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule


if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class Eth2(EthereumModule):
    """Module representation for Eth2"""

    def __init__(
        self,
        ethereum_manager: 'EthereumManager',
        database: 'DBHandler',
        premium: Optional[Premium],
        msg_aggregator: MessagesAggregator,
    ) -> None:
        self.database = database
        self.premium = premium
        self.ethereum_manager = ethereum_manager
        self.msg_aggregator = msg_aggregator

    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_eth2_deposits()
        self.database.delete_eth2_daily_stats()
