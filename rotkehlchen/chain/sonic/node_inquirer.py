from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_S
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain
from rotkehlchen.utils.misc import from_wei

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
    SONIC_MULTICALL_ADDRESS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.blockscout import Blockscout
    from rotkehlchen.externalapis.etherscan import Etherscan
    from rotkehlchen.externalapis.routescan import Routescan
    from rotkehlchen.tasks.supervisor import TaskSupervisor


class SonicInquirer(EvmNodeInquirer):

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
            blockchain=SupportedBlockchain.SONIC,
            contracts=(contracts := EvmContracts[Literal[ChainID.SONIC]](chain_id=ChainID.SONIC)),
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(SONIC_MULTICALL_ADDRESS),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_S.resolve_to_crypto_asset(),
        )

    # -- Implementation of EvmNodeInquirer base methods --

    def get_multi_balance(
            self,
            accounts: Sequence[ChecksumEvmAddress],
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[ChecksumEvmAddress, FVal]:
        """Sonic has no deployed balance scanner contract, so query the native
        balance of each account individually through the RPC nodes."""
        if len(accounts) == 0:
            return {}

        balances: dict[ChecksumEvmAddress, FVal] = {}
        for account in accounts:
            result = self._query(
                method=self._get_balance,
                call_order=call_order if call_order is not None else self.default_call_order(),
                address=account,
                block_identifier='latest',
            )
            balances[account] = from_wei(FVal(result))

        return balances

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )
