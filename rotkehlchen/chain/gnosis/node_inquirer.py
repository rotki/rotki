import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Literal

from eth_typing.abi import ABI

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks

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

GNOSIS_PAY_SAFE_ADMINS_CONTRACT: Final = string_to_evm_address('0x5De882ac4c220f69ADC18Ab242e5F0b834e302A2')  # noqa: E501
GNOSIS_PAY_SAFE_ADMINS_ABI: Final[ABI] = [{'inputs': [{'name': 'addresses', 'type': 'address[]'}], 'name': 'get_admins', 'outputs': [{'name': '', 'type': 'address[][]'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
GNOSIS_PAY_SAFE_QUERY_CHUNK_SIZE: Final[int] = 64  # defined in the contract


class GnosisInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.GNOSIS]](chain_id=ChainID.GNOSIS)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.GNOSIS,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_XDAI.resolve_to_crypto_asset(),
            blockscout=Blockscout(
                blockchain=SupportedBlockchain.GNOSIS,
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

    def get_safe_admins_for_addresses(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[ChecksumEvmAddress]]:
        """Return mapping of address -> safe admins (non-empty).
        May raise:
            - RemoteError
            - DeserializationError
        """
        if not addresses:
            return {}

        result: dict[ChecksumEvmAddress, list[ChecksumEvmAddress]] = {}
        for chunk in get_chunks(addresses, GNOSIS_PAY_SAFE_QUERY_CHUNK_SIZE):
            admins_result = self.call_contract(
                contract_address=GNOSIS_PAY_SAFE_ADMINS_CONTRACT,
                abi=GNOSIS_PAY_SAFE_ADMINS_ABI,
                method_name='get_admins',
                arguments=[(chunk_list := list(chunk))],
            )

            if (
                not isinstance(admins_result, (tuple, list)) or
                len(admins_result) != len(chunk_list)
            ):
                log.error(f'GnosisPay helper returned an unexpected result format {admins_result} for {chunk_list}')  # noqa: E501
                raise RemoteError('Failed to query on chain data for GnosisPay admins. Check logs for more details')  # noqa: E501

            for address, admins in zip(chunk_list, admins_result, strict=True):
                if not admins:
                    continue

                if not isinstance(admins, (tuple, list)):
                    log.error(f'Unexpected format in the list of admins. {admins}')
                    raise RemoteError('Failed to query on chain data for GnosisPay admins. Check logs for more details')  # noqa: E501

                result[address] = [deserialize_evm_address(admin) for admin in admins]

        return result
