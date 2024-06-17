import logging
from typing import TYPE_CHECKING, Literal, NamedTuple

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CURVE_ADDRESS_PROVIDER,
    CURVE_API_URL,
    CURVE_CHAIN_ID,
    CURVE_METAREGISTRY_METHODS,
    IGNORED_CURVE_POOLS,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.errors.misc import (
    InputError,
    NotERC20Conformant,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_like,
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_value,
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
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
)
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from gevent import DBCursor
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurvePoolData(NamedTuple):
    pool_address: ChecksumEvmAddress
    pool_name: str
    lp_token_address: ChecksumEvmAddress
    gauge_address: ChecksumEvmAddress | None
    coins: list[ChecksumEvmAddress]
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


def _ensure_curve_tokens_existence(
        evm_inquirer: 'EvmNodeInquirer',
        all_pools: list[CurvePoolData],
) -> list[CurvePoolData]:
    """This function receives data about curve pools and ensures that lp tokens and pool coins
    exist in rotki's database.

    Since is possible that a pool has an invalid token we keep a mapping of the valid ones
    and return it.
    """
    verified_pools = []
    for pool in all_pools:
        # Ensure pool coins exist in the globaldb.
        # We have to create underlying tokens only if pool utilizes them.
        if pool.underlying_coins is None or pool.underlying_coins == pool.coins:
            # If underlying coins is None, it means that pool doesn't utilize them.
            # If underlying coins list is equal to coins then there are no underlying coins as well.  # noqa: E501
            for token_address in pool.coins:
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                # ensure token exists
                try:
                    get_or_create_evm_token(
                        userdb=evm_inquirer.database,
                        evm_address=token_address,
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                        encounter=TokenEncounterInfo(
                            description='Querying curve pools',
                            should_notify=False,
                        ),
                    )
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
                    continue
                # ensure underlying token exists
                try:
                    get_or_create_evm_token(
                        userdb=evm_inquirer.database,
                        evm_address=underlying_token_address,
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                        encounter=TokenEncounterInfo(
                            description='Querying curve pools',
                            should_notify=False,
                        ),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping pool {pool} because {underlying_token_address} is not a '
                        f'valid ERC20 token. {e}',
                    )
                    continue

                try:
                    # and ensure token exists
                    get_or_create_evm_token(
                        userdb=evm_inquirer.database,
                        evm_address=token_address,
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                        underlying_tokens=[UnderlyingToken(
                            address=underlying_token_address,
                            token_kind=EvmTokenKind.ERC20,
                            weight=ONE,
                        )],
                        encounter=TokenEncounterInfo(
                            description='Querying curve pools',
                            should_notify=False,
                        ),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping pool {pool} because {token_address} is not a '
                        f'valid ERC20 token. {e}',
                    )
                    continue
        else:
            # Otherwise just ensure that coins and underlying coins exist in our assets database  # noqa: E501
            for token_address in pool.coins + pool.underlying_coins:
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                try:
                    get_or_create_evm_token(
                        userdb=evm_inquirer.database,
                        evm_address=token_address,
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                        encounter=TokenEncounterInfo(
                            description='Querying curve pools',
                            should_notify=False,
                        ),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping coin {token_address} because it is not a '
                        f'valid ERC20 token. {e}',
                    )
                    continue

        # finally ensure lp token and gauge token exists in the globaldb. Since they are created
        # by curve, they should always be an ERC20
        try:
            get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_address=pool.lp_token_address,
                chain_id=evm_inquirer.chain_id,
                evm_inquirer=evm_inquirer,
                protocol=CURVE_POOL_PROTOCOL,
                encounter=TokenEncounterInfo(
                    description='Querying curve pools',
                    should_notify=False,
                ),
            )
        except NotERC20Conformant as e:
            log.error(  # should only fail if the node is not up to date
                f'Failed to check integrity of the curve pool {pool.lp_token_address} '
                f'due to {e}. Skipping',
            )
            continue

        if pool.gauge_address is not None:
            try:
                get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=pool.gauge_address,
                    chain_id=evm_inquirer.chain_id,
                    evm_inquirer=evm_inquirer,
                    encounter=TokenEncounterInfo(
                        description='Querying curve gauges',
                        should_notify=False,
                    ),
                    underlying_tokens=[UnderlyingToken(
                        address=pool.lp_token_address,
                        token_kind=EvmTokenKind.ERC20,
                        weight=ONE,
                    )],
                )
            except NotERC20Conformant:
                log.warning(f'Curve gauge {pool.gauge_address} is not a valid ERC20 token.')

        verified_pools.append(pool)
    return verified_pools


