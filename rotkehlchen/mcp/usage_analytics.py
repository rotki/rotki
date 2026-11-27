from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Final, Literal
from weakref import WeakKeyDictionary, WeakSet

from rotkehlchen.mcp.backend import (
    BackendQueryError,
    get_backend_config,
    query_frontend_settings,
    query_settings,
)
from rotkehlchen.mcp.premium import get_current_tier
from rotkehlchen.sigil import (
    SIGIL_DEVELOPMENT_WEBSITE_ID,
    SIGIL_PRODUCTION_WEBSITE_ID,
    client_id_from_frontend_settings,
    create_sigil_events_batch,
    submit_sigil_batch,
)
from rotkehlchen.utils.misc import is_production

if TYPE_CHECKING:
    from mcp.server.session import ServerSession
    from mcp.types import InitializeRequestParams, RequestParams
    from pydantic import BaseModel

MODEL_METADATA_KEYS: Final = ('model', 'modelId', 'model_id')
McpAnalyticsEvent = Literal['mcp_gated', 'mcp_tool_used', 'mcp_usage']


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
    """Create the MCP client details sent to Sigil.

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

    with suppress(BackendQueryError):
        data['plan'] = get_current_tier()

    return data


def maybe_submit_mcp_analytics(
        events: list[tuple[McpAnalyticsEvent, dict[str, Any]]],
        client_params: InitializeRequestParams,
        request_meta: RequestParams.Meta | None,
) -> None:
    """Submit MCP events when analytics are enabled.

    The events carry the frontend's client id, when the frontend has stored one, so Sigil
    attributes them to the same user as the app's own events.
    """
    try:
        if query_settings().get('submit_usage_analytics') is not True:
            return
    except BackendQueryError:
        return

    client_data = create_mcp_usage_analytics(
        client_params=client_params,
        request_meta=request_meta,
    )
    distinct_id = None
    with suppress(BackendQueryError):
        distinct_id = client_id_from_frontend_settings(query_frontend_settings())

    batch = create_sigil_events_batch(
        events=[(name, '/mcp', {**client_data, **data}) for name, data in events],
        website_id=SIGIL_PRODUCTION_WEBSITE_ID
        if is_production() else SIGIL_DEVELOPMENT_WEBSITE_ID,
        distinct_id=distinct_id,
    )
    submit_sigil_batch(batch=batch, timeout=get_backend_config().timeout)


class McpUsageAnalyticsTracker:
    """Submit bounded usage, gated-access and tool analytics for MCP sessions."""

    def __init__(self) -> None:
        self._reported_models: WeakKeyDictionary[ServerSession, set[str]] = WeakKeyDictionary()
        self._reported_tools: WeakKeyDictionary[ServerSession, set[str]] = WeakKeyDictionary()
        self._reported_gates: WeakSet[ServerSession] = WeakSet()
        self._tasks: set[asyncio.Task[None]] = set()

    def track(
            self,
            session: ServerSession,
            client_params: InitializeRequestParams,
            request_meta: RequestParams.Meta | None,
            tool_name: str,
    ) -> None:
        """Record a model and each distinct tool at most once per session."""
        events: list[tuple[McpAnalyticsEvent, dict[str, Any]]] = []
        reported_models = self._reported_models.setdefault(session, set())
        if (model := _model_from_client(client_params, request_meta)) not in reported_models:
            reported_models.add(model)
            events.append(('mcp_usage', {}))

        reported_tools = self._reported_tools.setdefault(session, set())
        if tool_name not in reported_tools:
            reported_tools.add(tool_name)
            events.append(('mcp_tool_used', {'toolName': tool_name}))

        self._schedule(events=events, client_params=client_params, request_meta=request_meta)

    def track_gated(
            self,
            session: ServerSession,
            client_params: InitializeRequestParams,
            request_meta: RequestParams.Meta | None,
    ) -> None:
        """Record the first premium wall encountered during a session."""
        if session in self._reported_gates:
            return

        self._reported_gates.add(session)
        self._schedule(
            events=[('mcp_gated', {})],
            client_params=client_params,
            request_meta=request_meta,
        )

    def _schedule(
            self,
            events: list[tuple[McpAnalyticsEvent, dict[str, Any]]],
            client_params: InitializeRequestParams,
            request_meta: RequestParams.Meta | None,
    ) -> None:
        if not events:
            return

        self._tasks.add(task := asyncio.create_task(
            asyncio.to_thread(
                maybe_submit_mcp_analytics,
                events,
                client_params,
                request_meta,
            ),
        ))
        task.add_done_callback(self._tasks.discard)
