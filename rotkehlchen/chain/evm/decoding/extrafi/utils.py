import json
from typing import TYPE_CHECKING, Final, Literal

from eth_utils import to_checksum_address

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.extrafi.constants import EXTRAFI_FARMING_CONTRACT
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import CacheType, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer


def maybe_query_farm_data(
        vault_id: int,
        evm_inquirer: 'EvmNodeInquirer',
        farm_contract: EvmContract | None = None,
) -> tuple['EvmToken', 'EvmToken', 'EvmToken']:
    """Query vault information for an extrafi position. First check the cache and if we don't
    have it cached then query the chain.
    """
    globaldb = GlobalDBHandler()
    evm_addresses: tuple[ChecksumEvmAddress, ChecksumEvmAddress, ChecksumEvmAddress]
    cache_key: Final[tuple[Literal[CacheType.EXTRAFI_FARM_METADADATA], str, str]] = (
        CacheType.EXTRAFI_FARM_METADADATA,
        str(evm_inquirer.chain_id.serialize_for_db()),
        str(vault_id),
    )

    with globaldb.conn.read_ctx() as cursor:
        if (db_data := globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=cache_key,
        )) is None:
            if farm_contract is None:
                farm_contract = EvmContract(
                address=EXTRAFI_FARMING_CONTRACT,
                abi=evm_inquirer.contracts.abi('EXTRAFI_FARM'),
                deployed_block=0,  # is not used here
            )
            raw_data = farm_contract.call(
                node_inquirer=evm_inquirer,
                method_name='getVault',
                arguments=[vault_id],
            )
            evm_addresses = (
                to_checksum_address(raw_data[1]),  # lp token
                to_checksum_address(raw_data[2]),  # token0
                to_checksum_address(raw_data[3]),  # token1
            )
            with globaldb.conn.write_ctx() as write_cursor:
                globaldb_set_unique_cache_value(
                    write_cursor=write_cursor,
                    key_parts=cache_key,
                    value=json.dumps(evm_addresses),
                )
        else:
            evm_addresses = json.loads(db_data)

    return tuple(
        get_or_create_evm_token(
            userdb=evm_inquirer.database,
            evm_address=address,
            chain_id=evm_inquirer.chain_id,
        ) for address in evm_addresses
    )  # type: ignore  # mypy doesn't understand that since evm_addresses has length 3 the returned tuple will also have length 3
