import logging
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    CPT_AERODROME,
    CPT_VELODROME,
    SUGAR_V3_CONTRACT_ABI,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.evm.utils import (
    maybe_notify_cache_query_status,
    maybe_notify_new_pools_status,
)
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_like,
    globaldb_get_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    AddressbookEntry,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

VELODROME_LP_SUGAR_CONTRACT: Final = string_to_evm_address('0x1d5E1893fCfb62CAaCE48eB2BAF7a6E134a8a27c')  # Velodrome Finance LP Sugar v3  # noqa: E501
AERODROME_LP_SUGAR_CONTRACT: Final = string_to_evm_address('0x9DE6Eab7a910A288dE83a04b6A43B52Fd1246f1E')  # Aerodrome Finance LP Sugar v3  # noqa: E501
POOL_DATA_CHUNK_SIZE: Final = 500


class VelodromePoolData(NamedTuple):
    pool_address: ChecksumEvmAddress
    pool_name: str
    fee_address: ChecksumEvmAddress | None
    bribe_address: ChecksumEvmAddress | None
    gauge_address: ChecksumEvmAddress | None
    chain_id: Literal[ChainID.OPTIMISM, ChainID.BASE]


def save_velodrome_pool_to_cache(
        database: 'DBHandler',
        pool: VelodromePoolData,
) -> None:
    """
    Stores data about a velodrome pool and gauge in the global db cache tables.

    general_cache table:
    VELOP/AEROP -> {pool address}
    VELOG/AEROG -> {gauge address}
    """
    protocol_name = 'Velodrome' if pool.chain_id == ChainID.OPTIMISM else 'Aerodrome'
    addresbook_entries = [AddressbookEntry(
        address=pool.pool_address,
        name=f'{protocol_name} pool {pool.pool_name}',
        blockchain=pool.chain_id.to_blockchain(),
    )]
    if pool.gauge_address is not None:
        addresbook_entries.append(AddressbookEntry(
            address=pool.gauge_address,
            name=f'Gauge for {protocol_name} pool {pool.pool_name}',
            blockchain=pool.chain_id.to_blockchain(),
        ))

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        DBAddressbook(db_handler=database).add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=addresbook_entries,
        )

        if pool.chain_id == ChainID.OPTIMISM:
            pool_key = CacheType.VELODROME_POOL_ADDRESS
            gauge_key = CacheType.VELODROME_GAUGE_ADDRESS
            fee_key = CacheType.VELODROME_GAUGE_FEE_ADDRESS
            bribe_key = CacheType.VELODROME_GAUGE_BRIBE_ADDRESS
        else:
            pool_key = CacheType.AERODROME_POOL_ADDRESS
            gauge_key = CacheType.AERODROME_GAUGE_ADDRESS
            fee_key = CacheType.AERODROME_GAUGE_FEE_ADDRESS
            bribe_key = CacheType.AERODROME_GAUGE_BRIBE_ADDRESS

        tuples = [(pool_key.serialize(), pool.pool_address, (now_ts := ts_now()))]
        if pool.gauge_address is not None:
            tuples.append((gauge_key.serialize(), pool.gauge_address, now_ts))
        if pool.fee_address is not None:
            tuples.append((fee_key.serialize(), pool.fee_address, now_ts))
        if pool.bribe_address is not None:
            tuples.append((bribe_key.serialize(), pool.bribe_address, now_ts))

        write_cursor.executemany(
            'INSERT OR REPLACE INTO general_cache (key, value, last_queried_ts) VALUES (?, ?, ?)',
            tuples,
        )


