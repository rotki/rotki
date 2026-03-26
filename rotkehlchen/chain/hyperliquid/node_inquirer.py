import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain
from rotkehlchen.utils.misc import from_wei

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.blockscout import Blockscout
    from rotkehlchen.externalapis.etherscan import Etherscan
    from rotkehlchen.externalapis.routescan import Routescan

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HyperliquidInquirer(EvmNodeInquirer):
    """Node inquirer for Hyperliquid L1 (HyperEVM).

    Overrides get_multi_balance because the MyCrypto BalanceScanner contract
    is not deployed on Hyperliquid.  Individual eth_getBalance calls are used
    instead (the address count per user is small, so batching is unnecessary).
    """

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
            contract_multicall=contracts.contract(
                string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11'),
            ),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=Asset('HYPE').resolve_to_crypto_asset(),
        )

    def get_multi_balance(
            self,
            accounts: Sequence[ChecksumEvmAddress],
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[ChecksumEvmAddress, FVal]:
        """Query native HYPE balances via individual eth_getBalance calls.

        The MyCrypto BalanceScanner contract is not deployed on Hyperliquid,
        so we fall back to per-address RPC queries.

        May raise:
        - RemoteError if all nodes fail for every address
        """
        balances: dict[ChecksumEvmAddress, FVal] = {}
        if len(accounts) == 0:
            return balances

        log.debug(
            f'Querying {self.chain_name} chain for {self.blockchain.serialize()} balance',
            eth_addresses=accounts,
        )
        resolved_call_order = call_order if call_order is not None else self.default_call_order()
        for account in accounts:
            try:
                raw_balance = self._query(
                    method=self._get_balance,
                    call_order=resolved_call_order,
                    address=account,
                    block_identifier='latest',
                )
                balances[account] = from_wei(raw_balance)
            except RemoteError as e:
                log.error(f'Failed to query {self.chain_name} balance for {account}: {e}')
                balances[account] = FVal(0)

        return balances

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )
