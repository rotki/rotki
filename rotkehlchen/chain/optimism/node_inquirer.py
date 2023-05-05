import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, cast

from eth_typing import BlockNumber
from requests.exceptions import RequestException
from web3 import Web3
from web3.exceptions import TransactionNotFound

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.errors.misc import BlockchainQueryError
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, SupportedBlockchain, Timestamp

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    OPTIMISM_ETHERSCAN_NODE,
    OPTIMISM_ETHERSCAN_NODE_NAME,
    PRUNED_NODE_CHECK_TX_HASH,
)
from .etherscan import OptimismEtherscan

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            connect_at_start: Sequence[WeightedNode],
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        etherscan = OptimismEtherscan(
            database=database,
            msg_aggregator=database.msg_aggregator,
        )
        contracts = EvmContracts[Literal[ChainID.OPTIMISM]](chain_id=ChainID.OPTIMISM)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.OPTIMISM,
            etherscan_node=OPTIMISM_ETHERSCAN_NODE,
            etherscan_node_name=OPTIMISM_ETHERSCAN_NODE_NAME,
            contracts=contracts,
            connect_at_start=connect_at_start,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x2DC0E2aa608532Da689e89e237dF582B783E552C')),  # noqa: E501
            contract_scan=contracts.contract(string_to_evm_address('0x1e21bc42FaF802A0F115dC998e2F0d522aDb1F68')),  # noqa: E501
            dsproxy_registry=contracts.contract(string_to_evm_address('0x283Cc5C26e53D66ed2Ea252D986F094B37E6e895')),  # noqa: E501
        )
        self.etherscan = cast(OptimismEtherscan, self.etherscan)

    # -- Implementation of EvmNodeInquirer base methods --

    def query_highest_block(self) -> BlockNumber:
        block_number = self.etherscan.get_latest_block_number()
        log.debug('Optimism highest block result', block=block_number)
        return BlockNumber(block_number)

    def _is_pruned(self, web3: Web3) -> bool:
        try:
            tx = web3.eth.get_transaction(PRUNED_NODE_CHECK_TX_HASH)  # type: ignore
        except (
            RequestException,
            TransactionNotFound,
            BlockchainQueryError,
            KeyError,
            ValueError,
        ):
            tx = None

        return tx is None

    def _have_archive(self, web3: Web3) -> bool:
        balance = self.get_historical_balance(
            address=ARCHIVE_NODE_CHECK_ADDRESS,
            block_number=ARCHIVE_NODE_CHECK_BLOCK,
            web3=web3,
        )
        return balance == ARCHIVE_NODE_CHECK_EXPECTED_BALANCE

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
