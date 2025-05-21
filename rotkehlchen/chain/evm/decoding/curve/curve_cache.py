import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CPT_CURVE,
    CURVE_ADDRESS_PROVIDER,
    CURVE_API_URL,
    CURVE_CHAIN_ID,
    CURVE_METAREGISTRY_METHODS,
    IGNORED_CURVE_POOLS,
    MAX_ONCHAIN_POOLS_QUERY,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants import ONE
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.errors.misc import (
    NotERC20Conformant,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    compute_cache_key,
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_value,
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
    globaldb_update_cache_last_ts,
    read_curve_pool_tokens,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CURVE_POOL_PROTOCOL,
    AddressbookEntry,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    Timestamp,
)
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:

    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass
class CurvePoolData:
    pool_address: ChecksumEvmAddress
    pool_name: str | None
    lp_token_address: ChecksumEvmAddress
    gauge_address: ChecksumEvmAddress | None
    # Coins in the pool. Has the LP token of the base pool for metapools.
    coins: list[ChecksumEvmAddress]
    # All underlying coins in a meta-pool, including the coins from the base pool. None for non-metapools.  # noqa: E501
    underlying_coins: list[ChecksumEvmAddress] | None


def read_curve_pools_and_gauges(chain_id: ChainID) -> tuple[dict[ChecksumEvmAddress, list[ChecksumEvmAddress]], set[ChecksumEvmAddress]]:  # noqa: E501
    """Reads globaldb cache and returns:
    - A set of all known curve pools addresses for the given chain.
    - A set of all known curve gauges addresses for the given chain.

    Returned functions doesn't raise anything unless cache entries were inserted incorrectly.
    """
    chain_id_str = str(chain_id.serialize_for_db())
    with GlobalDBHandler().conn.read_ctx() as cursor:
        curve_pools_lp_tokens = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LP_TOKENS, chain_id_str),
        )
        curve_pools = {}
        curve_gauges = set()
        for lp_token_addr in curve_pools_lp_tokens:
            pool_address = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CURVE_POOL_ADDRESS, chain_id_str, lp_token_addr),
            )
            if pool_address is None:
                continue
            gauge_address_data = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CURVE_GAUGE_ADDRESS, chain_id_str, pool_address),
            )
            if gauge_address_data is not None:
                curve_gauges.add(string_to_evm_address(gauge_address_data))
            pool_address = string_to_evm_address(pool_address)
            curve_pools[pool_address] = read_curve_pool_tokens(
                cursor=cursor,
                pool_address=pool_address,
                chain_id=chain_id,
            )

    return curve_pools, curve_gauges


