import logging
from typing import TYPE_CHECKING, NamedTuple, Optional

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenSeenAt, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.drivers.gevent import DBCursor
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
    globaldb_set_general_cache_values,
    read_curve_pool_tokens,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CURVE_POOL_PROTOCOL,
    AddressbookEntry,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    GeneralCacheType,
    SupportedBlockchain,
)
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CURVE_POOLS_MAPPING_TYPE = dict[
    ChecksumEvmAddress,  # lp token address
    tuple[
        ChecksumEvmAddress,  # pool address
        list[ChecksumEvmAddress],  # list of coins addresses
        Optional[list[ChecksumEvmAddress]],  # optional list of underlying coins addresses
    ],
]

READ_CURVE_DATA_TYPE = tuple[
    dict[ChecksumEvmAddress, list[ChecksumEvmAddress]],
    set[ChecksumEvmAddress],

]
# list of pools that we know contain bad tokens
IGNORED_CURVE_POOLS = {'0x066B6e1E93FA7dcd3F0Eb7f8baC7D5A747CE0BF9'}

CURVE_API_URLS = [
    'https://api.curve.fi/api/getPools/ethereum/main',
    'https://api.curve.fi/api/getPools/ethereum/crypto',
    'https://api.curve.fi/api/getPools/ethereum/factory',
    'https://api.curve.fi/api/getPools/ethereum/factory-crypto',
]


CURVE_METAREGISTRY_METHODS = [
    'get_pool_name',
    'get_gauge',
    'get_lp_token',
    'get_coins',
    'get_underlying_coins',
]


class CurvePoolData(NamedTuple):
    pool_address: ChecksumEvmAddress
    pool_name: str
    lp_token_address: ChecksumEvmAddress
    gauge_address: Optional[ChecksumEvmAddress]
    coins: list[ChecksumEvmAddress]
    underlying_coins: Optional[list[ChecksumEvmAddress]]


def read_curve_pools_and_gauges() -> READ_CURVE_DATA_TYPE:
    """Reads globaldb cache and returns:
    - A set of all known curve pools addresses.
    - A set of all known curve gauges addresses.

    Doesn't raise anything unless cache entries were inserted incorrectly.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        curve_pools_lp_tokens = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        )
        curve_pools = {}
        curve_gauges = set()
        for lp_token_addr in curve_pools_lp_tokens:
            pool_address = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_addr],
            )[0]
            gauge_address_data = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, pool_address],
            )
            if len(gauge_address_data) > 0:
                curve_gauges.add(string_to_evm_address(gauge_address_data[0]))
            pool_address = string_to_evm_address(pool_address)
            curve_pools[pool_address] = read_curve_pool_tokens(cursor=cursor, pool_address=pool_address)  # noqa: E501

    return curve_pools, curve_gauges


def ensure_curve_tokens_existence(
        ethereum_inquirer: 'EthereumInquirer',
        all_pools: list[CurvePoolData],
) -> None:
    """This function receives data about curve pools and ensures that lp tokens and pool coins
    exist in rotki's database.

    Since is possible that a pool has an invalid token we keep a mapping of the valid ones
    and return it.

    May raise:
    - NotERC20Conformant if failed to query info while calling get_or_create_evm_token

    """
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
                        userdb=ethereum_inquirer.database,
                        evm_address=token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping pool {pool} because {token_address} is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue
        elif len(pool.coins) == len(pool.underlying_coins):
            # Coins and underlying coins lists represent a
            # mapping of coin -> underlying coin (each coin always has one underlying coin).
            for token_address, underlying_token_address in zip(pool.coins, pool.underlying_coins):
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                # ensure underlying token exists
                try:
                    get_or_create_evm_token(
                        userdb=ethereum_inquirer.database,
                        evm_address=underlying_token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping pool {pool} because {underlying_token_address} is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue

                try:
                    # and ensure token exists
                    get_or_create_evm_token(
                        userdb=ethereum_inquirer.database,
                        evm_address=token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        underlying_tokens=[UnderlyingToken(
                            address=underlying_token_address,
                            token_kind=EvmTokenKind.ERC20,
                            weight=ONE,
                        )],
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping pool {pool} because {token_address} is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue
        else:
            # Otherwise just ensure that coins and underlying coins exist in our assets database
            for token_address in pool.coins + pool.underlying_coins:
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                try:
                    get_or_create_evm_token(
                        userdb=ethereum_inquirer.database,
                        evm_address=token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.error(
                        f'Skipping coin {token_address} because it is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue

        # finally ensure lp token exists in the globaldb. Since is a token created by curve
        # it should always be an ERC20
        get_or_create_evm_token(
            userdb=ethereum_inquirer.database,
            evm_address=pool.lp_token_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            protocol=CURVE_POOL_PROTOCOL,
            seen=TokenSeenAt(description='Querying curve pools'),
        )


def save_curve_data_to_cache(
        write_cursor: DBCursor,
        database: 'DBHandler',
        new_pools: list[CurvePoolData],
) -> None:
    """Stores data received about curve pools and gauges in the cache"""
    db_addressbook = DBAddressbook(db_handler=database)
    for pool in new_pools:
        addresbook_entries = [AddressbookEntry(
            address=pool.pool_address,
            name=pool.pool_name,
            blockchain=SupportedBlockchain.ETHEREUM,
        )]
        if pool.gauge_address is not None:
            addresbook_entries.append(AddressbookEntry(
                address=pool.gauge_address,
                name=f'Curve gauge for {pool.pool_name}',
                blockchain=SupportedBlockchain.ETHEREUM,
            ))
        try:
            db_addressbook.add_addressbook_entries(
                write_cursor=write_cursor,
                entries=addresbook_entries,
            )
        except InputError as e:
            log.debug(
                f'Curve address book names for pool {pool.pool_address} were not added. '
                f'Probably names were added by the user earlier. {str(e)}')

        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
            values=[pool.lp_token_address],  # keys of pools_mapping are lp tokens
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, pool.lp_token_address],
            values=[pool.pool_address],
        )
        for idx, coin in enumerate(pool.coins):
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool.pool_address, str(idx)],
                values=[coin],
            )
        if pool.underlying_coins is not None:
            for idx, underlying_coin in enumerate(pool.underlying_coins):
                globaldb_set_general_cache_values(
                    write_cursor=write_cursor,
                    key_parts=[GeneralCacheType.CURVE_POOL_UNDERLYING_TOKENS, pool.pool_address, str(idx)],  # noqa: E501
                    values=[underlying_coin],
                )
        if pool.gauge_address is not None:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, pool.pool_address],
                values=[pool.gauge_address],
            )


def query_curve_data_from_api(existing_pools: list[ChecksumEvmAddress]) -> list[CurvePoolData]:
    """
    Query all curve information(lp tokens, pools, gagues, pool coins) from curve api.

    May raise:
    - RemoteError if failed to query curve api
    """
    all_api_pools = []
    for api_url in CURVE_API_URLS:
        response_json = request_get_dict(api_url)
        if response_json['success'] is False:
            raise RemoteError(f'Curve api endpoint {api_url} returned failure. Response: {response_json}')  # noqa: E501

        try:
            all_api_pools.extend(response_json['data']['poolData'])
        except KeyError as e:
            raise RemoteError(f'Curve api endpoint {api_url} response is missing {str(e)} key') from e  # noqa: E501

    processed_new_pools = []
    for api_pool_data in all_api_pools:
        try:
            pool_address = deserialize_evm_address(api_pool_data['address'])
            if pool_address in IGNORED_CURVE_POOLS or pool_address in existing_pools:
                continue

            coins = []
            for coin_data in api_pool_data['coins']:
                coins.append(deserialize_evm_address(coin_data['address']))
            underlying_coins = None
            if 'underlyingCoins' in api_pool_data:
                underlying_coins = []
                for underlying_coin_data in api_pool_data['underlyingCoins']:
                    underlying_coins.append(deserialize_evm_address(underlying_coin_data['address']))  # noqa: E501

            processed_new_pools.append(CurvePoolData(
                pool_address=pool_address,
                pool_name=api_pool_data['name'],
                lp_token_address=deserialize_evm_address(api_pool_data['lpTokenAddress']),
                gauge_address=deserialize_evm_address(api_pool_data['gaugeAddress']) if 'gaugeAddress' in api_pool_data else None,  # noqa: E501
                coins=coins,
                underlying_coins=underlying_coins,
            ))
        except KeyError as e:
            raise RemoteError(f'Curve pool data {api_pool_data} are missing key {str(e)}') from e
        except DeserializationError as e:
            log.error(
                f'Could not deserialize evm address while decoding curve pool {pool_address} '
                f'information from curve api: {str(e)}',
            )

    return processed_new_pools


def query_curve_data_from_chain(
        ethereum: 'EthereumInquirer',
        existing_pools: list[ChecksumEvmAddress],
) -> Optional[list[CurvePoolData]]:
    """
    Query all curve information(lp tokens, pools, gagues, pool coins) from metaregistry.

    May raise:
    - RemoteError if failed to query chain
    """
    address_provider = ethereum.contracts.contract(string_to_evm_address('0x0000000022D53366457F9d5E68Ec105046FC4383'))  # noqa: E501
    try:
        metaregistry_address = deserialize_evm_address(address_provider.call(
            node_inquirer=ethereum,
            method_name='get_address',
            arguments=[7],
        ))
    except DeserializationError as e:
        log.error(f'Curve address provider returned an invalid address for metaregistry. {str(e)}')
        return None

    metaregistry = EvmContract(
        address=metaregistry_address,
        abi=ethereum.contracts.abi('CURVE_METAREGISTRY'),  # type: ignore[call-overload]  # for some reason mypy doesn't properly see argument type  # noqa: E501
        deployed_block=0,  # deployment_block is not used and the contract is dynamic
    )
    pool_count = metaregistry.call(node_inquirer=ethereum, method_name='pool_count')
    new_pools = []
    for pool_index in range(pool_count):
        try:
            pool_address = deserialize_evm_address(metaregistry.call(
                node_inquirer=ethereum,
                method_name='pool_list',
                arguments=[pool_index],
            ))
        except DeserializationError as e:
            log.error(f'Could not deserialize curve pool address {pool_address}. {str(e)}')
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
        raw_pool_properties = ethereum.multicall_2(calls=calls, require_success=True)
        decoded_pool_properties = [
            metaregistry.decode(result=result[1], method_name=method_name, arguments=[pool_address])  # noqa: E501
            for result, method_name in zip(raw_pool_properties, CURVE_METAREGISTRY_METHODS)
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
                f'information from metaregistry: {str(e)}',
            )

    return new_pools


def query_curve_data(ethereum: 'EthereumInquirer') -> Optional[list[CurvePoolData]]:
    """Query curve lp tokens, curve pools and curve gauges.
    First tries to find data via curve api and if fails to do so, queries the chain (metaregistry).

    Returns list of pools if either api or chain query was successful, otherwise None.

    There is a known issue that curve api and metaregistry return different pool names. For example
    curve api returns "Curve.fi DAI/USDC/USDT" while metaregistry returns "3pool".
    TODO: think of how to make pool names uniform.

    May raise:
    - RemoteError if failed to query etherscan or node
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = [
            string_to_evm_address(address)
            for address in globaldb_get_general_cache_like(cursor=cursor, key_parts=[GeneralCacheType.CURVE_LP_TOKENS])  # noqa: E501
        ]
    pools_data = None
    try:
        pools_data = query_curve_data_from_api(existing_pools=existing_pools)
    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Could not query curve api due to: {str(e)}. Will query metaregistry on chain')
        try:
            pools_data = query_curve_data_from_chain(
                ethereum=ethereum,
                existing_pools=existing_pools,
            )
        except RemoteError as err:
            log.error(f'Could not query chain for curve pools due to: {str(err)}')

    return pools_data
