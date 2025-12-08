import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.l2_with_l1_fees.node_inquirer import L2WithL1FeesInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
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
    from rotkehlchen.externalapis.routescan import Routescan

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ScrollInquirer(L2WithL1FeesInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            routescan: 'Routescan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.SCROLL]](chain_id=ChainID.SCROLL)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            routescan=routescan,
            blockchain=SupportedBlockchain.SCROLL,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_ETH.resolve_to_crypto_asset(),
            blockscout=Blockscout(
                blockchain=SupportedBlockchain.SCROLL,
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
