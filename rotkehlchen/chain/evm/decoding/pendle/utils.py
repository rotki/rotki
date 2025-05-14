import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import requests

from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token, get_token
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, Price
from rotkehlchen.utils.network import create_session, request_get_dict

from .constants import CPT_PENDLE

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_pendle_markets(chain: ChainID) -> None:
    """Query Pendle markets for a given chain and cache their addresses."""
    all_markets, all_sy_tokens = [], []
    session = create_session()
    try:
        for market_type in ('active', 'inactive'):  # query active and inactive markets
            response = session.get(url=f'https://api-v2.pendle.finance/core/v1/{chain.serialize()}/markets/{market_type}')
            if response.status_code != HTTPStatus.OK:
                log.error(
                    f'Pendle {market_type} markets query for {chain} failed '
                    f'with status {response.status_code} and message {response.text}',
                )
                return

            for market in response.json()['markets']:
                try:
                    all_markets.append(deserialize_evm_address(market['address']))
                    all_sy_tokens.append(deserialize_evm_address(market['sy'].split('-')[1]))
                except (DeserializationError, KeyError, IndexError, ValueError) as e:
                    msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
                    log.warning(f'Skipping pendle market entry {market} for {chain} due to {msg}')
                    continue

    except (requests.RequestException, TypeError, KeyError) as e:
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
        log.error(f'Failed to retrieve Pendle markets for {chain} due to {msg}')

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.PENDLE_POOLS, str(chain.serialize())),
            values=all_markets,
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.PENDLE_SY_TOKENS, str(chain.serialize())),
            values=all_sy_tokens,
        )


def query_pendle_price(token: 'EvmToken') -> Price:
    """Query USD price for a given Pendle PT/YT/SY/LP token"""
    try:
        result = request_get_dict(f'https://api-v2.pendle.finance/core/v1/{token.chain_id.serialize()}/assets/prices?addresses={token.evm_address}')
        return deserialize_price(result['prices'][token.evm_address.lower()])
    except (RemoteError, UnableToDecryptRemoteData, DeserializationError, TypeError, ValueError, KeyError) as e:  # noqa: E501
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
        log.error(f'Unable to query usd price of pendle wrapped token {token} due to {msg}')
        return ZERO_PRICE


def query_pendle_yield_tokens(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Queries all Pendle yield tokens(LP, SY, PT, YT) and saves them to allow price queries."""
    all_tokens: set[ChecksumEvmAddress] = set()
    try:
        all_tokens.update(deserialize_evm_address(entry['address']) for entry in request_get_dict(f'https://api-v2.pendle.finance/core/v3/{evm_inquirer.chain_id.serialize()}/assets/all')['assets'])
    except (RemoteError, UnableToDecryptRemoteData, DeserializationError, IndexError, KeyError) as e:  # noqa: E501
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!r}'
        log.error(f'Unable to fetch pendle data for {evm_inquirer.chain_name} due to {msg}')
        return

    encounter = TokenEncounterInfo(should_notify=False, description='Querying Pendle yield tokens')
    for token in all_tokens:
        try:
            if (cached_token := get_token(evm_address=token, chain_id=evm_inquirer.chain_id)) is not None:  # noqa: E501
                get_or_create_evm_token(
                    name=cached_token.name,
                    symbol=cached_token.symbol,
                    decimals=cached_token.decimals,
                    protocol=CPT_PENDLE,
                    userdb=evm_inquirer.database,
                    evm_address=token,
                    encounter=encounter,
                    chain_id=evm_inquirer.chain_id,
                )
            else:
                get_or_create_evm_token(
                    evm_address=token,
                    protocol=CPT_PENDLE,
                    evm_inquirer=evm_inquirer,
                    userdb=evm_inquirer.database,
                    encounter=encounter,
                    chain_id=evm_inquirer.chain_id,
                )
        except NotERC20Conformant as e:
            log.error(f'Failed to add pendle token {token} for {evm_inquirer.chain_name} due to {e!s}')  # noqa: E501
            continue

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.PENDLE_YIELD_TOKENS, str(evm_inquirer.chain_id.serialize())),
            value=str(len(all_tokens)),
        )
