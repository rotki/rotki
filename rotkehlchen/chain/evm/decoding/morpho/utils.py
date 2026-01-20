import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO, MORPHO_VAULT_ABI
from rotkehlchen.chain.evm.decoding.utils import get_vault_price
from rotkehlchen.chain.evm.utils import (
    maybe_notify_cache_query_status,
    maybe_notify_new_pools_status,
)
from rotkehlchen.constants import EXP18_INT
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_set_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Price,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MORPHO_BLUE_API: Final = 'https://blue-api.morpho.org/graphql'
MORPHO_REWARDS_API: Final = 'https://rewards.morpho.org/v1/programs'
VAULT_QUERY_PAGE_SIZE: Final = 200
VAULT_QUERY: Final = 'items {address symbol name asset {address symbol name decimals} chain {id}}'


def _query_morpho_vaults_api(
        chain_id: ChainID,
        msg_aggregator: 'MessagesAggregator',
) -> list[dict[str, Any]] | None:
    """Query morpho vaults from the morpho blue api.
    Returns vault list or None if there was an error."""
    all_vaults, offset, last_notified_ts = [], 0, Timestamp(0)
    while True:
        try:
            response_data = requests.post(
                url=MORPHO_BLUE_API,
                json={'query': f'query {{ vaults(first:{VAULT_QUERY_PAGE_SIZE} skip:{offset} where:{{chainId_in:[{chain_id.value}]}}) {{ {VAULT_QUERY} }} }}'},  # noqa: E501
                headers={'Content-Type': 'application/json'},
                timeout=CachedSettings().get_timeout_tuple(),
            )
            vault_list = response_data.json()['data']['vaults']['items']
            all_vaults.extend(vault_list)
            offset += VAULT_QUERY_PAGE_SIZE
            last_notified_ts = maybe_notify_new_pools_status(
                msg_aggregator=msg_aggregator,
                last_notified_ts=last_notified_ts,
                protocol=CPT_MORPHO,
                chain=chain_id,
                get_new_pools_count=lambda: len(all_vaults),
            )
            if len(vault_list) < VAULT_QUERY_PAGE_SIZE:
                break  # no more vaults to retrieve

        except (requests.RequestException, JSONDecodeError, TypeError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(f'Failed to retrieve morpho vaults from api due to {error}')
            return None

    return all_vaults


def query_morpho_vaults(chain_id: ChainID, msg_aggregator: 'MessagesAggregator') -> None:
    """Query list of Morpho vaults and add the vault tokens to the global database."""
    if (vault_list := _query_morpho_vaults_api(
            chain_id=chain_id,
            msg_aggregator=msg_aggregator,
    )) is None:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_update_cache_last_ts(
                write_cursor=write_cursor,
                cache_type=CacheType.MORPHO_VAULTS,
                key_parts=(str(chain_id.serialize()),),
            )  # Update cache timestamp to prevent repeated errors.
        return

    cache_entries, last_notified_ts, total_entries = [], Timestamp(0), len(vault_list)
    for idx, vault in enumerate(vault_list):
        try:
            cache_entries.append(','.join((
                deserialize_evm_address(vault['address']),
                deserialize_evm_address(vault['asset']['address']),
            )))
        except (DeserializationError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(
                f'Failed to cache Morpho vault address and underlying token address for vault '
                f'{vault} due to {error}. Skipping.',
            )

        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_MORPHO,
            chain=chain_id,
            processed=idx + 1,
            total=total_entries,
        )

    if len(cache_entries) > 0:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.MORPHO_VAULTS, str(chain_id.serialize())),
                values=cache_entries,
            )


def query_morpho_reward_distributors(chain_id: ChainID) -> None:
    """Query Morpho reward distributor addresses from the api and cache them."""
    try:
        response_data = requests.get(
            url=f'{MORPHO_REWARDS_API}?chains={chain_id.value}',
            timeout=CachedSettings().get_timeout_tuple(),
        ).json().get('data', [])
    except (requests.RequestException, AttributeError) as e:  # AttributeError to handle if the json is not a dict  # noqa: E501
        log.error(f'Failed to retrieve morpho reward distributors from api due to {e!s}')
        return

    distributors = set()
    for item in response_data:
        try:
            distributors.add(deserialize_evm_address(item['distributor']['address']))
        except (DeserializationError, TypeError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(f'Failed to deserialize morpho reward distributor entry from api due to {error}')  # noqa: E501

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.MORPHO_REWARD_DISTRIBUTORS, str(chain_id)),
            values=distributors,
        )


def get_morpho_vault_token_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets the token price for a Morpho vault."""
    return get_vault_price(
        inquirer=inquirer,
        vault_token=vault_token,
        evm_inquirer=evm_inquirer,
        display_name='Morpho',
        vault_abi=MORPHO_VAULT_ABI,
        pps_method='convertToAssets',
        pps_method_args=[EXP18_INT],  # 1 share with 18 decimals
    )
