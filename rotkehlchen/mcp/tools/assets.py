import asyncio
from typing import Any

from rotkehlchen.mcp.backend import query_asset_details
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='get_asset_details')
async def get_asset_details(identifiers: list[str]) -> dict[str, Any]:
    """Get GlobalDB details for assets by their exact rotki identifiers.

    Use identifiers found in balance and history-event data. Each matching entry includes
    its canonical identifier, asset type, name and symbol. Token entries also include their
    decimals, address, chain, token kind and protocol. Identifiers without a match are omitted.
    """
    return await asyncio.to_thread(query_asset_details, identifiers=identifiers)