def _ensure_single_pool_curve_tokens_existence(
        evm_inquirer: 'EvmNodeInquirer',
        pool: CurvePoolData,
) -> CurvePoolData | None:
    encounter = TokenEncounterInfo(
        description=f'Querying curve pools for {evm_inquirer.chain_name}',
        should_notify=False,
    )
    # Ensure pool coins exist in the globaldb.
    # We have to create underlying tokens only if pool utilizes them.
    underlying_token_names = []
    if pool.underlying_coins is None:
        # If underlying coins is None, it means that pool doesn't utilize them.
        # If underlying coins list is equal to coins then there are no underlying coins as well.  # noqa: E501
        for token_address in pool.coins:
            if token_address == ETH_SPECIAL_ADDRESS:
                underlying_token_names.append('ETH')
                continue

            try:  # ensure token exists
                underlying_token_names.append(get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=token_address,
                    chain_id=evm_inquirer.chain_id,
                    evm_inquirer=evm_inquirer,
                    encounter=encounter,
                ).symbol)
            except NotERC20Conformant as e:
                log.error(
                    f'Skipping pool {pool} because {token_address} is not a '
                    f'valid ERC20 token. {e}',
                )
                continue

    elif len(pool.coins) == len(pool.underlying_coins):
        # Coins and underlying coins lists represent a
        # mapping of coin -> underlying coin (each coin always has one underlying coin).
        for token_address, underlying_token_address in zip(pool.coins, pool.underlying_coins, strict=True):  # noqa: E501
            if token_address == ETH_SPECIAL_ADDRESS:
                underlying_token_names.append('ETH')
                continue

            try:  # ensure underlying token exists
                get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=underlying_token_address,
                    chain_id=evm_inquirer.chain_id,
                    evm_inquirer=evm_inquirer,
                    encounter=encounter,
                )
            except NotERC20Conformant as e:
                log.error(
                    f'Skipping pool {pool} because {underlying_token_address} is not a '
                    f'valid ERC20 token. {e}',
                )
                continue

            if underlying_token_address == token_address:  # they are the same token. Stop here
                continue  # can happen for a pool to have token's underlying token as itself

            try:  # and ensure token exists
                underlying_token_names.append(get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=token_address,
                    chain_id=evm_inquirer.chain_id,
                    evm_inquirer=evm_inquirer,
                    underlying_tokens=[UnderlyingToken(
                        address=underlying_token_address,
                        token_kind=EvmTokenKind.ERC20,
                        weight=ONE,
                    )],
                    encounter=encounter,
                ).symbol)
            except NotERC20Conformant as e:
                log.error(
                    f'Skipping pool {pool} because {token_address} is not a '
                    f'valid ERC20 token. {e}',
                )
                continue

    else:  # Otherwise just ensure that coins and underlying coins exist in our assets database  # noqa: E501
        for token_address in set(pool.coins + pool.underlying_coins):
            if token_address == ETH_SPECIAL_ADDRESS:
                underlying_token_names.append('ETH')
                continue

            try:
                underlying_token_names.append(get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=token_address,
                    chain_id=evm_inquirer.chain_id,
                    evm_inquirer=evm_inquirer,
                    encounter=encounter,
                ).symbol)
            except NotERC20Conformant as e:
                log.error(
                    f'Skipping coin {token_address} because it is not a '
                    f'valid ERC20 token. {e}',
                )
                continue

    if pool.pool_name is None:
        pool.pool_name = '/'.join(underlying_token_names)

    # finally ensure lp token and gauge token exists in the globaldb. Since they are created
    # by curve, they should always be an ERC20
    try:
        pool_lp_token = get_or_create_evm_token(
            userdb=evm_inquirer.database,
            evm_address=pool.lp_token_address,
            chain_id=evm_inquirer.chain_id,
            evm_inquirer=evm_inquirer,
            protocol=CURVE_POOL_PROTOCOL,
            encounter=encounter,
        )
    except NotERC20Conformant as e:
        log.error(  # should only fail if the node is not up to date
            f'Failed to check integrity of the curve pool {pool.lp_token_address} '
            f'due to {e}. Skipping',
        )
        return None

    if pool.gauge_address is not None:
        try:
            # Old gauges don't have the name/symbol/decimals methods. They use 18 decimals but
            # the name and symbol differ and in the latest versions it is configurable. To be
            # in sync with the onchain name we use the contract values and only
            # if they are missing we resort to the fallback name and symbol.
            get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_address=pool.gauge_address,
                chain_id=evm_inquirer.chain_id,
                evm_inquirer=evm_inquirer,
                encounter=encounter,
                underlying_tokens=[UnderlyingToken(
                    address=pool.lp_token_address,
                    token_kind=EvmTokenKind.ERC20,
                    weight=ONE,
                )],
                fallback_decimals=18,  # all gauges have 18 decimals https://t.me/curvefi/654915  # noqa: E501
                fallback_name=f'{pool_lp_token.name} Gauge Deposit',
                fallback_symbol=f'{pool_lp_token.symbol}-gauge',
            )
        except NotERC20Conformant:
            log.warning(f'Curve gauge {pool.gauge_address} is not a valid ERC20 token.')

    return pool


def _ensure_curve_tokens_existence(
        evm_inquirer: 'EvmNodeInquirer',
        all_pools: list[CurvePoolData],
        msg_aggregator: 'MessagesAggregator',
) -> list[CurvePoolData]:
    """This function receives data about curve pools and ensures that lp tokens and pool coins
    exist in rotki's database.

    Since is possible that a pool has an invalid token we keep a mapping of the valid ones
    and return it.
    """
    verified_pools, last_notified_ts, all_pools_length = [], Timestamp(0), len(all_pools)

    for idx, pool in enumerate(all_pools):
        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_CURVE,
            chain=evm_inquirer.chain_id,
            processed=idx + 1,
            total=all_pools_length,
        )
        if (verified_pool := _ensure_single_pool_curve_tokens_existence(
            evm_inquirer=evm_inquirer,
            pool=pool,
        )) is not None:
            verified_pools.append(verified_pool)

    return verified_pools


