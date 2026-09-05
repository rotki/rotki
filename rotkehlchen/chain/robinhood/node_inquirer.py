import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain
from rotkehlchen.utils.misc import from_wei

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
    ROBINHOOD_MULTICALL_ADDRESS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.blockscout import Blockscout
    from rotkehlchen.externalapis.etherscan import Etherscan
    from rotkehlchen.externalapis.routescan import Routescan
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

    def get_multi_balance(
            self,
            accounts: Sequence[ChecksumEvmAddress],
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[ChecksumEvmAddress, FVal]:
        """Query native balances through Multicall3's getEthBalance.

        The rotki balance scanner is not deployed on Robinhood chain yet. Once it is,
        drop this override so the default scanner path in the base class is used.

        May raise:
        - RemoteError if the multicall fails on all nodes.
        """
        if len(accounts) == 0:
            return {}

        log.debug(
            'Querying Robinhood chain for ETH balances via multicall',
            eth_addresses=accounts,
        )
        results = self.multicall(
            calls=[(
                self.contract_multicall.address,
                self.contract_multicall.encode(method_name='getEthBalance', arguments=[account]),
            ) for account in accounts],
            call_order=call_order,
        )
        return {
            account: from_wei(FVal(self.contract_multicall.decode(
                result=result,
                method_name='getEthBalance',
                arguments=[account],
            )[0]))
            for account, result in zip(accounts, results, strict=True)
        }

    # -- Implementation of EvmNodeInquirer base methods --

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )
