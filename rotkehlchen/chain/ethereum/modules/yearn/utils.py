import logging
from collections import defaultdict
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, overload

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_STAKING,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int
from rotkehlchen.types import (
    CacheType,
    ChainID,
    TokenKind,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

YDAEMON_API: Final[str] = 'https://ydaemon.yearn.fi/rotki'  # contains v2 and v3 vaults
YDAEMON_PAGE_SIZE: Final[int] = 200


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _maybe_reset_yearn_cache_timestamp(count: int | None) -> bool:
    """Get the number of vaults processed in the last execution of this function.
    If it was the same number of vaults this response has then we don't need to take
    action since vaults are not removed from their API response.

    If count is None we force saving a new timestamp as it means an error happened

    It returns if we should stop updating (True) or not (False)
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        yearn_api_cache: str | None = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    if count is None or (yearn_api_cache is not None and int(yearn_api_cache) == count):
        vaults_amount = yearn_api_cache if yearn_api_cache is not None else '0'
        log.debug(
            f'Previous query of yearn vaults returned {vaults_amount} vaults and last API '
            f'response had the same amount of vaults. Not processing the API response since '
            f'it is identical to what we have.',
        )
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # update the timestamp of the last time these vaults were queried
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=[CacheType.YEARN_VAULTS],
                value=vaults_amount,
            )
        return True  # we should stop here

    return False  # will continue


@overload
def _query_ydaemon(endpoint: Literal['count/vaults'], params: str) -> dict[str, int]:
    ...


@overload
def _query_ydaemon(endpoint: Literal['list/vaults'], params: str) -> list[dict[str, Any]]:
    ...


def _query_ydaemon(endpoint: str, params: str) -> list[dict[str, Any]] | dict[str, Any]:
    """Query the ydaemon api.
    Returns the response from the api in a list or dict.

    May raise:
    - RemoteError
    """
    timeout_tuple = CachedSettings().get_timeout_tuple()
    url = f'{YDAEMON_API}/{endpoint}?{params}'
    try:
        response = requests.get(url, timeout=timeout_tuple)
    except requests.exceptions.RequestException as e:
        log.error(f'Request to {url} failed due to {e!s}')
        raise RemoteError('Failed to obtain yearn vault information') from e

    if response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE):
        raise RemoteError('Failed to obtain a proper response from the yearn API')

    try:
        data = response.json()
    except (DeserializationError, JSONDecodeError) as e:
        log.error(f'Failed to deserialize yearn api response {response.text} as JSON due to {e!s}')
        raise RemoteError('Failed to deserialize data from the yearn api') from e

    return data


def _query_yearn_vaults() -> list[dict[str, Any]]:
    """Query list of yearn v2 and v3 vaults from the ydaemon api.
    Returns the list of vaults.

    At the moment this logic queries only ethereum vaults.
    May raise:
        - RemoteError
    """
    all_vaults, offset = [], 0
    while True:
        data = _query_ydaemon(
            endpoint='list/vaults',
            params=f'chainIDs=1&limit={YDAEMON_PAGE_SIZE}&skip={offset}',
        )
        all_vaults.extend(data)
        offset += YDAEMON_PAGE_SIZE
        if len(data) < YDAEMON_PAGE_SIZE:
            break  # No more vaults to retrieve

    return all_vaults


def _query_yearn_vault_count() -> int:
    """Query count of yearn v2 and v3 vaults from the ydaemon api.
    Returns total vault count.

    May raise:
    - RemoteError
    """
    data = _query_ydaemon(endpoint='count/vaults', params='chainIDs=1')
    if 'numberOfVaults' not in data:
        msg = 'Unexpected format from yearn vault count response.'
        log.error(f'{msg} Expected a dict containing numberOfVaults integer, got {data}')
        raise RemoteError(msg)

    try:
        return deserialize_int(data['numberOfVaults'])
    except DeserializationError as e:
        log.error(f'Yearn number of vaults is not an integer {data}')
        raise RemoteError(
            'Yearn number of vaults is not an integer. Check logs for more details',
        ) from e


def query_yearn_vaults(db: 'DBHandler', ethereum_inquirer: 'EthereumInquirer') -> None:
    """Query yearn API and ensure that all the tokens exist locally. If they exist but the protocol
    is not the correct one, then the asset will be edited.

    May raise:
    - RemoteError
    """
    try:
        count = _query_yearn_vault_count()
        if _maybe_reset_yearn_cache_timestamp(count=count):
            return  # no new vaults

        data = _query_yearn_vaults()
    except RemoteError as e:
        log.error(f'Failed to query yearn vaults due to {e}. Resetting yearn cache ts')
        _maybe_reset_yearn_cache_timestamp(count=None)  # reset timestamp to prevent repeated errors  # noqa: E501
        raise

    if (vault_count := len(data)) != count:
        log.error(
            'Queried amount of yearn vaults does not match expected number. '
            f'Expected {count} vaults, got {vault_count}. {data}',
        )

    assert data is not None, 'data exists. Checked by _maybe_reset_yearn_cache_timestamp'
    tokens_to_update_by_protocol = defaultdict(list)

    for vault in data:
        if (version := vault.get('version')) is None:
            log.error(f'Could not identify the yearn vault type for {vault}. Skipping...')
            continue

        if version.startswith('0.'):  # version '0.x.x' happens in ydaemon and is always a v2 vault
            vault_type = CPT_YEARN_V2
        elif version.startswith(('3.', '~3.')):  # '~' indicates it has basically the same functionality as a yearn vault but is not deployed by yearn  # noqa: E501
            vault_type = CPT_YEARN_V3
        else:
            log.error(f'Found yearn token with unknown version {vault}. Skipping...')
            continue

        encounter = TokenEncounterInfo(
            description=f'Querying {vault_type} balances',
            should_notify=False,
        )
        try:
            underlying_token = get_or_create_evm_token(
                userdb=db,
                evm_address=string_to_evm_address(vault['token']['address']),
                chain_id=ChainID.ETHEREUM,
                decimals=vault['token']['decimals'],
                name=vault['token']['name'],
                symbol=vault['token']['symbol'],
                encounter=encounter,
            )
            vault_token = get_or_create_evm_token(
                userdb=db,
                evm_address=string_to_evm_address(vault['address']),
                chain_id=ChainID.ETHEREUM,
                protocol=vault_type,
                decimals=vault['decimals'],
                name=vault['name'],
                symbol=vault['symbol'],
                underlying_tokens=[UnderlyingToken(
                    address=underlying_token.evm_address,
                    token_kind=TokenKind.ERC20,
                    weight=ONE,
                )],
                encounter=encounter,
            )
            if (staking_address := vault.get('staking')) is not None:  # check if the vault has a staking contract where the user can deposit vault tokens. Shares are 1:1  # noqa: E501
                get_or_create_evm_token(
                    userdb=db,
                    evm_address=staking_address,
                    evm_inquirer=ethereum_inquirer,
                    chain_id=ChainID.ETHEREUM,
                    protocol=CPT_YEARN_STAKING,
                    underlying_tokens=[UnderlyingToken(
                        address=vault_token.evm_address,
                        token_kind=TokenKind.ERC20,
                        weight=ONE,
                    )],
                    fallback_name=f'Yearn staking {vault_token.name}',  # fallback in case for the vaults that aren't ERC20  # noqa: E501
                    fallback_symbol=f'YG-{vault_token.symbol}',
                    fallback_decimals=18,
                    encounter=encounter,
                )

        except KeyError as e:
            log.error(
                f'Failed to store token information for yearn {vault_type} vault due to '
                f'missing key {e!s}. Vault: {vault}. Skipping...',
            )
            continue

        # if it existed but the protocol is not correct edit it. Can happen if it was auto added
        # before this logic existed or executed.
        if vault_token.protocol != vault_type:
            tokens_to_update_by_protocol[vault_type].append(vault_token)

    for protocol, tokens in tokens_to_update_by_protocol.items():
        log.debug(f'Updating protocol for {len(tokens)} ethereum {protocol} assets')
        GlobalDBHandler.set_tokens_protocol_if_missing(
            tokens=tokens,
            new_protocol=protocol,
        )

    # Store in the globaldb cache the number of vaults processed from this call to the API
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # overwrites the old value cached and store in the cache the amount of vaults
        # processed in this response.

        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
            value=str(len(data)),
        )
