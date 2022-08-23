from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List

from rotkehlchen.chain.ethereum.defi.structures import DefiProtocolBalances
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZerionSDK
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class DefiChad():
    """An aggregator for many things ethereum DeFi"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
            database: 'DBHandler',
    ) -> None:
        self.ethereum = ethereum_manager
        self.zerion_sdk = ZerionSDK(
            ethereum_manager=ethereum_manager,
            msg_aggregator=msg_aggregator,
            database=database,
        )

    def query_defi_balances(
            self,
            addresses: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, List[DefiProtocolBalances]]:
        defi_balances = defaultdict(list)
        for account in addresses:
            balances = self.zerion_sdk.all_balances_for_account(account)
            if len(balances) != 0:
                defi_balances[account] = balances
        return defi_balances
