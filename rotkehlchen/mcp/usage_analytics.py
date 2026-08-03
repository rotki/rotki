from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final, Literal, TypedDict
from weakref import WeakKeyDictionary

import requests

from rotkehlchen.mcp.backend import BackendQueryError, get_backend_config, query_settings
from rotkehlchen.utils.misc import ROTKI_USER_AGENT, is_production

if TYPE_CHECKING:
    from mcp.server.session import ServerSession
    from mcp.types import InitializeRequestParams, RequestParams
    from pydantic import BaseModel

SIGIL_BATCH_ENDPOINT: Final = 'https://sigil.rotki.com/api/batch'
SIGIL_DEVELOPMENT_WEBSITE_ID: Final = 'a3d69a71-060f-4397-afc5-e2ea1b6d389e'
SIGIL_PRODUCTION_WEBSITE_ID: Final = '4c195fc3-2beb-4492-a4f5-4c0f860bfbee'
MODEL_METADATA_KEYS: Final = ('model', 'modelId', 'model_id')


class SigilEventPayload(TypedDict):
    website: str
    hostname: str
    screen: str
    language: str
    title: str
    url: str
    referrer: str
    name: str
    data: dict[str, str]


class SigilBatchEntry(TypedDict):
    type: Literal['event']
    payload: SigilEventPayload


def _model_from_metadata(metadata: BaseModel | None) -> str | None:
    if metadata is None:
        return None

    if (extra := metadata.model_extra) is None:
        return None

    for key in MODEL_METADATA_KEYS:
        if isinstance(model := extra.get(key), str) and model:
            return model

    return None


def _model_from_client(
        client_params: InitializeRequestParams,
        request_meta: RequestParams.Meta | None,
) -> str:
    for metadata in (
        request_meta,
        client_params.meta,
        client_params.clientInfo,
        client_params,
    ):
        if (model := _model_from_metadata(metadata)) is not None:
            return model

    return ''


def create_mcp_usage_analytics(
        client_params: InitializeRequestParams,
        request_meta: RequestParams.Meta | None,
) -> dict[str, str]:
    """Create the non-identifying MCP client details sent to Sigil.

    MCP does not define a model field. Clients that want to expose it can add one to
    request ``_meta``, initialize ``_meta``, ``clientInfo``, or the initialize params.
    """
    client_info = client_params.clientInfo
    data = {
        'clientName': client_info.name,
        'clientVersion': client_info.version,
        'model': _model_from_client(client_params=client_params, request_meta=request_meta),
    }
    if client_info.title is not None:
        data['clientTitle'] = client_info.title

    return data


def create_sigil_batch(
        data: dict[str, str],
        website_id: str,
) -> list[SigilBatchEntry]:
    """Create the same batch-entry schema used by the frontend Sigil queue."""
    return [{
        'type': 'event',
        'payload': {
            'website': website_id,
            'hostname': '',
            'screen': '',
            'language': '',
            'title': '',
            'url': '/mcp',
            'referrer': '',
            'name': 'mcp_usage',
            'data': data,
        },
    }]


def maybe_submit_mcp_usage_analytics(data: dict[str, str]) -> None:
    """Submit one MCP client/model event when usage analytics are enabled."""
    try:
        if query_settings().get('submit_usage_analytics') is not True:
            return
    except BackendQueryError:
        return

    batch = create_sigil_batch(
        data=data,
        website_id=SIGIL_PRODUCTION_WEBSITE_ID
        if is_production() else SIGIL_DEVELOPMENT_WEBSITE_ID,
    )
    try:
        requests.post(
            url=SIGIL_BATCH_ENDPOINT,
            json=batch,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': ROTKI_USER_AGENT,
            },
            timeout=get_backend_config().timeout,
        )
    except requests.exceptions.RequestException:
        return


class McpUsageAnalyticsTracker:
    """Submit each model at most once during an MCP session."""

    def __init__(self) -> None:
        self._reported: WeakKeyDictionary[ServerSession, set[str]] = WeakKeyDictionary()
        self._tasks: set[asyncio.Task[None]] = set()

    def track(
            self,
            session: ServerSession,
            client_params: InitializeRequestParams,
            request_meta: RequestParams.Meta | None,
    ) -> None:
        data = create_mcp_usage_analytics(
            client_params=client_params,
            request_meta=request_meta,
        )
        reported_models = self._reported.setdefault(session, set())
        if (model := data['model']) in reported_models:
            return

        reported_models.add(model)
        self._tasks.add(task := asyncio.create_task(
            asyncio.to_thread(maybe_submit_mcp_usage_analytics, data),
        ))
        task.add_done_callback(self._tasks.discard)