def _save_curve_data_to_cache(
        evm_inquirer: 'EvmNodeInquirer',
        new_data: list[CurvePoolData],
) -> None:
    """Stores data received about curve pools and gauges in the cache"""
    db_addressbook = DBAddressbook(db_handler=evm_inquirer.database)
    chain_id_str = str(evm_inquirer.chain_id.serialize_for_db())
    for pool in new_data:
        addressbook_entries = []
        if pool.pool_name is not None:
            addressbook_entries = [AddressbookEntry(
                address=pool.pool_address,
                name=pool.pool_name,
                blockchain=evm_inquirer.blockchain,
            )]
            if pool.gauge_address is not None:
                addressbook_entries.append(AddressbookEntry(
                    address=pool.gauge_address,
                    name=f'Curve gauge for {pool.pool_name}',
                    blockchain=evm_inquirer.blockchain,
                ))
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            db_addressbook.add_or_update_addressbook_entries(
                write_cursor=write_cursor,
                entries=addressbook_entries,
            )
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.CURVE_LP_TOKENS, chain_id_str),
                values=[pool.lp_token_address],  # keys of pools_mapping are lp tokens
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.CURVE_POOL_ADDRESS, chain_id_str, pool.lp_token_address),
                value=pool.pool_address,
            )
            for idx, coin in enumerate(pool.coins):
                globaldb_set_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=(
                        CacheType.CURVE_POOL_TOKENS,
                        chain_id_str,
                        pool.pool_address,
                        str(idx),
                    ),
                    values=[coin],
                )
            if pool.gauge_address is not None:
                globaldb_set_unique_cache_value(
                    write_cursor=write_cursor,
                    key_parts=(CacheType.CURVE_GAUGE_ADDRESS, chain_id_str, pool.pool_address),
                    value=pool.gauge_address,
                )


def _query_curve_data_from_api(
        chain_id: ChainID,
        existing_pools: set[ChecksumEvmAddress],
) -> list[CurvePoolData]:
    """
    Query all curve information(lp tokens, pools, gauges, pool coins) from curve api.

    May raise:
    - RemoteError if failed to query curve api
    """
    all_api_pools, api_url = [], CURVE_API_URL.format(curve_blockchain_id=CURVE_CHAIN_ID[chain_id])
    log.debug(f'Querying curve api {api_url}')
    response_json = request_get_dict(api_url)
    if response_json['success'] is False:
        raise RemoteError(f'Curve api endpoint {api_url} returned failure. Response: {response_json}')  # noqa: E501

    try:
        all_api_pools.extend(response_json['data']['poolData'])
    except KeyError as e:
        raise RemoteError(f'Curve api endpoint {api_url} response is missing {e} key') from e

    processed_new_pools = []
    for api_pool_data in all_api_pools:
        try:
            pool_address = deserialize_evm_address(api_pool_data['address'])
            if pool_address in IGNORED_CURVE_POOLS or pool_address in existing_pools:
                continue

            coins = [deserialize_evm_address(x['address']) for x in api_pool_data['coins']]
            underlying_coins = None
            if (
                'underlyingCoins' in api_pool_data and
                (u_coins := [
                    deserialize_evm_address(x['address'])
                    for x in api_pool_data['underlyingCoins']
                ]) != coins
            ):
                underlying_coins = u_coins

            processed_new_pools.append(CurvePoolData(
                pool_address=pool_address,
                pool_name=api_pool_data['name'],
                lp_token_address=deserialize_evm_address(api_pool_data['lpTokenAddress']),
                gauge_address=deserialize_evm_address(api_pool_data['gaugeAddress']) if 'gaugeAddress' in api_pool_data else None,  # noqa: E501
                coins=coins,
                underlying_coins=underlying_coins,
            ))
        except KeyError as e:
            raise RemoteError(f'Curve pool data {api_pool_data} are missing key {e}') from e
        except DeserializationError as e:
            log.error(
                f'Could not deserialize evm address while decoding curve pool '
                f'{api_pool_data["address"]} information from curve api: {e}',
            )

    return processed_new_pools


