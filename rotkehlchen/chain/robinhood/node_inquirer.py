import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
    ROBINHOOD_MULTICALL_ADDRESS,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.blockscout import Blockscout
    from rotkehlchen.externalapis.etherscan import Etherscan
    from rotkehlchen.externalapis.routescan import Routescan
    from rotkehlchen.fval import FVal
    from rotkehlchen.tasks.supervisor import TaskSupervisor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RobinhoodInquirer(EvmNodeInquirer):

    def __init__(
            self,
            task_supervisor: TaskSupervisor,
            database: DBHandler,
            etherscan: Etherscan,
            blockscout: Blockscout,
            routescan: Routescan,
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        super().__init__(
            task_supervisor=task_supervisor,
            database=database,
            etherscan=etherscan,
            blockscout=blockscout,
            routescan=routescan,
            blockchain=SupportedBlockchain.ROBINHOOD,
            contracts=(contracts := EvmContracts[Literal[ChainID.ROBINHOOD]](chain_id=ChainID.ROBINHOOD)),  # noqa: E501
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(ROBINHOOD_MULTICALL_ADDRESS),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_ETH.resolve_to_crypto_asset(),
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
