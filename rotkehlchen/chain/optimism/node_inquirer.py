import logging
from typing import TYPE_CHECKING, Any, Literal, cast

from eth_typing import BlockNumber

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import DSProxyInquirerWithCacheData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.externalapis.utils import maybe_read_integer
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
    OPTIMISM_ETHERSCAN_NODE,
    OPTIMISM_ETHERSCAN_NODE_NAME,
    PRUNED_NODE_CHECK_TX_HASH,
)
from .etherscan import OptimismEtherscan

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismInquirer(DSProxyInquirerWithCacheData):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
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
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x2DC0E2aa608532Da689e89e237dF582B783E552C')),  # noqa: E501
            contract_scan=contracts.contract(string_to_evm_address('0x1e21bc42FaF802A0F115dC998e2F0d522aDb1F68')),  # noqa: E501
            dsproxy_registry=contracts.contract(string_to_evm_address('0x283Cc5C26e53D66ed2Ea252D986F094B37E6e895')),  # noqa: E501
            native_token=A_ETH.resolve_to_crypto_asset(),
        )
        self.etherscan = cast(OptimismEtherscan, self.etherscan)

    def _additional_receipt_processing(self, tx_receipt: dict[str, Any]) -> None:
        """Performs additional tx_receipt processing where necessary

        May raise:
            - DeserializationError if it can't convert a value to an int or if an unexpected
            type is given.
            - KeyError if tx_receipt has no l1Fee entry
        """
        tx_receipt['l1Fee'] = maybe_read_integer(data=tx_receipt, key='l1Fee', api='web3 optimism')

    # -- Implementation of EvmNodeInquirer base methods --

    def query_highest_block(self) -> BlockNumber:
        block_number = self.etherscan.get_latest_block_number()
        log.debug('Optimism highest block result', block=block_number)
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