def read_velodrome_like_pools_and_gauges_from_cache(
        cache_type_pool: Literal[CacheType.VELODROME_POOL_ADDRESS, CacheType.AERODROME_POOL_ADDRESS],  # noqa: E501
        cache_type_gauge: Literal[CacheType.VELODROME_GAUGE_ADDRESS, CacheType.AERODROME_GAUGE_ADDRESS],  # noqa: E501
) -> tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]:
    """
    Reads globaldb cache and returns:
    - A set of all known addresses of (velo/aero)drome pools.
    - A set of all known addresses of (velo/aero)drome gauges.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        str_pool_addresses = globaldb_get_general_cache_values(cursor=cursor, key_parts=(cache_type_pool,))  # noqa: E501
        pool_addresses = {string_to_evm_address(pool_address) for pool_address in str_pool_addresses}  # noqa: E501

        str_gauge_addresses = globaldb_get_general_cache_values(cursor=cursor, key_parts=(cache_type_gauge,))  # noqa: E501
        gauge_addresses = {string_to_evm_address(gauge_address) for gauge_address in str_gauge_addresses}  # noqa: E501

    return pool_addresses, gauge_addresses


def read_velodrome_pools_and_gauges_from_cache() -> tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]:  # noqa: E501
    """
    Reads globaldb cache and returns:
    - A set of all known addresses of velodrome pools.
    - A set of all known addresses of velodrome gauges.
    """
    return read_velodrome_like_pools_and_gauges_from_cache(
        cache_type_pool=CacheType.VELODROME_POOL_ADDRESS,
        cache_type_gauge=CacheType.VELODROME_GAUGE_ADDRESS,
    )


def read_aerodrome_pools_and_gauges_from_cache() -> tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]:  # noqa: E501
    """
    Reads globaldb cache and returns:
    - A set of all known addresses of aerodrome pools.
    - A set of all known addresses of aerodrome gauges.
    """
    return read_velodrome_like_pools_and_gauges_from_cache(
        cache_type_pool=CacheType.AERODROME_POOL_ADDRESS,
        cache_type_gauge=CacheType.AERODROME_GAUGE_ADDRESS,
    )


def query_velodrome_data_from_chain(
        inquirer: 'OptimismInquirer | BaseInquirer',
        existing_pools: set[str],
        msg_aggregator: 'MessagesAggregator',
        reload_all: bool,
) -> list[VelodromePoolData]:
    """
    Queries velodrome data from chain from the Velodrome Finance LP Sugar v3 contract.
    If new pools are found their tokens are created and the pools are returned.
    (Find more details for the contract here: https://github.com/velodrome-finance/sugar).

    Will only process up to POOL_DATA_MAX_QUERY (400) pools at a time. Queries pool data in
    chunks of POOL_DATA_CHUNK_SIZE (100) from the Sugar contract.

    - It only queries velodrome v2 & v3. Velodrome v1 data is "hardcoded" in the packaged db
    because they are not expected to change and there is no reason to make this method slower
    by querying v1 too.

    May raise:
    - RemoteError if there is an error connecting with the remote source of data
    """
    if inquirer.chain_id == ChainID.OPTIMISM:
        data_contract = EvmContract(
            address=VELODROME_LP_SUGAR_CONTRACT,
            abi=SUGAR_V3_CONTRACT_ABI,
        )
        counterparty = CPT_VELODROME
    else:
        data_contract = EvmContract(
            address=AERODROME_LP_SUGAR_CONTRACT,
            abi=SUGAR_V3_CONTRACT_ABI,
        )
        counterparty = CPT_AERODROME

    pool_data: list[dict] = []
    pool_data_chunk: list[dict] = []
    offset = initial_offset = 0 if reload_all else len(existing_pools)
    limit, last_notified_ts = POOL_DATA_CHUNK_SIZE, Timestamp(0)
    while len(pool_data_chunk) == limit or (len(pool_data_chunk) == 0 and offset == initial_offset):  # noqa: E501
        try:
            pool_data_chunk = data_contract.call(
                node_inquirer=inquirer,
                method_name='all',
                arguments=[limit, offset, 0],  # return all.
            )
        except RemoteError as e:
            log.warning(f'Failed to query {counterparty} pool data chunk due to {e!s}.')
            # If the total count of existing pools is a multiple of 100 it will try to query
            # a chunk for which there is no data, which results in a remote error here.
            # So break the loop since this indicates we have gotten all pools.
            break

        pool_data.extend(pool_data_chunk)
        offset += limit

        last_notified_ts = maybe_notify_new_pools_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=counterparty,
            chain=inquirer.chain_id,
            get_new_pools_count=lambda: len(pool_data),
        )

    deserialized_pools: list[VelodromePoolData] = []
    all_pools_length = len(pool_data)
    for idx, raw_pool in enumerate(pool_data):
        try:
            if (pool_address := deserialize_evm_address(raw_pool[0])) in existing_pools:
                continue  # This pool is already present in the cache

            gauge_address = deserialize_evm_address(raw_pool[13])
            fee_address = deserialize_evm_address(raw_pool[16])
            bribe_address = deserialize_evm_address(raw_pool[17])
            pool = VelodromePoolData(
                pool_address=pool_address,
                pool_name=raw_pool[1],
                fee_address=fee_address if fee_address != ZERO_ADDRESS else None,
                bribe_address=bribe_address if bribe_address != ZERO_ADDRESS else None,
                gauge_address=gauge_address if gauge_address != ZERO_ADDRESS else None,
                chain_id=inquirer.chain_id,  # type: ignore
            )
        except (DeserializationError, IndexError) as e:
            log.error(
                f'Skipping {counterparty} pool {raw_pool[0]}. Could not deserialize it while '
                f'decoding it. Additional information: {e}',
            )
            continue

        deserialized_pools.append(pool)
        save_velodrome_pool_to_cache(database=inquirer.database, pool=pool)
        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=counterparty,
            chain=inquirer.chain_id,
            processed=(processed := idx + 1),
            total=all_pools_length,
        )
        log.debug(
            f'Processed {counterparty} pool {processed}/{all_pools_length} {pool.pool_address} '
            f'on {inquirer.chain_name}.',
        )

    return deserialized_pools


def query_velodrome_like_data(
        inquirer: 'OptimismInquirer | BaseInquirer',
        cache_type: Literal[CacheType.VELODROME_POOL_ADDRESS, CacheType.AERODROME_POOL_ADDRESS],
        msg_aggregator: 'MessagesAggregator',
        reload_all: bool,
) -> list[VelodromePoolData] | None:
    """Queries velodrome pools and tokens."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        existing_pools = globaldb_get_general_cache_like(
            cursor=write_cursor,
            key_parts=(cache_type,),
        )
        globaldb_update_cache_last_ts(  # update the last_queried_ts of db entries
            write_cursor=write_cursor,
            cache_type=cache_type,
            key_parts=None,
        )

    return pools_data if len(pools_data := query_velodrome_data_from_chain(
        inquirer=inquirer,
        existing_pools=set(existing_pools),
        msg_aggregator=msg_aggregator,
        reload_all=reload_all,
    )) > 0 else None
