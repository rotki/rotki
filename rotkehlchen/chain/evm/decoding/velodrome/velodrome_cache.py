import logging
from typing import TYPE_CHECKING, Literal, NamedTuple

from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.evm.utils import (
    maybe_notify_cache_query_status,
    maybe_notify_new_pools_status,
)
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_like,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    AERODROME_POOL_PROTOCOL,
    VELODROME_POOL_PROTOCOL,
    AddressbookEntry,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

VELODROME_SUGAR_V2_CONTRACT = string_to_evm_address('0xc734656F0112CA18cdcaD424ddd8949F3D4c1DdD')  # Velodrome Finance LP Sugar v3  # noqa: E501
AERODROME_SUGAR_V2_CONTRACT = string_to_evm_address('0xC301856B4262E49E9239ec8a2d0c754d5ae317c0')  # Aerodrome Finance LP Sugar v3  # noqa: E501


class VelodromePoolData(NamedTuple):
    pool_address: ChecksumEvmAddress
    pool_name: str
    pool_decimals: int
    tick_spacing: int
    token0_address: ChecksumEvmAddress
    token1_address: ChecksumEvmAddress
    fee_address: ChecksumEvmAddress | None
    bribe_address: ChecksumEvmAddress | None
    gauge_address: ChecksumEvmAddress | None
    chain_id: Literal[ChainID.OPTIMISM, ChainID.BASE]


def save_velodrome_data_to_cache(
        database: 'DBHandler',
        pools_data: list[VelodromePoolData],
) -> None:
    """
    Stores data about velodrome pools and gauges in the global db cache tables.

    general_cache table:
    VELOP/AEROP -> {pool address}
    VELOG/AEROG -> {gauge address}
    """
    db_addressbook = DBAddressbook(db_handler=database)
    globaldb = GlobalDBHandler()
    for pool in pools_data:
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

        with globaldb.conn.write_ctx() as write_cursor:
            db_addressbook.add_or_update_addressbook_entries(
                write_cursor=write_cursor,
                entries=addresbook_entries,
            )

            if pool.chain_id == ChainID.OPTIMISM:
                pool_key = (CacheType.VELODROME_POOL_ADDRESS,)
                gauge_key = (CacheType.VELODROME_GAUGE_ADDRESS,)
                fee_key = (CacheType.VELODROME_GAUGE_FEE_ADDRESS,)
                bribe_key = (CacheType.VELODROME_GAUGE_BRIBE_ADDRESS,)
            else:
                pool_key = (CacheType.AERODROME_POOL_ADDRESS,)
                gauge_key = (CacheType.AERODROME_GAUGE_ADDRESS,)
                fee_key = (CacheType.AERODROME_GAUGE_FEE_ADDRESS,)
                bribe_key = (CacheType.AERODROME_GAUGE_BRIBE_ADDRESS,)

            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=pool_key,  # type: ignore
                values=[pool.pool_address],
            )
            if pool.gauge_address is not None:
                globaldb_set_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=gauge_key,  # type: ignore
                    values=[pool.gauge_address],
                )
            if pool.fee_address is not None:
                globaldb_set_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=fee_key,  # type: ignore
                    values=[pool.fee_address],
                )
            if pool.bribe_address is not None:
                globaldb_set_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=bribe_key,  # type: ignore
                    values=[pool.bribe_address],
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