def save_curve_data_to_cache(
        write_cursor: 'DBCursor',
        database: 'DBHandler',
        new_data: list[CurvePoolData],
        chain_id: ChainID,
) -> None:
    """Stores data received about curve pools and gauges in the cache"""
    db_addressbook = DBAddressbook(db_handler=database)
    chain_id_str = str(chain_id.serialize_for_db())
    for pool in new_data:
        addresbook_entries = [AddressbookEntry(
            address=pool.pool_address,
            name=pool.pool_name,
            blockchain=chain_id.to_blockchain(),
        )]
        if pool.gauge_address is not None:
            addresbook_entries.append(AddressbookEntry(
                address=pool.gauge_address,
                name=f'Curve gauge for {pool.pool_name}',
                blockchain=chain_id.to_blockchain(),
            ))
        try:
            db_addressbook.add_addressbook_entries(
                write_cursor=write_cursor,
                entries=addresbook_entries,
            )
        except InputError as e:
            log.debug(
                f'Curve address book names for pool {pool.pool_address} were not added. '
                f'Probably names were added by the user earlier. {e}')

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
                key_parts=(CacheType.CURVE_POOL_TOKENS, chain_id_str, pool.pool_address, str(idx)),
                values=[coin],
            )
        if pool.underlying_coins is not None:
            for idx, underlying_coin in enumerate(pool.underlying_coins):
                globaldb_set_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=(CacheType.CURVE_POOL_UNDERLYING_TOKENS, chain_id_str, pool.pool_address, str(idx)),  # noqa: E501
                    values=[underlying_coin],
                )
        if pool.gauge_address is not None:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.CURVE_GAUGE_ADDRESS, chain_id_str, pool.pool_address),
                value=pool.gauge_address,
            )


