import asyncio
from typing import Any

from rotkehlchen.mcp.backend import BackendQueryError, get_backend_config, request_api
from rotkehlchen.mcp.registry import register_tool
from rotkehlchen.utils.version_check import get_current_version


def _extract_backend_version(payload: dict[str, Any]) -> str | None:
    if not isinstance(result := payload.get('result'), dict):
        return None
    if not isinstance(version := result.get('version'), dict):
        return None
    if (our_version := version.get('our_version')) is None:
        return None
    return str(our_version)


def _get_backend_status() -> dict[str, Any]:
    backend_config = get_backend_config()
    status: dict[str, Any] = {
        'url': backend_config.base_url,
        'connected': False,
        'unlocked': False,
        'message': None,
    }

    try:
        request_api(
            base_url=backend_config.base_url,
            endpoint='ping',
            timeout=backend_config.timeout,
        )
        status['connected'] = True

        users_payload = request_api(
            base_url=backend_config.base_url,
            endpoint='users',
            timeout=backend_config.timeout,
        )
        users = users_payload['result']
        if not isinstance(users, dict):
            raise BackendQueryError('rotki backend returned an unexpected users response')

        status['unlocked'] = any(user_status == 'loggedin' for user_status in users.values())
        if status['unlocked'] is False:
            status['message'] = 'rotki backend is reachable but no user database is unlocked'

        info_payload = request_api(
            base_url=backend_config.base_url,
            endpoint='info',
            timeout=backend_config.timeout,
            params={'check_for_updates': False},
        )
        status['version'] = _extract_backend_version(info_payload)
    except BackendQueryError as e:
        status['message'] = str(e)

    return status


def get_info() -> dict[str, Any]:
    """Return the MCP version and unlocked backend connectivity status."""
    return {
        'mcp': {
            'version': str(get_current_version().our_version),
        },
        'backend': _get_backend_status(),
    }


@register_tool(name='info')
async def info() -> dict[str, Any]:
    """Return rotki version and verify connectivity to the unlocked backend."""
    return await asyncio.to_thread(get_info)
