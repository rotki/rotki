import logging
from collections import defaultdict
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_STAKING,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
)
from rotkehlchen.constants import ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, TokenQueryFailed
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CacheType,
    ChainID,
    TokenKind,
    UniqueCacheType,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler

KONG_API: Final[str] = 'https://kong.yearn.fi/api/rest'


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _get_cache_args(chain_id: ChainID) -> tuple[UniqueCacheType, str]:
    return CacheType.YEARN_VAULTS, str(chain_id.serialize_for_db())


def _maybe_reset_yearn_cache_timestamp(count: int | None, chain_id: ChainID) -> bool:
    """Get the number of vaults processed in the last execution of this function.
    If it was the same number of vaults this response has then we don't need to take
    action since vaults are not removed from their API response.

    If count is None we force saving a new timestamp as it means an error happened

    It returns if we should stop updating (True) or not (False)
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        yearn_api_cache: str | None = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=_get_cache_args(chain_id),
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
                key_parts=_get_cache_args(chain_id),
                value=vaults_amount,
            )
        return True  # we should stop here

    return False  # will continue


def _query_yearn_vaults(chain_id: ChainID) -> list[dict[str, Any]]:
    """Query Yearn v2 and v3 vault metadata from Kong.

    Include hidden, retired and third-party vaults for historical transaction decoding.
    May raise RemoteError.
    """
    url = f'{KONG_API}/list/vaults/{chain_id.value}'
    try:
        response = requests.get(url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException as e:
        log.error(f'Request to {url} failed due to {e!s}')
        raise RemoteError('Failed to obtain yearn vault information') from e

    if response.status_code != HTTPStatus.OK:
        raise RemoteError(f'Failed to query Kong vaults: HTTP {response.status_code}')

    try:
        data = response.json()
    except (DeserializationError, JSONDecodeError) as e:
        log.error('Failed to deserialize Kong response as JSON due to %s', e)
        raise RemoteError('Failed to deserialize data from Kong') from e

    if not isinstance(data, list) or any(not isinstance(vault, dict) for vault in data):
        raise RemoteError('Unexpected format from Kong vault list response')

    return data


def query_yearn_vaults(db: DBHandler, ethereum_inquirer: EvmNodeInquirer) -> None:
    """Query yearn API and ensure that all the tokens exist locally. If they exist but the protocol
    is not the correct one, then the asset will be edited.

    May raise:
    - RemoteError
    """
    chain_id = ethereum_inquirer.chain_id
    try:
        data = _query_yearn_vaults(chain_id=chain_id)
        if _maybe_reset_yearn_cache_timestamp(count=len(data), chain_id=chain_id):
            return  # no new vaults
    except RemoteError as e:
        log.error(
            f'Failed to query yearn vaults on {chain_id} due to {e}. '
            'Resetting yearn cache ts',
        )
        _maybe_reset_yearn_cache_timestamp(count=None, chain_id=chain_id)  # reset timestamp to prevent repeated errors  # noqa: E501
        raise

    tokens_to_update_by_protocol = defaultdict(list)

    for vault in data:
        if (version := vault.get('apiVersion')) is None:  # Kong also lists non-yearn ERC4626 vaults (sDAI, Fluid, Morpho...) without an apiVersion  # noqa: E501
            log.debug('Skipping Kong vault %s without apiVersion', vault.get('address'))
            continue

        if version.startswith('0.'):  # v2 vault API versions use 0.x.x
            vault_type = CPT_YEARN_V2
        elif version.startswith(('3.', '~3.')):  # '~' indicates it has basically the same functionality as a yearn vault but is not deployed by yearn  # noqa: E501
            vault_type = CPT_YEARN_V3
        else:
            log.error(f'Found yearn token with unknown version {vault}. Skipping...')
            continue

        if not isinstance(asset := vault.get('asset'), dict):  # Kong has not indexed the underlying asset yet  # noqa: E501
            log.info('Skipping yearn %s vault %s without underlying asset', vault_type, vault.get('address'))  # noqa: E501
            continue

        encounter = TokenEncounterInfo(
            description=f'Querying {vault_type} balances',
            should_notify=False,
        )
        try:
            underlying_token = get_or_create_evm_token(
                userdb=db,
                evm_address=deserialize_evm_address(asset['address']),
                chain_id=chain_id,
                decimals=asset['decimals'],
                name=asset['name'],
                symbol=asset['symbol'],
                encounter=encounter,
            )
            vault_token = get_or_create_evm_token(
                userdb=db,
                evm_address=deserialize_evm_address(vault['address']),
                chain_id=chain_id,
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
            if (staking := vault.get('staking')) is not None and not isinstance(staking, dict):
                raise DeserializationError(f'Unexpected staking metadata {staking}')

            if (staking_address := (staking or {}).get('address')) is not None:  # check if the vault has a staking contract where the user can deposit vault tokens. Shares are 1:1  # noqa: E501
                staking_token_address = deserialize_evm_address(staking_address)
                staking_underlying_tokens = [UnderlyingToken(
                    address=vault_token.evm_address,
                    token_kind=TokenKind.ERC20,
                    weight=ONE,
                )]
                try:
                    get_or_create_evm_token(
                        userdb=db,
                        evm_address=staking_token_address,
                        evm_inquirer=ethereum_inquirer,
                        chain_id=chain_id,
                        protocol=CPT_YEARN_STAKING,
                        underlying_tokens=staking_underlying_tokens,
                        fallback_name=f'Yearn staking {vault_token.name}',  # fallback in case for the vaults that aren't ERC20  # noqa: E501
                        fallback_symbol=f'YG-{vault_token.symbol}',
                        fallback_decimals=18,
                        encounter=encounter,
                    )
                except TokenQueryFailed as e:
                    # save it without querying, so it is known as a yearn staking token, with
                    # the identifier as name. That makes it a placeholder whose details are
                    # filled in by the token details retry task once the nodes respond.
                    log.warning('Could not query yearn staking token %s due to %s. Saving it without its details', staking_address, e)  # noqa: E501
                    get_or_create_evm_token(
                        userdb=db,
                        evm_address=staking_token_address,
                        chain_id=chain_id,
                        protocol=CPT_YEARN_STAKING,
                        underlying_tokens=staking_underlying_tokens,
                        decimals=vault_token.decimals,  # shares are 1:1 with the vault
                        encounter=encounter,
                    )

        except (KeyError, DeserializationError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(
                f'Failed to store token information for yearn {vault_type} vault due to '
                f'{msg}. Vault: {vault}. Skipping...',
            )
            continue

        # if it existed but the protocol is not correct edit it. Can happen if it was auto added
        # before this logic existed or executed.
        if vault_token.protocol != vault_type:
            tokens_to_update_by_protocol[vault_type].append(vault_token)

    for protocol, tokens in tokens_to_update_by_protocol.items():
        log.debug('Updating protocol for %s %s %s assets', len(tokens), chain_id.name, protocol)
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
            key_parts=_get_cache_args(chain_id),
            value=str(len(data)),
        )
