import logging
from typing import Any, Final

from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID
from rotkehlchen.utils.network import request_get_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SUPERFLUID_TOKENLIST_URL: Final = 'https://raw.githubusercontent.com/superfluid-org/tokenlist/refs/heads/main/superfluid.extended.tokenlist.json'


def _get_token_list() -> tuple[str, list[dict[str, Any]]] | None:
    """Get the raw token list from Superfluid's tokenlist repo on GitHub.
    Returns its version and tokens in a tuple or None on error.
    """
    try:
        version_data = (data := request_get_dict(url=SUPERFLUID_TOKENLIST_URL))['version']
        return (
            f'{version_data["major"]}.{version_data["minor"]}.{version_data["patch"]}',
            data['tokens'],
        )
    except (RemoteError, UnableToDecryptRemoteData, KeyError) as e:
        log.error(f'Failed to get Superfluid token list from github due to: {e!s}')
        return None


def query_superfluid_tokens(chain_id: ChainID) -> None:
    """Query Superfluid super tokens and their underlying tokens from their token list on GitHub
    and cache their addresses in the global database.
    """
    chain_id_int = chain_id.serialize_for_db()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_version = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.SUPERFLUID_TOKEN_LIST_VERSION, str(chain_id_int)),
        )

    if (version_and_tokens := _get_token_list()) is None:
        return  # Error has already been logged in _get_token_list

    version, token_data_list = version_and_tokens
    if existing_version == version:
        return  # The remote token list hasn't been updated since we last queried.

    super_tokens = []
    for token_data in token_data_list:
        if (
            token_data.get('chainId') != chain_id_int or
            'supertoken' not in token_data.get('tags', [])
        ):
            continue  # skip tokens for other chains and underlying tokens

        if (
            (token_info := token_data.get('extensions', {}).get('superTokenInfo')) is None or
            (token_type := token_info.get('type')) is None
        ):
            log.error(f'Encountered a Superfluid super token missing expected data. Skipping. Token data: {token_data}')  # noqa: E501
            continue

        try:
            if token_type == 'Pure':
                continue  # Pure super tokens don't have an underlying asset with any need for deposit/withdrawal decoding etc.  # noqa: E501
            elif token_type == 'Native Asset':
                underlying_token = 'native'
            elif token_type == 'Wrapper':
                underlying_token = deserialize_evm_address(token_info['underlyingTokenAddress'])
            else:
                log.error(
                    f'Encountered a Superfluid super token with unknown type. '
                    f'Expected either "Native Asset" or "Wrapper", but got "{token_type}". '
                    f'Skipping. Token data: {token_data}',
                )
                continue

            super_token = deserialize_evm_address(token_data['address'])
        except (KeyError, DeserializationError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(
                f'Failed to load Superfluid underlying token address due to {msg}. Skipping. '
                f'Token data: {token_data}.',
            )
            continue

        super_tokens.append(f'{super_token},{underlying_token}')

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.SUPERFLUID_SUPER_TOKENS, str(chain_id_int)),
            values=super_tokens,
        )
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.SUPERFLUID_TOKEN_LIST_VERSION, str(chain_id_int)),
            value=version,
        )
