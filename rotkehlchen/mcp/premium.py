from __future__ import annotations

import time
from typing import Any, Final

from rotkehlchen.mcp.backend import BackendQueryError, get_backend_config, request_api

DEFAULT_TIER: Final = 'Free'
# Tiers that do NOT grant MCP access. Everything else (Basic and up) does. The tier
# names are defined server-side, not here; the authoritative list can be fetched from
# https://rotki.com/webapi/2/available-tiers (the `tier_name` of each entry). As of this
# writing the paid tiers are ordered Supporter < Basic < Advanced.
NON_MCP_TIERS: Final = frozenset({DEFAULT_TIER, 'Supporter'})
PREMIUM_CACHE_TTL: Final = 60.0
UPGRADE_URL: Final = 'https://rotki.com/products/'

_premium_cache: tuple[float, bool] | None = None


def _query_mcp_access() -> bool:
    backend_config = get_backend_config()
    payload = request_api(
        base_url=backend_config.base_url,
        endpoint='premium/capabilities',
        timeout=backend_config.timeout,
    )
    if not isinstance(result := payload.get('result'), dict):
        raise BackendQueryError(
            'rotki backend returned an unexpected premium capabilities response',
        )
    return result.get('current_tier', DEFAULT_TIER) not in NON_MCP_TIERS


def has_mcp_access() -> bool:
    """Return whether the unlocked backend's subscription tier grants MCP access.

    MCP is available to the Basic tier and up; the Free and Supporter tiers are excluded.
    The result is cached for PREMIUM_CACHE_TTL seconds so gated tools don't hit the
    backend on every call, while still noticing a subscription that lapses or starts
    mid-session.
    """
    global _premium_cache  # noqa: PLW0603 -- short-lived MCP premium status cache
    now = time.monotonic()
    if _premium_cache is not None and now - _premium_cache[0] < PREMIUM_CACHE_TTL:
        return _premium_cache[1]

    allowed = _query_mcp_access()
    _premium_cache = (now, allowed)
    return allowed


def reset_premium_cache() -> None:
    """Clear the cached premium status. Mainly useful for tests."""
    global _premium_cache  # noqa: PLW0603 -- short-lived MCP premium status cache
    _premium_cache = None


def premium_gate() -> dict[str, Any] | None:
    """Return a structured error if MCP access should be blocked, otherwise None.

    A backend that cannot be reached or queried is treated as ineligible so gated
    tools fail closed rather than leaking data.
    """
    try:
        if has_mcp_access():
            return None
    except BackendQueryError as e:
        return {
            'error': 'premium_check_failed',
            'message': f'Could not verify rotki premium subscription: {e!s}',
            'upgrade_url': UPGRADE_URL,
        }

    return {
        'error': 'premium_required',
        'message': 'This tool requires a rotki Basic subscription or higher.',
        'upgrade_url': UPGRADE_URL,
    }
