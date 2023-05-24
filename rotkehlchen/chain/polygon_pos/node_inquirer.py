import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, cast

from eth_typing import BlockNumber

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    POLYGON_POS_ETHERSCAN_NODE,
    POLYGON_POS_ETHERSCAN_NODE_NAME,
    PRUNED_NODE_CHECK_TX_HASH,
)
from .etherscan import PolygonPOSEtherscan

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PolygonPOSInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            connect_at_start: Sequence[WeightedNode],
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        etherscan = PolygonPOSEtherscan(
            database=database,
            msg_aggregator=database.msg_aggregator,
        )
        contracts = EvmContracts[Literal[ChainID.POLYGON_POS]](chain_id=ChainID.POLYGON_POS)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.POLYGON_POS,
            etherscan_node=POLYGON_POS_ETHERSCAN_NODE,
            etherscan_node_name=POLYGON_POS_ETHERSCAN_NODE_NAME,
            contracts=contracts,
            connect_at_start=connect_at_start,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x275617327c958bD06b5D6b871E7f491D76113dd8')),  # noqa: E501
            contract_scan=contracts.contract(string_to_evm_address('0x2aB513B211C801673758D1C32815605B5289ad29')),  # noqa: E501
        )
        self.etherscan = cast(PolygonPOSEtherscan, self.etherscan)

    # -- Implementation of EvmNodeInquirer base methods --

    def query_highest_block(self) -> BlockNumber:
        block_number = self.etherscan.get_latest_block_number()
        log.debug('Polygon POS highest block result', block=block_number)
        return BlockNumber(block_number)

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )

    def get_blocknumber_by_time(
            self,
            ts: Timestamp,
            etherscan: bool = True,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Searches for the blocknumber of a specific timestamp

        May raise RemoteError
        """
        return self.etherscan.get_blocknumber_by_time(ts=ts, closest=closest)
