from typing import TYPE_CHECKING, Dict, List, Optional

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator

from .common import AaveHistory, AaveInquirer

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class AaveGraphInquirer(AaveInquirer):
    """Reads Aave historical data from the graph protocol"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            premium: Optional[Premium],
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/aave/protocol-raw')

    def get_history_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
            to_block: int,
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """
        Queries aave history for a list of addresses.

        This function should be entered while holding the history_lock
        semaphore
        """
        result = {}
        for address in addresses:
            last_query = self.database.get_used_query_range(f'aave_events_{address}')
            history_results = self.get_history_for_address(
                user_address=address,
                to_block=to_block,
                given_from_block=last_query[1] + 1 if last_query is not None else None,
            )
            if len(history_results.events) == 0:
                continue
            result[address] = history_results

        return result

    def get_history_for_address(
            self,
            user_address: ChecksumEthAddress,
            to_block: int,
            atokens_list: Optional[List[EthereumToken]] = None,
            given_from_block: Optional[int] = None,
    ) -> AaveHistory:
        """
        Queries aave history for a single address.

        This function should be entered while holding the history_lock
        semaphore
        """
        return AaveHistory(events=[], total_earned={})
