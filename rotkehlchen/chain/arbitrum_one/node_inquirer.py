import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

from web3.types import BlockIdentifier

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import (
    ETHEREUM_ETHERSCAN_NODE,
)
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.etherscan import Etherscan

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ArbitrumOneInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.ARBITRUM_ONE]](chain_id=ChainID.ARBITRUM_ONE)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.ARBITRUM_ONE,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_ETH.resolve_to_crypto_asset(),
            blockscout=Blockscout(
                blockchain=SupportedBlockchain.ARBITRUM_ONE,
                database=database,
                msg_aggregator=database.msg_aggregator,
            ),
        )

    # -- Implementation of EvmNodeInquirer base methods --

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )

    def multicall(
            self,
            calls: list[tuple[ChecksumEvmAddress, str]],
            require_success: bool = True,
            call_order: Sequence['WeightedNode'] | None = None,
            block_identifier: BlockIdentifier = 'latest',
            calls_chunk_size: int = MULTICALL_CHUNKS,
    ) -> Any:
        """Overrides multicall to handle etherscan's gas limit constraints on Arbitrum.

        Etherscan on Arbitrum has reduced gas limits which limits the number of multicall
        calls that can be batched together. This implementation tries regular nodes first
        with normal chunk sizes, then falls back to etherscan with smaller chunks (3).
        """
        call_order = self.default_call_order() if call_order is None else call_order
        try:
            return super().multicall(
                calls=calls,
                require_success=require_success,
                call_order=[node for node in call_order if node != ETHEREUM_ETHERSCAN_NODE],
                block_identifier=block_identifier,
                calls_chunk_size=calls_chunk_size,
            )
        except (RemoteError, BlockchainQueryError):
            return super().multicall(
                calls=calls,
                require_success=require_success,
                call_order=[ETHEREUM_ETHERSCAN_NODE],
                block_identifier=block_identifier,
                calls_chunk_size=3,
            )
