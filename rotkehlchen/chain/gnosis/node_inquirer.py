import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Literal

from eth_typing.abi import ABI
from web3 import Web3

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain
from rotkehlchen.utils.misc import bytes_to_address, get_chunks

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

GNOSIS_PAY_SAFE_ADMINS_CONTRACT: Final = string_to_evm_address('0x5De882ac4c220f69ADC18Ab242e5F0b834e302A2')  # noqa: E501
GNOSIS_PAY_SAFE_ADMINS_ABI: Final[ABI] = [{'inputs': [{'name': 'addresses', 'type': 'address[]'}], 'name': 'get_admins', 'outputs': [{'name': '', 'type': 'address[][]'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
GNOSIS_PAY_SAFE_QUERY_CHUNK_SIZE: Final[int] = 64  # defined in the contract
# Gnosis Pay's post-hack migration re-points a compromised safe's singleton to a frozen
# implementation whose getOwners()/getModulesPaginated() return empty, so the helper above
# can't see the admins. The data still lives in the proxy's own storage though, so we recover
# it from there (Safe storage layout: `modules` mapping at slot 1, `owners` mapping at slot 2)
# and query the first (Delay) module directly, since the module proxy itself is not frozen.
SAFE_MODULES_STORAGE_SLOT: Final = 1
SAFE_OWNERS_STORAGE_SLOT: Final = 2
SAFE_SENTINEL_ADDRESS: Final = string_to_evm_address('0x0000000000000000000000000000000000000001')
SAFE_MODULE_CONTROLLED_OWNER: Final = string_to_evm_address('0x0000000000000000000000000000000000000002')  # noqa: E501
SAFE_MODULES_PAGINATED_ABI: Final[ABI] = [{'inputs': [{'name': 'start', 'type': 'address'}, {'name': 'pageSize', 'type': 'uint256'}], 'name': 'getModulesPaginated', 'outputs': [{'name': 'array', 'type': 'address[]'}, {'name': 'next', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


class GnosisInquirer(EvmNodeInquirer):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            blockscout: 'Blockscout',
            routescan: 'Routescan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.GNOSIS]](chain_id=ChainID.GNOSIS)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockscout=blockscout,
            routescan=routescan,
            blockchain=SupportedBlockchain.GNOSIS,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            native_token=A_XDAI.resolve_to_crypto_asset(),
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
                    # helper sees no admins. The safe's singleton may have been frozen by
                    # Gnosis Pay's post-hack migration, hiding its modules. Recover from storage.
                    if len(recovered := self._recover_admins_from_frozen_safe(address)) != 0:
                        result[address] = recovered
                    continue

                if not isinstance(admins, (tuple, list)):
                    log.error(f'Unexpected format in the list of admins. {admins}')
                    raise RemoteError('Failed to query on chain data for GnosisPay admins. Check logs for more details')  # noqa: E501

                result[address] = [deserialize_evm_address(admin) for admin in admins]

        return result

    def _read_safe_mapping_address(
            self,
            safe_address: ChecksumEvmAddress,
            base_slot: int,
            key: ChecksumEvmAddress,
    ) -> ChecksumEvmAddress:
        """Read mapping(address => address)[key] directly from a Safe proxy's own storage.

        Used to recover data that a frozen safe singleton no longer returns via its view
        functions. May raise RemoteError or DeserializationError.
        """
        return bytes_to_address(self.get_storage_at(
            account_address=safe_address,
            position=int.from_bytes(Web3.keccak(
                int(key, 16).to_bytes(32) + base_slot.to_bytes(32),
            )),
        ))

    def _recover_admins_from_frozen_safe(
            self,
            safe_address: ChecksumEvmAddress,
    ) -> list[ChecksumEvmAddress]:
        """Recover a Gnosis Pay safe's admins when its singleton has been frozen by Gnosis
        Pay's post-hack migration so that getOwners()/getModulesPaginated() return empty.

        The module list still lives in the proxy's own storage, so we read the first module
        (the Zodiac Delay module) from there and query that live module for its enabled
        modules, which are the admins. Returns an empty list for anything that is not a
        module-controlled Gnosis Pay safe.

        Best-effort: any failure (e.g. no rpc node able to read storage) is swallowed and
        returns [] so it can never break detection for the other queried safes.
        """
        try:
            if self._read_safe_mapping_address(  # only module-controlled safes (owner == 0x..02)
                safe_address=safe_address,
                base_slot=SAFE_OWNERS_STORAGE_SLOT,
                key=SAFE_SENTINEL_ADDRESS,
            ) != SAFE_MODULE_CONTROLLED_OWNER:
                return []

            if (delay_module := self._read_safe_mapping_address(  # modules[SENTINEL] is modules[0]
                safe_address=safe_address,
                base_slot=SAFE_MODULES_STORAGE_SLOT,
                key=SAFE_SENTINEL_ADDRESS,
            )) in (ZERO_ADDRESS, SAFE_SENTINEL_ADDRESS):
                return []

            return [deserialize_evm_address(admin) for admin in self.call_contract(
                contract_address=delay_module,  # the Delay module proxy itself is not frozen
                abi=SAFE_MODULES_PAGINATED_ABI,
                method_name='getModulesPaginated',
                arguments=[SAFE_SENTINEL_ADDRESS, GNOSIS_PAY_SAFE_QUERY_CHUNK_SIZE],
            )[0]]
        except (RemoteError, BlockchainQueryError, DeserializationError) as e:
            log.error('Failed to recover gnosis pay admins for frozen safe %s: %s', safe_address, e)  # noqa: E501
            return []
