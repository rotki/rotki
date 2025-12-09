import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.superfluid.constants import CPT_SUPERFLUID
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, Timestamp
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

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


def query_superfluid_tokens(
        evm_inquirer: 'EvmNodeInquirer',
) -> None:
    """Query Superfluid super tokens and their underlying tokens from their token list on GitHub
    and add them to the global database.
    """
    chain_id_int = evm_inquirer.chain_id.serialize_for_db()
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

    super_tokens_data, underlying_tokens_data = [], {}
    for token_data in token_data_list:
        if token_data.get('chainId') != chain_id_int:
            continue

        if 'underlying' in (tags := token_data.get('tags', [])):
            underlying_tokens_data[token_data.get('address')] = token_data
        elif 'supertoken' in tags:
            super_tokens_data.append(token_data)
        else:
            log.error(
                f'Encountered unexpected token tags in the Superfluid token list. '
                f'Expected either "underlying" or "supertoken" tags. Skipping. '
                f'Token data: {token_data!s}',
            )

    last_notified_ts = maybe_notify_cache_query_status(
        msg_aggregator=evm_inquirer.database.msg_aggregator,
        last_notified_ts=Timestamp(0),
        protocol='Superfluid',
        chain=evm_inquirer.chain_id,
        processed=0,
        total=(total_super_token_count := len(super_tokens_data)),
    )  # Notify of the total super token count and then process the tokens
    for super_token in super_tokens_data:
        if (
            (token_info := super_token.get('extensions', {}).get('superTokenInfo')) is None or
            (token_type := token_info.get('type')) is None
        ):
            log.error(f'Encountered a Superfluid super token missing expected data. Skipping. Token data: {super_token}')  # noqa: E501
            continue

        if token_type == 'Pure':
            continue  # Pure super tokens don't have an underlying asset with any need for deposit/withdrawal decoding etc.  # noqa: E501
        elif token_type == 'Native Asset':
            underlying_tokens = []  # Underlying tokens must have evm addresses. Any super token with no underlying tokens will be assumed to have the native asset for its underlying token.  # noqa: E501
        elif token_type == 'Wrapper':
            underlying_token_data = None
            try:
                if (underlying_token_data := underlying_tokens_data.get(underlying_token_address := token_info['underlyingTokenAddress'])) is not None:  # noqa: E501
                    underlying_token = get_or_create_evm_token(
                        userdb=evm_inquirer.database,
                        evm_address=deserialize_evm_address(underlying_token_address),
                        chain_id=evm_inquirer.chain_id,
                        symbol=underlying_token_data['symbol'],
                        name=underlying_token_data['name'],
                        decimals=underlying_token_data['decimals'],
                    )
                else:
                    log.warning(
                        'Encountered a Superfluid super token with an underlying token that was '
                        'missing from the token list. Querying its token details from onchain. ',
                    )
                    underlying_token = get_or_create_evm_token(
                        userdb=evm_inquirer.database,
                        evm_address=deserialize_evm_address(underlying_token_address),
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                    )
            except (KeyError, NotERC20Conformant) as e:
                msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
                log.error(
                    f'Failed to load Superfluid underlying token due to {msg}. Skipping. '
                    f'Token data: {super_token}. Underlying token data: {underlying_token_data}',
                )
                continue

            underlying_tokens = [UnderlyingToken(
                address=underlying_token.evm_address,
                token_kind=underlying_token.token_kind,
                weight=ONE,
            )]
        else:
            log.error(
                f'Encountered a Superfluid super token with unknown type. '
                f'Expected either "Native Asset" or "Wrapper", but got "{token_type}". Skipping. '
                f'Token data: {super_token}',
            )
            continue

        try:
            get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_address=deserialize_evm_address(super_token['address']),
                chain_id=evm_inquirer.chain_id,
                symbol=super_token['symbol'],
                name=super_token['name'],
                decimals=super_token['decimals'],
                protocol=CPT_SUPERFLUID,
                underlying_tokens=underlying_tokens,
            )
        except (KeyError, NotERC20Conformant) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(f'Failed to load Superfluid super token due to {msg}. Skipping. Token data: {super_token}')  # noqa: E501

        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=evm_inquirer.database.msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol='Superfluid',
            chain=evm_inquirer.chain_id,
            processed=0,
            total=total_super_token_count,
        )

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.SUPERFLUID_TOKEN_LIST_VERSION, str(chain_id_int)),
            value=version,
        )