def _query_curve_data_from_chain(
        evm_inquirer: 'EvmNodeInquirer',
        existing_pools: set[ChecksumEvmAddress],
        msg_aggregator: 'MessagesAggregator',
) -> None:
    """
    Query all curve information(lp tokens, pools, gagues, pool coins) from metaregistry.

    May raise:
    - RemoteError if failed to query chain
    """
    address_provider = evm_inquirer.contracts.contract(CURVE_ADDRESS_PROVIDER)
    try:
        metaregistry_address = deserialize_evm_address(address_provider.call(
            node_inquirer=evm_inquirer,
            method_name='get_address',
            arguments=[7],
        ))
    except (RemoteError, DeserializationError) as e:
        log.error(
            f'Failed to retrieve metaregistry address from the Curve '
            f'address provider on {evm_inquirer.chain_name} due to {e!s}',
        )
        return

    metaregistry = EvmContract(
        address=metaregistry_address,
        abi=evm_inquirer.contracts.abi('CURVE_METAREGISTRY'),  # type: ignore[call-overload]  # for some reason mypy doesn't properly see argument type
        deployed_block=0,  # deployment_block is not used and the contract is dynamic
    )
    try:
        pool_count = metaregistry.call(node_inquirer=evm_inquirer, method_name='pool_count')
    except RemoteError as e:
        log.error(
            'Failed to retrieve Curve pool count from the metaregistry '
            f'on {evm_inquirer.chain_name} due to {e!s}',
        )
        return

    if (existing_pool_count := len(existing_pools)) == pool_count:
        return
    if (new_pool_count := pool_count - existing_pool_count) > MAX_ONCHAIN_POOLS_QUERY:
        pool_count = existing_pool_count + MAX_ONCHAIN_POOLS_QUERY
        new_pool_count = MAX_ONCHAIN_POOLS_QUERY
        log.info(
            f'Tried to query {new_pool_count} {evm_inquirer.chain_name} Curve pools. '
            f'Too many pools to query onchain. Only querying {new_pool_count}.',
        )

    last_notified_ts = Timestamp(0)
    pools_to_skip = IGNORED_CURVE_POOLS | existing_pools
    for pool_index in range((start_idx := pool_count - new_pool_count), pool_count):
        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_CURVE,
            chain=evm_inquirer.chain_id,
            processed=(processed := pool_index - start_idx),
            total=new_pool_count,
        )

        try:
            if (pool_address := deserialize_evm_address(metaregistry.call(
                node_inquirer=evm_inquirer,
                method_name='pool_list',
                arguments=[pool_index],
            ))) in pools_to_skip:
                continue

            log.debug(
                f'Processing Curve pool {processed}/{new_pool_count} {pool_address} '
                f'on {evm_inquirer.chain_name}.',
            )
            raw_pool_properties = evm_inquirer.multicall_2(
                calls=[(
                    metaregistry_address,
                    metaregistry.encode(method_name=method_name, arguments=[pool_address]),
                ) for method_name in CURVE_METAREGISTRY_METHODS],
                require_success=False,
            )
        except (RemoteError, DeserializationError) as e:
            log.error(
                f'Failed to retrieve Curve pool address for index {pool_index} '
                f'from the metaregistry on {evm_inquirer.chain_name} due to {e!s}',
            )
            continue

        decoded_pool_properties: list[Any] = []
        for (success, result), method_name in zip(raw_pool_properties, CURVE_METAREGISTRY_METHODS, strict=True):  # length should be same due to the call  # noqa: E501
            if success is False:
                if method_name == 'get_pool_name':  # There are a number of pools (especially later ones) where the pool name query fails  # noqa: E501
                    decoded_pool_properties.append(None)  # Pool name will be constructed from the underlying tokens later instead  # noqa: E501
                    continue
                else:
                    break

            decoded_pool_properties.append(metaregistry.decode(
                result=result,
                method_name=method_name,
                arguments=[pool_address],
            )[0])

        if len(decoded_pool_properties) != len(CURVE_METAREGISTRY_METHODS):
            log.error(
                f'Failed to query properties of curve pool {pool_address} '
                f'on {evm_inquirer.chain_name}. Skipping.',
            )
            continue

        try:
            pool_name, gauge_address, lp_token_address, coins_raw, underlying_coins_raw = decoded_pool_properties  # noqa: E501
            gauge_address = deserialize_evm_address(gauge_address)
            lp_token_address = deserialize_evm_address(lp_token_address)
            coins = [deserialize_evm_address(x) for x in coins_raw if x != ZERO_ADDRESS]
            u_coins = [deserialize_evm_address(x) for x in underlying_coins_raw if x != ZERO_ADDRESS]  # noqa: E501
            underlying_coins = None if u_coins == coins or len(u_coins) == 0 else u_coins
        except DeserializationError as e:
            log.error(
                f'Could not deserialize evm address while decoding curve pool {pool_address} '
                f'information from metaregistry: {e}',
            )
            continue

        if (pool := _ensure_single_pool_curve_tokens_existence(
            evm_inquirer=evm_inquirer,
            pool=CurvePoolData(
                pool_address=pool_address,
                pool_name=pool_name,
                lp_token_address=lp_token_address,
                gauge_address=gauge_address if gauge_address != ZERO_ADDRESS else None,
                coins=coins,
                underlying_coins=underlying_coins,
            ),
        )) is not None:
            _save_curve_data_to_cache(evm_inquirer=evm_inquirer, new_data=[pool])


