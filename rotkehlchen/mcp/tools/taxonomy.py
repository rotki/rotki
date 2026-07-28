import asyncio
from typing import Any

from rotkehlchen.mcp.registry import register_tool
from rotkehlchen.mcp.taxonomy import get_event_taxonomy as build_event_taxonomy


@register_tool(name='get_event_taxonomy')
async def get_event_taxonomy() -> dict[str, Any]:
    """Explain what rotki's history event types and subtypes mean, and which way value moves.

    **Call this before any aggregate over ``event_type``, ``event_subtype`` or ``direction``.**
    A ``GROUP BY event_type, event_subtype`` returns 30+ combinations whose names do not say
    whether they are income, expense or a bookkeeping annotation, and guessing produces
    confidently wrong totals -- most commonly by double counting MEV and block-production
    rewards, which appear both as an ``informational`` report and as the real event.

    Returns, all derived from rotki's own definitions rather than restated here:

    - ``rules``: the handful of semantics you cannot read off the data.
    - ``entries``: every valid ``(event_type, event_subtype)`` with its category, label,
      ``group`` (income / expense / trade / staking ...) and ``direction``
      (``in`` / ``out`` / ``neutral``). ``direction`` is the field to aggregate on.
    - ``grouped_event_types``: which event types span several rows sharing a
      ``group_identifier``, and in what leg order.
    """
    return await asyncio.to_thread(build_event_taxonomy)
