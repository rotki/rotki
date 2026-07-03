import asyncio
from typing import Any

from rotkehlchen.mcp.backend import query_historical_prices
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_historical_prices')
async def get_historical_prices(
        asset_timestamps: list[tuple[str, int]],
        target_asset: str,
        max_seconds_distance: int = 3600,
) -> dict[str, Any]:
    """Get historical prices already stored in rotki's GlobalDB.

    ``asset_timestamps`` is a JSON list of ``[asset_identifier, unix_timestamp]`` pairs.
    All timestamps are in seconds and all prices use ``target_asset`` as their quote asset.
    For each pair, the closest stored price within ``max_seconds_distance`` seconds is
    returned. Missing prices are omitted. This is cache-only and never calls remote oracles.
    """
    return await asyncio.to_thread(
        query_historical_prices,
        asset_timestamps=asset_timestamps,
        target_asset=target_asset,
        max_seconds_distance=max_seconds_distance,
    )
