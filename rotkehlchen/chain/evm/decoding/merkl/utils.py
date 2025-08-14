import logging
from typing import Final, Literal

from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChainID
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.network import request_get

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MERKL_PROTOCOL_CACHE_REFRESH: Final = DAY_IN_SECONDS * 2


def get_merkl_protocol_for_token(
        account: str,
        token: str,
        chain_id: ChainID,
) -> str | None:
    """Get protocol for a specific account and token by fetching directly from Merkl API"""
    key_parts: tuple[Literal[CacheType.MERKL_REWARD_PROTOCOLS], str] = (CacheType.MERKL_REWARD_PROTOCOLS, f'{chain_id.serialize_for_db()!s}_{token}_{account}')  # noqa: E501
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (  # Check if cache is still valid (not expired)
            (last_update_ts := globaldb_get_unique_cache_last_queried_ts_by_key(
                cursor=cursor,
                key_parts=key_parts,
            )) and ts_now() - last_update_ts < MERKL_PROTOCOL_CACHE_REFRESH and
            (result := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=key_parts,
            )) is not None
        ):
            return result

    protocols = set()
    page, items_per_page = 0, 100
    while True:
        try:
            response = request_get(f'https://api.merkl.xyz/v4/opportunities?chainId={chain_id.serialize_for_db()}&search={token}&page={page}&items={items_per_page}&status=LIVE,PAST,SOON')
            for opportunity in response:
                try:
                    protocols.add(opportunity['protocol']['name'])
                except KeyError as e:
                    log.error(f'Failed to get protocols for {account=} on {chain_id=} due to missing key {e!s}')  # noqa: E501
                    continue

            if len(response) < items_per_page:  # If we get less than the full page size, we've reached the end  # noqa: E501
                break

            page += 1

        except (RemoteError, UnableToDecryptRemoteData, KeyError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(f'Failed to retrieve Merkl opportunities for account {account=} on {chain_id=} page {page} due to {msg}')  # noqa: E501
            return None

    # Merkl API doesn't provide a way to match claims to specific protocols.
    # We can only confidently return a protocol if exactly one protocol uses this token.
    # If there are multiple protocols or none, we cannot determine the correct one.
    if len(protocols) != 1:
        log.debug(f'Found multiple protocols `{protocols}` for token {token} on {chain_id=}. Cannot determine specific protocol for merkle claim')  # noqa: E501
        return None

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=key_parts,
            value=(protocol := next(iter(protocols))),
        )

    return protocol
