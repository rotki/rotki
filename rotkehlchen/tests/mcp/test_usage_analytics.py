import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import requests
from mcp.types import InitializeRequestParams, RequestParams

from rotkehlchen.mcp import usage_analytics
from rotkehlchen.mcp.backend import BackendQueryError, configure_backend

if TYPE_CHECKING:
    from mcp.server.session import ServerSession


class MockSession:
    pass


def test_create_mcp_usage_analytics() -> None:
    client_params = InitializeRequestParams.model_validate({
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {
            'name': 'codex-mcp-client',
            'title': 'Codex',
            'version': '0.47.0',
        },
    })

    assert usage_analytics.create_mcp_usage_analytics(
        client_params=client_params,
        request_meta=None,
    ) == {
        'clientName': 'codex-mcp-client',
        'clientTitle': 'Codex',
        'clientVersion': '0.47.0',
        'model': '',
    }

    assert usage_analytics.create_mcp_usage_analytics(
        client_params=client_params,
        request_meta=RequestParams.Meta.model_validate({'model': 'gpt-5.6'}),
    )['model'] == 'gpt-5.6'


def test_create_sigil_batch_matches_frontend_schema() -> None:
    data = {'clientName': 'codex-mcp-client', 'model': 'gpt-5.6'}

    assert usage_analytics.create_sigil_batch(
        data=data,
        website_id=usage_analytics.SIGIL_PRODUCTION_WEBSITE_ID,
    ) == [{
        'type': 'event',
        'payload': {
            'website': usage_analytics.SIGIL_PRODUCTION_WEBSITE_ID,
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


async def _track_models(
        tracker: usage_analytics.McpUsageAnalyticsTracker,
        client_params: InitializeRequestParams,
) -> None:
    first_session = cast('ServerSession', MockSession())
    second_session = cast('ServerSession', MockSession())
    first_model = RequestParams.Meta.model_validate({'model': 'gpt-5.6'})
    second_model = RequestParams.Meta.model_validate({'model': 'claude-opus-4'})
    tracker.track(session=first_session, client_params=client_params, request_meta=first_model)
    tracker.track(session=first_session, client_params=client_params, request_meta=first_model)
    tracker.track(session=first_session, client_params=client_params, request_meta=second_model)
    tracker.track(session=second_session, client_params=client_params, request_meta=first_model)
    await asyncio.sleep(0)


def test_mcp_usage_analytics_tracker_deduplicates_per_session_and_model(monkeypatch) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', to_thread_mock := AsyncMock())
    client_params = InitializeRequestParams.model_validate({
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {'name': 'codex-mcp-client', 'version': '0.47.0'},
    })
    tracker = usage_analytics.McpUsageAnalyticsTracker()

    asyncio.run(_track_models(tracker=tracker, client_params=client_params))

    assert to_thread_mock.await_count == 3


def test_submit_mcp_usage_analytics(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=3)
    monkeypatch.setattr(usage_analytics, 'is_production', lambda: True)
    monkeypatch.setattr(
        usage_analytics,
        'query_settings',
        lambda: {'submit_usage_analytics': True},
    )

    monkeypatch.setattr(
        requests,
        'post',
        post_mock := MagicMock(return_value=MagicMock(ok=True, status_code=200)),
    )
    usage_analytics.maybe_submit_mcp_usage_analytics(data := {
        'clientName': 'codex-mcp-client',
        'clientTitle': 'Codex',
        'clientVersion': '0.47.0',
        'model': 'gpt-5.6',
    })

    post_mock.assert_called_once()
    assert (kwargs := post_mock.call_args.kwargs)['url'] == usage_analytics.SIGIL_BATCH_ENDPOINT
    assert kwargs['timeout'] == 3
    assert kwargs['headers']['Content-Type'] == 'application/json'
    assert kwargs['json'][0]['payload']['website'] == (
        usage_analytics.SIGIL_PRODUCTION_WEBSITE_ID
    )
    assert kwargs['json'][0]['payload']['name'] == 'mcp_usage'
    assert kwargs['json'][0]['payload']['data'] == data


def test_submit_mcp_usage_analytics_uses_development_website(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=3)
    monkeypatch.setattr(usage_analytics, 'is_production', lambda: False)
    monkeypatch.setattr(
        usage_analytics,
        'query_settings',
        lambda: {'submit_usage_analytics': True},
    )
    monkeypatch.setattr(
        requests,
        'post',
        post_mock := MagicMock(return_value=MagicMock(ok=True, status_code=200)),
    )

    usage_analytics.maybe_submit_mcp_usage_analytics({'model': 'gpt-5.6'})

    assert post_mock.call_args.kwargs['json'][0]['payload']['website'] == (
        usage_analytics.SIGIL_DEVELOPMENT_WEBSITE_ID
    )


def test_submit_mcp_usage_analytics_respects_opt_out(monkeypatch) -> None:
    monkeypatch.setattr(usage_analytics, 'is_production', production_mock := MagicMock())
    monkeypatch.setattr(
        usage_analytics,
        'query_settings',
        lambda: {'submit_usage_analytics': False},
    )
    monkeypatch.setattr(
        requests,
        'post',
        post_mock := MagicMock(),
    )

    usage_analytics.maybe_submit_mcp_usage_analytics({'model': ''})
    post_mock.assert_not_called()
    production_mock.assert_not_called()


def test_submit_mcp_usage_analytics_ignores_failures(monkeypatch) -> None:
    monkeypatch.setattr(usage_analytics, 'is_production', lambda: True)
    monkeypatch.setattr(
        usage_analytics,
        'query_settings',
        MagicMock(side_effect=BackendQueryError('backend unavailable')),
    )
    usage_analytics.maybe_submit_mcp_usage_analytics({'model': ''})

    monkeypatch.setattr(
        usage_analytics,
        'query_settings',
        lambda: {'submit_usage_analytics': True},
    )
    monkeypatch.setattr(
        requests,
        'post',
        MagicMock(side_effect=requests.ConnectionError()),
    )
    usage_analytics.maybe_submit_mcp_usage_analytics({'model': ''})
