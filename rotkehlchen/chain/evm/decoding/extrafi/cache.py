import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.extrafi.constants import EXTRAFI_POOL_CONTRACT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_value,
    globaldb_set_general_cache_values_at_ts,
    globaldb_set_unique_cache_value_at_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import get_chunks, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
MAX_RESERVES_QUERIED_PER_CHUNK = 20  # the maximum number of reserves that we can query without etherscan failing  # noqa: E501


def get_existing_reward_pools(chain_id: ChainID) -> tuple[set[ChecksumEvmAddress]]:
    """Get extrafi rewards pools for extrafi lending"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return ({
            string_to_evm_address(address) for address in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(CacheType.EXTRAFI_REWARD_CONTRACTS, str(chain_id.serialize())),
            )
        },)


def query_extrafi_data(
        inquirer: 'EvmNodeInquirer',
        cache_type: Literal[CacheType.EXTRAFI_NEXT_RESERVE_ID],
        msg_aggregator: 'MessagesAggregator',
        reload_all: bool,
) -> list[ChecksumEvmAddress] | None:
    """Query and store information of rewards pools.
    Updates the last queried ts when executed.

    May raise:
    - RemoteError
    """
    lending_contract = EvmContract(
        address=EXTRAFI_POOL_CONTRACT,
        abi=inquirer.contracts.abi('EXTRAFI_LENDING'),
        deployed_block=96265067,
    )
    cache_key = (cache_type, str(inquirer.chain_id.serialize_for_db()))
    next_reserve_id = lending_contract.call(
        node_inquirer=inquirer,
        method_name='nextReserveId',
    )

    now = ts_now()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if reload_all is True or (saved_next_reserve_id_str := globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=cache_key,
        )) is None:
            saved_next_reserve_id = 1  # used later to start querying on reserve id 1
        else:
            saved_next_reserve_id = int(saved_next_reserve_id_str)

        if next_reserve_id == saved_next_reserve_id:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                globaldb_set_unique_cache_value_at_ts(
                    write_cursor=write_cursor,
                    key_parts=cache_key,
                    value=str(next_reserve_id),
                    timestamp=now,
                )
                return None

        reward_addresses = []
        for chunk in get_chunks(
            lst=range(saved_next_reserve_id, next_reserve_id),
            n=MAX_RESERVES_QUERIED_PER_CHUNK,
        ):
            calls = [(
                EXTRAFI_POOL_CONTRACT,
                lending_contract.encode(method_name='getStakingAddress', arguments=[idx]),
            ) for idx in chunk]

            try:
                outputs = inquirer.multicall_2(require_success=False, calls=calls)
            except RemoteError:
                outputs = [(False, b'') for _ in chunk]

            for idx, output in enumerate(outputs):
                status, encoded_data = output
                if status is False:
                    continue

                try:
                    reward_addresses.append(deserialize_evm_address(lending_contract.decode(
                        result=encoded_data,
                        method_name='getStakingAddress',
                        arguments=[chunk[idx]],
                    )[0]))
                except DeserializationError:
                    log.error(f'Failed to deserialize extrafi pool for reserve id {chunk[idx]}')

        with GlobalDBHandler().conn.write_ctx() as write_cursor:  # save queried data to the db
            globaldb_set_general_cache_values_at_ts(
                write_cursor=write_cursor,
                key_parts=(CacheType.EXTRAFI_REWARD_CONTRACTS, str(inquirer.chain_id.serialize())),
                values=reward_addresses,
                timestamp=now,
            )
            globaldb_set_unique_cache_value_at_ts(
                write_cursor=write_cursor,
                key_parts=cache_key,
                value=next_reserve_id,
                timestamp=now,
            )

        return reward_addresses
