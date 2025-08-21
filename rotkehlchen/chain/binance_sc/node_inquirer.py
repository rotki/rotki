from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BSC_BNB
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
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
    PRUNED_NODE_CHECK_TX_HASH,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.etherscan import Etherscan


class BinanceSCInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.BINANCE_SC,
            contracts=(contracts := EvmContracts[Literal[ChainID.BINANCE_SC]](chain_id=ChainID.BINANCE_SC)),  # noqa: E501
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_BSC_BNB.resolve_to_crypto_asset(),
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

    def get_blocknumber_by_time(
            self,
            ts: 'Timestamp',
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Searches for the blocknumber of a specific timestamp.
        Reimplemented because bsc doesn't have a blockscout api.

        May raise RemoteError
        """
        return self.etherscan.get_blocknumber_by_time(
            chain_id=self.chain_id,
            ts=ts,
            closest=closest,
        )