def _query_curve_data_from_api(
        chain_id: ChainID,
        existing_pools: list[ChecksumEvmAddress],
) -> list[CurvePoolData]:
    """
    Query all curve information(lp tokens, pools, gagues, pool coins) from curve api.

    May raise:
    - RemoteError if failed to query curve api
    """
    all_api_pools = []
    api_url = CURVE_API_URL.format(curve_blockchain_id=CURVE_CHAIN_ID[chain_id])
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
            if 'underlyingCoins' in api_pool_data:
                underlying_coins = [deserialize_evm_address(x['address']) for x in api_pool_data['underlyingCoins']]  # noqa: E501

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
        existing_pools: list[ChecksumEvmAddress],
) -> list[CurvePoolData] | None:
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
    except DeserializationError as e:
        log.error(f'Curve address provider returned an invalid address for metaregistry. {e}')
        return None

    metaregistry = EvmContract(
        address=metaregistry_address,
        abi=evm_inquirer.contracts.abi('CURVE_METAREGISTRY'),  # type: ignore[call-overload]  # for some reason mypy doesn't properly see argument type
        deployed_block=0,  # deployment_block is not used and the contract is dynamic
    )
    pool_count = metaregistry.call(node_inquirer=evm_inquirer, method_name='pool_count')
    new_pools = []
    for pool_index in range(pool_count):
        raw_address = metaregistry.call(
            node_inquirer=evm_inquirer,
            method_name='pool_list',
            arguments=[pool_index],
        )
        try:
            pool_address = deserialize_evm_address(raw_address)
        except DeserializationError as e:
            log.error(f'Could not deserialize curve pool address {raw_address}. {e}')
            continue

        if pool_address in IGNORED_CURVE_POOLS or pool_address in existing_pools:
            continue

        calls = [
            (
                metaregistry_address,
                metaregistry.encode(method_name=method_name, arguments=[pool_address]),
            )
            for method_name in CURVE_METAREGISTRY_METHODS
        ]
        raw_pool_properties = evm_inquirer.multicall_2(calls=calls, require_success=True)
        decoded_pool_properties = [
            metaregistry.decode(result=result[1], method_name=method_name, arguments=[pool_address])  # noqa: E501
            for result, method_name in zip(raw_pool_properties, CURVE_METAREGISTRY_METHODS, strict=True)  # length should be same due to the call # noqa: E501
        ]
        try:
            pool_name: str = decoded_pool_properties[0][0]
            gauge_address = deserialize_evm_address(decoded_pool_properties[1][0])
            lp_token_address = deserialize_evm_address(decoded_pool_properties[2][0])
            coins_raw = decoded_pool_properties[3][0]
            underlying_coins_raw = decoded_pool_properties[4][0]
            coins = []
            for raw_coin_address in coins_raw:
                if raw_coin_address == ZERO_ADDRESS:
                    break
                coins.append(deserialize_evm_address(raw_coin_address))
            underlying_coins = []
            for raw_underlying_coin_address in underlying_coins_raw:
                if raw_underlying_coin_address == ZERO_ADDRESS:
                    break
                underlying_coins.append(deserialize_evm_address(raw_underlying_coin_address))

            new_pools.append(CurvePoolData(
                pool_address=pool_address,
                pool_name=pool_name,
                lp_token_address=lp_token_address,
                gauge_address=gauge_address if gauge_address != ZERO_ADDRESS else None,
                coins=coins,
                underlying_coins=underlying_coins if len(underlying_coins) > 0 else None,
            ))
        except DeserializationError as e:
            log.error(
                f'Could not deserialize evm address while decoding curve pool {pool_address} '
                f'information from metaregistry: {e}',
            )

    return new_pools


def query_curve_data(
        inquirer: 'EvmNodeInquirer',
        cache_type: Literal[CacheType.CURVE_LP_TOKENS],
) -> list[CurvePoolData] | None:
    """Query curve lp tokens, curve pools and curve gauges.
    First tries to find data via curve api and if fails to do so, queries the chain (metaregistry).

    Returns list of pools if either api or chain query was successful, otherwise None.

    There is a known issue that curve api and metaregistry return different pool names. For example
    curve api returns "Curve.fi DAI/USDC/USDT" while metaregistry returns "3pool".
    TODO: think of how to make pool names uniform."""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = [
            string_to_evm_address(address)
            for address in globaldb_get_general_cache_like(
                cursor=cursor,
                key_parts=(cache_type, str(inquirer.chain_id.serialize_for_db())),
            )
        ]
    try:
        pools_data: list[CurvePoolData] | None = _query_curve_data_from_api(
            chain_id=inquirer.chain_id,
            existing_pools=existing_pools,
        )
    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Could not query curve api due to: {e}. Will query metaregistry on chain')
        try:
            pools_data = _query_curve_data_from_chain(
                evm_inquirer=inquirer,
                existing_pools=existing_pools,
            )
        except RemoteError as err:
            log.error(f'Could not query chain for curve pools due to: {err}')
            return None

    if pools_data is None:
        return None

    verified_pools = _ensure_curve_tokens_existence(
        evm_inquirer=inquirer,
        all_pools=pools_data,
    )
    return verified_pools


def get_lp_and_gauge_token_addresses(
        pool_address: 'ChecksumEvmAddress',
        chain_id: ChainID,
) -> set['ChecksumEvmAddress']:
    """Reads the db to get the lp and gauge token addresses for the given pool address"""
    addresses = set()
    chain_id_str = str(chain_id.serialize_for_db())
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