def query_curve_data(
        inquirer: 'EvmNodeInquirer',
        cache_type: Literal[CacheType.CURVE_LP_TOKENS],
        msg_aggregator: 'MessagesAggregator',
) -> list[CurvePoolData] | None:
    """Query curve lp tokens, curve pools and curve gauges and save them in the database.
    First tries to find data via curve api.

    Returns list of pools if api query was successful, otherwise None.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = {  # query the pools that we already have in the db
            string_to_evm_address(address[0])
            for address in cursor.execute(
                'SELECT value FROM unique_cache WHERE key LIKE ?',
                (compute_cache_key((
                    CacheType.CURVE_POOL_ADDRESS,
                    str(inquirer.chain_id.serialize_for_db()),
                    '0x%',  # Include the beginning `0x` of the address to avoid matching chain id 10 when using chain id 1  # noqa: E501
                )),),
            )
        }

    pools_data: list[CurvePoolData] = []
    try:
        pools_data = _query_curve_data_from_api(
            chain_id=inquirer.chain_id,
            existing_pools=existing_pools,
        )
    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Could not query curve api due to: {e}. Will query the metaregistry on chain')
        inquirer.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Query Curve pools from the onchain metaregistry',
            exception_is_error=False,
            method=_query_curve_data_from_chain,
            evm_inquirer=inquirer,
            existing_pools=existing_pools,
            msg_aggregator=msg_aggregator,
        )

    if len(pools_data) == 0:
        # if no new pools, update the last_queried_ts of db entries
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_update_cache_last_ts(
                write_cursor=write_cursor,
                cache_type=cache_type,
                key_parts=(str(inquirer.chain_id.serialize_for_db()),),
            )
        return None

    verified_pools = _ensure_curve_tokens_existence(
        evm_inquirer=inquirer,
        all_pools=pools_data,
        msg_aggregator=msg_aggregator,
    )
    _save_curve_data_to_cache(evm_inquirer=inquirer, new_data=verified_pools)
    return verified_pools


def get_lp_and_gauge_token_addresses(
        pool_address: 'ChecksumEvmAddress',
        chain_id: ChainID,
) -> set['ChecksumEvmAddress']:
    """Reads the db to get the lp and gauge token addresses for the given pool address"""
    addresses, chain_id_str = set(), str(chain_id.serialize_for_db())
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (key := cursor.execute(
            'SELECT key FROM unique_cache WHERE value = ?',
            (pool_address,),
        ).fetchone()) is not None:
            addresses.add(key[0][-42:])  # 42 is the length of the EVM address

            if (gauge_address := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CURVE_GAUGE_ADDRESS, chain_id_str, pool_address),
            )) is not None:
                addresses.add(gauge_address)

    return addresses
