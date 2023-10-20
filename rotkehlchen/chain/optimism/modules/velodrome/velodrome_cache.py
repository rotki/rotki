import logging
from typing import TYPE_CHECKING, NamedTuple, Optional

from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.misc import InputError, NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_like,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    VELODROME_POOL_PROTOCOL,
    AddressbookEntry,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

VELODROME_SUGAR_V2_CONTRACT = string_to_evm_address('0x7F45F1eA57E9231f846B2b4f5F8138F94295A726')  # Velodrome Finance LP Sugar v2  # noqa: E501


class VelodromePoolData(NamedTuple):
    pool_address: ChecksumEvmAddress
    pool_name: str
    token0_address: ChecksumEvmAddress
    token1_address: ChecksumEvmAddress
    gauge_address: Optional[ChecksumEvmAddress]


def save_velodrome_data_to_cache(
        write_cursor: DBCursor,
        database: 'DBHandler',
        new_data: list[VelodromePoolData],
) -> None:
    """
    Stores data about velodrome pools and gauges in the global db cache tables.

    general_cache table:
    VELOP -> {pool address}
    VELOG -> {gauge address}
    """
    db_addressbook = DBAddressbook(db_handler=database)
    for pool in new_data:
        addresbook_entries = [AddressbookEntry(
            address=pool.pool_address,
            name=f'Velodrome pool {pool.pool_name}',
            blockchain=SupportedBlockchain.OPTIMISM,
        )]
        if pool.gauge_address is not None:
            addresbook_entries.append(AddressbookEntry(
                address=pool.gauge_address,
                name=f'Gauge for Velodrome pool {pool.pool_name}',
                blockchain=SupportedBlockchain.OPTIMISM,
            ))
        try:
            db_addressbook.add_addressbook_entries(
                write_cursor=write_cursor,
                entries=addresbook_entries,
            )
        except InputError as e:
            log.debug(
                f'Velodrome address book names for pool {pool.pool_address} were not added. '
                f'Probably names were added by the user earlier. {e}')

        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.VELODROME_POOL_ADDRESS,),
            values=[pool.pool_address],
        )
        if pool.gauge_address is not None:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.VELODROME_GAUGE_ADDRESS,),
                values=[pool.gauge_address],
            )


def read_velodrome_pools_and_gauges_from_cache() -> tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]:  # noqa: E501
    """
    Reads globaldb cache and returns:
    - A set of all known addresses of velodrome pools.
    - A set of all known addresses of velodrome gauges.
    """
    gauge_addresses = set()
    pool_addresses = set()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        str_pool_addresses = globaldb_get_general_cache_values(cursor=cursor, key_parts=(CacheType.VELODROME_POOL_ADDRESS,))  # noqa: E501
        for pool_address in str_pool_addresses:
            pool_addresses.add(string_to_evm_address(pool_address))

        str_gauge_addresses = globaldb_get_general_cache_values(cursor=cursor, key_parts=(CacheType.VELODROME_GAUGE_ADDRESS,))  # noqa: E501
        for gauge_address in str_gauge_addresses:
            gauge_addresses.add(string_to_evm_address(gauge_address))

    return pool_addresses, gauge_addresses


def query_velodrome_data_from_chain_and_maybe_create_tokens(
        inquirer: 'OptimismInquirer',
        existing_pools: list[ChecksumEvmAddress],
) -> Optional[list[VelodromePoolData]]:
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
    data_contract = inquirer.contracts.contract(VELODROME_SUGAR_V2_CONTRACT)
    pool_data = []
    offset = 0
    limit = 200
    pool_data_chunk: list[dict] = []
    while len(pool_data_chunk) == limit or (len(pool_data_chunk) == 0 and offset == 0):
        pool_data_chunk = data_contract.call(
            node_inquirer=inquirer,
            method_name='all',
            arguments=[limit, offset, ZERO_ADDRESS],  # the address argument here is needed by the design of this contract interface to cover other user cases its developers had in mind, but it isn't needed for this particular call in which we only want to get the pools. So we can just use any address.  # noqa: E501
        )
        pool_data.extend(pool_data_chunk)
        offset += limit

    deserialized_pools = []
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
            token0_address, token1_address = deserialize_evm_address(pool[5]), deserialize_evm_address(pool[8])  # noqa: E501
            gauge_address = deserialize_evm_address(pool[11])
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
            token0_address=token0_address,
            token1_address=token1_address,
            gauge_address=gauge_address if gauge_address != ZERO_ADDRESS else None,
        ))

    inquirer.get_multiple_erc20_contract_info(addresses)  # multicall for token info

    returned_pools = []
    for entry in deserialized_pools:
        for token in (entry.token0_address, entry.token1_address, entry.pool_address):  # create the tokens for the new pools. Keep in mind that the pool address is the address of the lp token received when depositing to the pool  # noqa: E501
            try:
                get_or_create_evm_token(
                    userdb=inquirer.database,
                    evm_address=token,
                    chain_id=ChainID.OPTIMISM,
                    evm_inquirer=inquirer,
                    encounter=TokenEncounterInfo(
                        description='Querying velodrome pools',
                        should_notify=False,
                    ),
                    protocol=VELODROME_POOL_PROTOCOL if token == pool_address else None,  # mark the lp tokens with the protocol to identify them for special treatment for price calculation  # noqa: E501
                )
            except NotERC20Conformant as e:
                log.error(
                    f'Skipping velodrome token {token} because it is not a valid ERC20 token. {e}',
                )
                break
        else:
            returned_pools.append(entry)

    return returned_pools


def query_velodrome_data(inquirer: 'OptimismInquirer') -> Optional[list[VelodromePoolData]]:
    """
    Queries velodrome pools and tokens.
    Returns a list of pool data if the query was successful.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = [
            string_to_evm_address(address)
            for address in globaldb_get_general_cache_like(cursor=cursor, key_parts=(CacheType.VELODROME_POOL_ADDRESS,))  # noqa: E501
        ]

    try:
        pools_data = query_velodrome_data_from_chain_and_maybe_create_tokens(
            inquirer=inquirer,
            existing_pools=existing_pools,
        )
    except RemoteError as err:
        log.error(f'Could not query chain for velodrome pools due to: {err}')
        pools_data = None

    return pools_data
