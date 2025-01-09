from typing import TYPE_CHECKING, Literal, cast

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BSC_BNB
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    BINANCE_SC_ETHERSCAN_NODE,
    BINANCE_SC_ETHERSCAN_NODE_NAME,
    PRUNED_NODE_CHECK_TX_HASH,
)
from .etherscan import BinanceSCEtherscan

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class BinanceSCInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=BinanceSCEtherscan(
                database=database,
                msg_aggregator=database.msg_aggregator,
            ),
            blockchain=SupportedBlockchain.BINANCE_SC,
            etherscan_node=BINANCE_SC_ETHERSCAN_NODE,
            etherscan_node_name=BINANCE_SC_ETHERSCAN_NODE_NAME,
            contracts=(contracts := EvmContracts[Literal[ChainID.BINANCE_SC]](chain_id=ChainID.BINANCE_SC)),  # noqa: E501
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_BSC_BNB.resolve_to_crypto_asset(),
        )
        self.etherscan = cast('BinanceSCEtherscan', self.etherscan)

    # -- Implementation of EvmNodeInquirer base methods --

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )
