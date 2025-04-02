import logging

from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID
from rotkehlchen.utils.network import request_get_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_pendle_markets(chain: ChainID) -> None:
    """Query Pendle markets for a given chain and cache their addresses."""
    all_markets, all_sy_tokens = [], []
    try:
        for market_type in ['active', 'inactive']:  # query active and inactive markets
            response_data = request_get_dict(url=f'https://api-v2.pendle.finance/core/v1/{chain.value}/markets/{market_type}')
            for market in response_data['markets']:
                try:
                    all_markets.append(deserialize_evm_address(market['address']))
                    all_sy_tokens.append(deserialize_evm_address(market['sy'].split('-')[1]))
                except (KeyError, ValueError) as e:
                    log.warning(f'Skipping pendle market entry {market} due to {e!s}')
                    continue

    except (RemoteError, UnableToDecryptRemoteData, TypeError, KeyError) as e:
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
        log.error(f'Failed to retrieve Pendle markets for chain {chain} due to {msg}')

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.PENDLE_POOLS, str(chain.value)),
            values=all_markets,
        )

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.PENDLE_SY_TOKENS, str(chain.value)),
            values=all_sy_tokens,
        )
