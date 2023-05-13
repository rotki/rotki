from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.defi.structures import DefiProtocolBalances
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZerionSDK
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


class DefiChad():
    """An aggregator for many things ethereum DeFi"""

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            msg_aggregator: MessagesAggregator,
            database: 'DBHandler',
    ) -> None:
        self.zerion_sdk = ZerionSDK(
            ethereum_inquirer=ethereum_inquirer,
            msg_aggregator=msg_aggregator,
            database=database,
        )

    def query_defi_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[DefiProtocolBalances]]:
        defi_balances = defaultdict(list)
        for account in addresses:
            balances = self.zerion_sdk.all_balances_for_account(account)
            if len(balances) != 0:
                defi_balances[account] = balances
        return defi_balances