def query_velodrome_data_from_chain_and_maybe_create_tokens(
        inquirer: 'OptimismInquirer | BaseInquirer',
        existing_pools: list[ChecksumEvmAddress],
        msg_aggregator: 'MessagesAggregator',
) -> list[VelodromePoolData]:
    """
    Queries velodrome data from chain from the Velodrome Finance LP Sugar v2 contract.
    If new pools are found their tokens are created and the pools are returned.
    (Find more details for the contract here: https://github.com/velodrome-finance/sugar).

    - It only queries velodrome v2. Velodrome v1 data is "hardcoded" in the packaged db
    because they are not expected to change and there is no reason to make this method slower
    by querying v1 too.

    May raise:
    - RemoteError if there is an error connecting with the remote source of data
    """
    if inquirer.chain_id == ChainID.OPTIMISM:
        data_contract = inquirer.contracts.contract(VELODROME_SUGAR_V2_CONTRACT)
        protocol = VELODROME_POOL_PROTOCOL
        counterparty = CPT_VELODROME
    else:
        data_contract = inquirer.contracts.contract(AERODROME_SUGAR_V2_CONTRACT)
        protocol = AERODROME_POOL_PROTOCOL
        counterparty = CPT_AERODROME

    pool_data: list[dict] = []
    pool_data_chunk: list[dict] = []
    offset, limit, last_notified_ts = 0, 100, Timestamp(0)
    while len(pool_data_chunk) == limit or (len(pool_data_chunk) == 0 and offset == 0):
        try:
            pool_data_chunk = data_contract.call(
                node_inquirer=inquirer,
                method_name='all',
                arguments=[limit, offset],
            )
        except RemoteError as e:
            log.warning(f'Failed to query velodrome pool data chunk due to {e!s}.')
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
    # first gather all pool data, and prepare a multicall for token information
    addresses = []
    for pool in pool_data:
        try:
            pool_address = deserialize_evm_address(pool[0])
        except DeserializationError as e:
            log.error(
                f'Skipping velodrome pool {pool[0]}. Could not deserialize it while '
                f'decoding it. Additional information: {e}',
            )
            continue

        if pool_address in existing_pools:
            continue

        try:
            token0_address, token1_address = deserialize_evm_address(pool[7]), deserialize_evm_address(pool[10])  # noqa: E501
            gauge_address = deserialize_evm_address(pool[13])
            fee_address = deserialize_evm_address(pool[16])
            bribe_address = deserialize_evm_address(pool[17])
        except DeserializationError as e:
            log.error(
                f'Skipping velodrome pool {pool[0]}. Could not deserialize an evm address while '
                f'decoding it. Additional information: {e}',
            )
            continue

        addresses.extend([pool_address, token0_address, token1_address])
        deserialized_pools.append(VelodromePoolData(
            pool_address=pool_address,
            pool_name=pool[1],
            pool_decimals=pool[2],
            tick_spacing=pool[4],
            token0_address=token0_address,
            token1_address=token1_address,
            fee_address=fee_address if fee_address != ZERO_ADDRESS else None,
            bribe_address=bribe_address if bribe_address != ZERO_ADDRESS else None,
            gauge_address=gauge_address if gauge_address != ZERO_ADDRESS else None,
            chain_id=inquirer.chain_id,  # type: ignore
        ))

    inquirer.get_multiple_erc20_contract_info(addresses)  # multicall for token info

    returned_pools = []
    encounter = TokenEncounterInfo(
        description=f'Querying velodrome pools for {inquirer.chain_name}',
        should_notify=False,
    )
    all_pools_length = len(deserialized_pools)
    for idx, entry in enumerate(deserialized_pools):
        try:
            token0, token1 = (
                get_or_create_evm_token(
                    userdb=inquirer.database,
                    evm_address=token,
                    chain_id=inquirer.chain_id,
                    evm_inquirer=inquirer,
                    encounter=encounter,
                )  # create the tokens for the new pools. Keep in mind that the pool address is the address of the lp token received when depositing to the pool  # noqa: E501
                for token in (entry.token0_address, entry.token1_address)
            )
        except NotERC20Conformant as e:
            log.error(
                f'Skipping velodrome pool {entry.pool_address} '
                f'because its tokens are not valid ERC20 tokens. {e}',
            )
            continue

        pool_name = f'CL{entry.tick_spacing}-{token0.symbol}/{token1.symbol}' if entry.pool_name == '' else entry.pool_name  # noqa: E501
        get_or_create_evm_token(  # this will not raise NotERC20Conformant because we give fallback info  # noqa: E501
            userdb=inquirer.database,
            evm_address=entry.pool_address,
            chain_id=inquirer.chain_id,
            evm_inquirer=inquirer,
            encounter=encounter,
            protocol=protocol,  # mark the lp tokens with the protocol to identify them for special treatment for price calculation  # noqa: E501
            fallback_decimals=entry.pool_decimals,
            fallback_name=f'{pool_name} Pool',
            fallback_symbol=pool_name,
        )
        returned_pools.append(entry)
        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=counterparty,
            chain=inquirer.chain_id,
            processed=idx + 1,
            total=all_pools_length,
        )

    return returned_pools


def query_velodrome_like_data(
        inquirer: 'OptimismInquirer | BaseInquirer',
        cache_type: Literal[CacheType.VELODROME_POOL_ADDRESS, CacheType.AERODROME_POOL_ADDRESS],
        msg_aggregator: 'MessagesAggregator',
) -> list[VelodromePoolData] | None:
    """
    Queries velodrome pools and tokens.
    Returns a list of pool data if the query was successful.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = [
            string_to_evm_address(address)
            for address in globaldb_get_general_cache_like(cursor=cursor, key_parts=(cache_type,))
        ]

    try:
        pools_data = query_velodrome_data_from_chain_and_maybe_create_tokens(
            inquirer=inquirer,
            existing_pools=existing_pools,
            msg_aggregator=msg_aggregator,
        )
    except RemoteError as err:
        log.error(f'Could not query chain for velodrome pools due to: {err}')
        pools_data = []

    if len(pools_data) != 0:
        save_velodrome_data_to_cache(
            database=inquirer.database,
            pools_data=pools_data,
        )

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_update_cache_last_ts(  # update the last_queried_ts of db entries
            write_cursor=write_cursor,
            cache_type=cache_type,
            key_parts=None,
        )

    return pools_data
