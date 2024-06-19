import logging
from typing import TYPE_CHECKING, Literal, cast

from eth_typing import BlockNumber

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    GNOSIS_ETHERSCAN_NODE,
    GNOSIS_ETHERSCAN_NODE_NAME,
    PRUNED_NODE_CHECK_TX_HASH,
)
from .etherscan import GnosisEtherscan

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GnosisInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        etherscan = GnosisEtherscan(
            database=database,
            msg_aggregator=database.msg_aggregator,
        )
        contracts = EvmContracts[Literal[ChainID.GNOSIS]](chain_id=ChainID.GNOSIS)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.GNOSIS,
            etherscan_node=GNOSIS_ETHERSCAN_NODE,
            etherscan_node_name=GNOSIS_ETHERSCAN_NODE_NAME,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(string_to_evm_address('0x571C62a1c863aEAD01c1d34D8cB3Ee2c6f938800')),
            native_token=A_XDAI.resolve_to_crypto_asset(),
        )
        self.etherscan = cast(GnosisEtherscan, self.etherscan)

    # -- Implementation of EvmNodeInquirer base methods --

    def query_highest_block(self) -> BlockNumber:
        block_number = self.etherscan.get_latest_block_number()
        log.debug('Gnosis highest block result', block=block_number)
        return BlockNumber(block_number)

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )
