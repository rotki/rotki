import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.gearbox.constants import (
    CHAIN_ID_TO_DATA_COMPRESSOR,
    CPT_GEARBOX,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.evm.utils import (
    maybe_notify_cache_query_status,
    maybe_notify_new_pools_status,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    InputError,
    NotERC20Conformant,
    RemoteError,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_keys_and_values_like,
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_value,
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, Timestamp, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class GearboxPoolData:
    """Represents the details of a Gearbox pool, including its address, name, farming token,
    LP tokens, chain ID, and the underlying token address.

    underlying_token can be None in the case where we read the pool data from the cache and the
    underlying token is not required.
    """
    pool_address: ChecksumEvmAddress
    pool_name: str
    farming_pool_token: str
    lp_tokens: set[str]
    underlying_token: ChecksumEvmAddress | None = None


def get_existing_pools(
        cursor: 'DBCursor',
        cache_type: Literal[CacheType.GEARBOX_POOL_ADDRESS],
        chain_id: ChainID,
) -> set[ChecksumEvmAddress]:
    """Returns all the gearbox pool rewards address stored in cache"""
    return {
        string_to_evm_address(address) for address in globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(cache_type, str(chain_id.serialize())),
        )
    }


def save_gearbox_data_to_cache(
        new_data: list[GearboxPoolData],
        chain_id: ChainID,
) -> None:
    """Stores data about gearbox pools and their names in the global db cache tables."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for pool in new_data:
            str_chain_id = str(chain_id.serialize())
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.GEARBOX_POOL_ADDRESS, str_chain_id),
                values=[pool.pool_address],
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.GEARBOX_POOL_NAME, pool.pool_address, str_chain_id),
                value=pool.pool_name,
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.GEARBOX_POOL_FARMING_TOKEN, pool.pool_address, str_chain_id),
                value=pool.farming_pool_token,
            )
            if pool.lp_tokens is not None:
                for idx, lp_token in enumerate(pool.lp_tokens):
                    globaldb_set_general_cache_values(
                        write_cursor=write_cursor,
                        key_parts=(CacheType.GEARBOX_POOL_LP_TOKENS, pool.pool_address, str_chain_id, str(idx)),  # noqa: E501
                        values=[lp_token],
                    )


def read_gearbox_data_from_cache(chain_id: ChainID | None) -> tuple[dict[ChecksumEvmAddress, Any]]:
    """Reads gearbox pools and names from global db cache tables."""
    if not chain_id:
        return ({},)

    pools: dict[ChecksumEvmAddress, Any] = {}
    with GlobalDBHandler().conn.read_ctx() as cursor:
        str_chain_id = str(chain_id.serialize())
        for pool_address in get_existing_pools(
            cursor=cursor,
            cache_type=CacheType.GEARBOX_POOL_ADDRESS,
            chain_id=chain_id,
        ):
            if (pool_name := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.GEARBOX_POOL_NAME, pool_address, str_chain_id),
            )) is None:
                continue
            if (farming_pool_token := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.GEARBOX_POOL_FARMING_TOKEN, pool_address, str_chain_id),
            )) is None:
                continue
            if len(token_lp_addresses := globaldb_get_general_cache_keys_and_values_like(
                cursor=cursor,
                key_parts=(CacheType.GEARBOX_POOL_LP_TOKENS, pool_address, str_chain_id),
            )) == ZERO:
                continue
            pools[pool_address] = GearboxPoolData(
                pool_address=pool_address,
                pool_name=pool_name,
                farming_pool_token=farming_pool_token,
                lp_tokens={addr[1] for addr in token_lp_addresses},  # just the token address
            )

    return (pools,)


def register_token(
        evm_inquirer: 'EvmNodeInquirer',
        token_address: str,
        pool: GearboxPoolData,
        encounter: TokenEncounterInfo,
) -> EvmToken:
    """Gets or creates a token in the database and returns the EvmToken object."""
    return get_or_create_evm_token(
        userdb=evm_inquirer.database,
        evm_address=string_to_evm_address(token_address),
        chain_id=evm_inquirer.chain_id,
        protocol=CPT_GEARBOX,
        evm_inquirer=evm_inquirer,
        underlying_tokens=(
            [UnderlyingToken(address=pool.underlying_token, token_kind=TokenKind.ERC20, weight=ONE)]  # noqa: E501
            if pool.underlying_token is not None else []
        ),
        encounter=encounter,
    )


def ensure_gearbox_tokens_existence(
        evm_inquirer: 'EvmNodeInquirer',
        all_pools: list[GearboxPoolData],
        msg_aggregator: 'MessagesAggregator',
) -> list[GearboxPoolData]:
    """This function receives data about gearbox pools and ensures that lp tokens and pool coins
    exist in rotki's database."""
    verified_pools, all_pools_length, last_notified_ts = [], len(all_pools), Timestamp(0)
    encounter = TokenEncounterInfo(
        description=f'Querying gearbox pools for {evm_inquirer.chain_id.to_name()}',
        should_notify=False,
    )
    for idx, pool in enumerate(all_pools):
        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_GEARBOX,
            chain=evm_inquirer.chain_id,
            processed=idx + 1,
            total=all_pools_length,
        )

        # Ensure pool coins and underlying tokens exist in the globaldb.
        if pool.underlying_token is not None:
            try:
                get_or_create_evm_token(
                    userdb=evm_inquirer.database,
                    evm_address=pool.underlying_token,
                    chain_id=evm_inquirer.chain_id,
                    evm_inquirer=evm_inquirer,
                    encounter=encounter,
                )
            except NotERC20Conformant as e:
                log.error(f'Skipping pool {pool} because {pool.underlying_token} is not a valid ERC20 token. {e}')  # noqa: E501
                continue

        # ensure the lp tokens exist in the db
        lp_tokens_from_db = set()
        for token_address in pool.lp_tokens:
            try:
                token = register_token(
                    evm_inquirer=evm_inquirer,
                    token_address=token_address,
                    pool=pool,
                    encounter=encounter,
                )
                lp_tokens_from_db.add(token.identifier)
            except NotERC20Conformant as e:
                log.error(
                    f'Skipping pool {pool} because {token_address} is not a '
                    f'valid ERC20 token. {e}',
                )
                continue

        # ensure the farm token exist in the db and get the identifier
        pool.farming_pool_token = register_token(
            evm_inquirer=evm_inquirer,
            token_address=pool.farming_pool_token,
            pool=pool,
            encounter=encounter,
        ).identifier
        pool.lp_tokens = lp_tokens_from_db
        verified_pools.append(pool)
    return verified_pools


def ensure_gearbox_lp_underlying_tokens(
        node_inquirer: 'EvmNodeInquirer',
        token_identifier: str,
        lp_contract: 'EvmContract',
) -> EvmToken | None:
    """Ensures that the underlying token of a Gearbox liquidity pool (LP) is stored in the global
    database. If the underlying token is not already saved, it queries the chain to retrieve
    and save it."""
    try:
        remote_underlying_token = lp_contract.call(node_inquirer, 'underlyingToken')
    except (RemoteError, BlockchainQueryError) as e:
        log.error(f'Failed to query underlyingToken method in {node_inquirer.chain_name} Gearbox pool {lp_contract.address}. {e!s}')  # noqa: E501
        return None

    try:
        underlying_token_address = deserialize_evm_address(remote_underlying_token)
    except DeserializationError:
        log.error(f'underlyingToken call of {node_inquirer.chain_name} {lp_contract.address} returned invalid address {remote_underlying_token}')  # noqa: E501
        return None

    try:  # make sure it's in the global DB
        underlying_token = get_or_create_evm_token(
            userdb=node_inquirer.database,
            evm_address=underlying_token_address,
            chain_id=node_inquirer.chain_id,
            encounter=TokenEncounterInfo(description='Detecting Gearbox pool underlying tokens'),
        )
    except NotERC20Conformant as e:
        log.error(f'Error fetching {node_inquirer.chain_name} token {underlying_token_address} while detecting underlying tokens of {lp_contract.address!s}: {e!s}')  # noqa: E501
        return None

    # store it in the DB, so next time no need to query chain
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        try:
            GlobalDBHandler._add_underlying_tokens(
                write_cursor=write_cursor,
                parent_token_identifier=token_identifier,
                underlying_tokens=[
                    UnderlyingToken(
                        address=underlying_token_address,
                        token_kind=TokenKind.ERC20,
                        weight=ONE,  # all gearbox vaults have single underlying
                    ),
                ],
                chain_id=node_inquirer.chain_id,
            )
        except InputError as e:
            log.error(f'Failed to add gearbox underlying token {underlying_token_address} for {token_identifier} due to: {e}')  # noqa: E501
            return None

    return underlying_token


def get_gearbox_pool_tokens(inquirer: 'EvmNodeInquirer', pool_data: list[str], underlying_token_address: ChecksumEvmAddress) -> set[ChecksumEvmAddress] | None:  # noqa: E501
    """Extracts lp and farming token from the pool data, excluding the underlying token address
    and the special ETH address."""
    try:
        return {
            deserialized_address
            for data in pool_data[23]  # ZapperInfo[] on ABI
            for address in data[1:]  # ignore contract address, only consider tokenIn and tokenOut
            if (deserialized_address := deserialize_evm_address(address)) not in {underlying_token_address, ETH_SPECIAL_ADDRESS}  # noqa: E501
        }
    except (DeserializationError, IndexError) as e:
        log.error(f'Could not deserialize gearbox pool tokens from {inquirer.chain_name} gearbox pool data with underlying as {underlying_token_address}: {e}')  # noqa: E501
        return None


def query_gearbox_data_from_chain(
        evm_inquirer: 'EvmNodeInquirer',
        existing_pools: set[ChecksumEvmAddress],
        msg_aggregator: 'MessagesAggregator',
) -> list[GearboxPoolData] | None:
    """
    Query all Gearbox information(lp tokens, pools, lp coins) from data compressor.

    May raise:
    - RemoteError if failed to query chain
    """
    pools_data = evm_inquirer.contracts.contract(
        CHAIN_ID_TO_DATA_COMPRESSOR[evm_inquirer.chain_id],
    ).call(node_inquirer=evm_inquirer, method_name='getPoolsV3List')
    new_pools: list[GearboxPoolData] = []
    last_notified_ts = Timestamp(0)
    for pool_data in pools_data:
        last_notified_ts = maybe_notify_new_pools_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_GEARBOX,
            chain=evm_inquirer.chain_id,
            get_new_pools_count=lambda: len(new_pools),
        )

        try:
            pool_address = deserialize_evm_address(pool_data[0])
        except DeserializationError:
            log.error(f'Could not deserialize evm address {pool_data[0]} while decoding gearbox pool information')  # noqa: E501
            continue

        if pool_address in existing_pools:
            continue

        try:
            pool_name: str = pool_data[4]
            underlying_token_address = deserialize_evm_address(pool_data[1])
        except (DeserializationError, IndexError) as e:
            log.error(f'Could not deserialize evm address while decoding gearbox pool {pool_address} information from data_compressor: {e}')  # noqa: E501
            continue

        if (gearbox_pool_tokens := get_gearbox_pool_tokens(evm_inquirer, pool_data, underlying_token_address)) is None:  # noqa: E501
            log.error(f'Could not get lp and farming tokens for gearbox pool {pool_address} on {evm_inquirer.chain_name}')  # noqa: E501
            continue

        calls = [
            (
                (_contract := EvmContract(
                    address=address,
                    abi=evm_inquirer.contracts.abi('GEARBOX_FARMING_POOL'),
                    deployed_block=0,  # is not used here
                )).address,
                _contract.encode(method_name='stakingToken'),
            )
            for address in gearbox_pool_tokens
        ]
        output = evm_inquirer.multicall_2(require_success=False, calls=calls)
        farming_pool_token = None
        lp_token_ids: set[str] = set()
        for token_address, (is_farming_pool, _), in zip(gearbox_pool_tokens, output, strict=True):
            if is_farming_pool:
                farming_pool_token = token_address
            else:
                lp_token_ids.add(token_address)

        if farming_pool_token is None:
            log.error(f'Gearbox pool {pool_address} on {evm_inquirer.chain_name} has no farming tokens. Expected 1')  # noqa: E501
            continue

        new_pools.append(GearboxPoolData(
            pool_address=pool_address,
            pool_name=pool_name,
            farming_pool_token=farming_pool_token,
            lp_tokens=lp_token_ids,
            underlying_token=underlying_token_address,
        ))
    return new_pools


def query_gearbox_data(
        inquirer: 'EvmNodeInquirer',
        cache_type: Literal[CacheType.GEARBOX_POOL_ADDRESS],
        msg_aggregator: 'MessagesAggregator',
        reload_all: bool,  # pylint: disable=unused-argument
) -> list[GearboxPoolData] | None:
    """
    Queries chain for all gearbox rewards pools and returns a list of the mappings not cached
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = get_existing_pools(
            cursor=cursor,
            cache_type=cache_type,
            chain_id=inquirer.chain_id,
        )

    try:
        if (pools_data := query_gearbox_data_from_chain(
            evm_inquirer=inquirer,
            existing_pools=existing_pools,
            msg_aggregator=msg_aggregator,
        )) is None:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                globaldb_update_cache_last_ts(  # update the last_queried_ts of db entries
                    write_cursor=write_cursor,
                    cache_type=cache_type,
                    key_parts=(str(inquirer.chain_id.serialize_for_db())),
                )

            return None
    except RemoteError as err:
        log.error(f'Could not query chain for {inquirer.chain_name} gearbox pools due to: {err}')
        return None

    verified_pools = ensure_gearbox_tokens_existence(
        evm_inquirer=inquirer,
        all_pools=pools_data,
        msg_aggregator=msg_aggregator,
    )

    save_gearbox_data_to_cache(
        new_data=verified_pools,
        chain_id=inquirer.chain_id,
    )
    return verified_pools
