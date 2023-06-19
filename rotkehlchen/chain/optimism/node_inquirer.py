import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, Optional, cast

from eth_typing import BlockNumber

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT, FAKE_GENESIS_TX_RECEIPT, GENESIS_HASH
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer, EvmNodeInquirerWithDSProxy
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int_from_hex
from rotkehlchen.serialization.serialize import process_result
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


class OptimismInquirer(EvmNodeInquirerWithDSProxy):

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
    
    def _get_transaction_receipt(
            self,
            web3: Optional[Web3],
            tx_hash: EVMTxHash,
    ) -> Optional[dict[str, Any]]:
        if tx_hash == GENESIS_HASH:
            return FAKE_GENESIS_TX_RECEIPT
        if web3 is None:
            tx_receipt = self.etherscan.get_transaction_receipt(tx_hash)
            if tx_receipt is None:
                return None

            try:
                # Turn hex numbers to int
                block_number = int(tx_receipt['blockNumber'], 16)
                tx_receipt['blockNumber'] = block_number
                tx_receipt['cumulativeGasUsed'] = int(tx_receipt['cumulativeGasUsed'], 16)
                tx_receipt['gasUsed'] = int(tx_receipt['gasUsed'], 16)
                tx_receipt['l1Fee'] = int(tx_receipt['l1Fee'], 16)
                tx_receipt['status'] = int(tx_receipt.get('status', '0x1'), 16)
                tx_index = int(tx_receipt['transactionIndex'], 16)
                tx_receipt['transactionIndex'] = tx_index
                for receipt_log in tx_receipt['logs']:
                    receipt_log['blockNumber'] = block_number
                    receipt_log['logIndex'] = deserialize_int_from_hex(
                        symbol=receipt_log['logIndex'],
                        location='etherscan tx receipt',
                    )
                    receipt_log['transactionIndex'] = tx_index
            except (DeserializationError, ValueError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'missing key {msg}'
                log.error(
                    f'Couldnt deserialize transaction receipt {tx_receipt} data from '
                    f'etherscan due to {msg}',
                )
                raise RemoteError(
                    f'Couldnt deserialize transaction receipt data from etherscan '
                    f'due to {msg}. Check logs for details',
                ) from e
            return tx_receipt

        # Can raise TransactionNotFound if the user's node is pruned and transaction is old
        tx_receipt = web3.eth.get_transaction_receipt(tx_hash)  # type: ignore
        return process_result(tx_receipt)
