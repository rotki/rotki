from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    HYPERLIQUID_MULTICALL_ADDRESS,
    PRUNED_NODE_CHECK_TX_HASH,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.blockscout import Blockscout
    from rotkehlchen.externalapis.etherscan import Etherscan
    from rotkehlchen.externalapis.routescan import Routescan


class HyperliquidInquirer(EvmNodeInquirer):
    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            blockscout: 'Blockscout',
            routescan: 'Routescan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.HYPERLIQUID]](chain_id=ChainID.HYPERLIQUID)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockscout=blockscout,
            routescan=routescan,
            blockchain=SupportedBlockchain.HYPERLIQUID,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(HYPERLIQUID_MULTICALL_ADDRESS),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_HYPE.resolve_to_crypto_asset(),
        )

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )
