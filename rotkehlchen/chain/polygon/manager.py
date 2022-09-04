import logging
from typing import TYPE_CHECKING, Any, Dict, Sequence

from eth_typing import BlockNumber

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.types import WeightedNode, string_to_evm_address
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.constants.ethereum import ETH_SCAN, MATIC_MULTICALL, MATIC_MULTICALL_2
from rotkehlchen.externalapis.etherscan import Polygonscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

from .constants import POLYGONSCAN_NODE, POLYGONSCAN_NODE_NAME

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


MAX_ADDRESSES_IN_REVERSE_ENS_QUERY = 80


class PolygonManager(EvmManager):
    """PolygonManager inherits from EvmManager and defines Polygon-specific methods
    such as ENS resolution."""
    def __init__(
            self,
            polygonscan: Polygonscan,
            msg_aggregator: MessagesAggregator,
            greenlet_manager: GreenletManager,
            connect_at_start: Sequence[WeightedNode],
            database: 'DBHandler',
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        log.debug(f'Initializing Polygon Manager. Nodes to connect {connect_at_start}')

        super().__init__(
            etherscan=polygonscan,
            msg_aggregator=msg_aggregator,
            greenlet_manager=greenlet_manager,
            connect_at_start=connect_at_start,
            database=database,
            etherscan_node=POLYGONSCAN_NODE,
            etherscan_node_name=POLYGONSCAN_NODE_NAME,
            blockchain=SupportedBlockchain.POLYGON,
            contract_scan=ETH_SCAN[SupportedBlockchain.POLYGON],
            contract_multicall=MATIC_MULTICALL,
            contract_multicall_2=MATIC_MULTICALL_2,
            rpc_timeout=rpc_timeout,
        )
        # A cache for the erc20 contract info to not requery same one
        # TODO: Add WETH for Polygon too?
        self.contract_info_cache: Dict[ChecksumEvmAddress, Dict[str, Any]] = {}

    def have_archive(self, requery: bool = False) -> bool:
        if self.queried_archive_connection and requery is False:
            return self.archive_connection

        balance = self.get_historical_balance(
            address=string_to_evm_address('0x5973918275c01f50555d44e92c9d9b353cadad54'),
            block_number=483,
        )
        # TODO: validar y ajustar FVal(), tambien se puede probar con block_number=1787
        self.archive_connection = balance is not None and balance == FVal('5.1063307')
        self.queried_archive_connection = True
        return self.archive_connection

    def query_highest_block(self) -> BlockNumber:
        block_number = self.etherscan.get_latest_block_number()
        log.debug('Polygon highest block result', block=block_number)
        return BlockNumber(block_number)

    def get_blocknumber_by_time(self, ts: Timestamp, etherscan: bool = True) -> int:
        """Searches for the blocknumber of a specific timestamp
        - Performs the etherscan api call
        - Raises RemoteError if there is any connection issue with etherscan
        """
        if not etherscan:
            raise NotImplementedError('No alternative method for polygon get_blocknumber')

        return self.etherscan.get_blocknumber_by_time(ts)
