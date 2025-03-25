import logging
from collections import defaultdict
from typing import Final

from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID
from rotkehlchen.utils.network import request_get_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

STAKEDAO_API: Final = 'https://api.stakedao.org/api'
# This is gotten from:
# https://github.com/stake-dao/api?tab=readme-ov-file#strategies-data
SUPPORTED_STAKEDAO_STRATEGIES: Final = {'curve', 'balancer', 'pendle', 'pancakeswap', 'angle'}


def query_stakedao_gauges() -> None:
    """Query StakeDAO gauges for lockers and strategies from the API and cache them."""
    all_gauges: dict[ChainID, set] = defaultdict(set)

    try:  # Query lockers
        response_data = request_get_dict(url=f'{STAKEDAO_API}/lockers')
        for item in response_data['parsed']:
            try:
                all_gauges[ChainID.deserialize(item['chainId'])].add(deserialize_evm_address(item['modules']['gauge']))
            except (KeyError, DeserializationError) as e:
                log.warning(f'Skipping stakedao locker entry {item} due to {e!s}')
                continue

        for protocol in SUPPORTED_STAKEDAO_STRATEGIES:  # Query strategies
            response_data = request_get_dict(url=f'{STAKEDAO_API}/strategies/{protocol}')
            for item in response_data['deployed']:
                try:
                    all_gauges[ChainID.deserialize(item['chainId'])].add(deserialize_evm_address(item['sdGauge']['address']))
                except (KeyError, DeserializationError) as e:
                    log.warning(f'Skipping stakedao strategy entry {item} due to {e!s}')
                    continue

    except (RemoteError, UnableToDecryptRemoteData, TypeError, KeyError) as e:
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
        log.error(f'Failed to retrieve StakeDAO gauges for lockers and strategies from API due to {msg}')  # noqa: E501

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for chain_id, addresses in all_gauges.items():
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.STAKEDAO_GAUGES, str(chain_id.value)),
                values=addresses,
            )
