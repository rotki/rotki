import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
import requests
from mcp.types import InitializeRequestParams, RequestParams

from rotkehlchen.mcp import usage_analytics
from rotkehlchen.mcp.backend import BackendQueryError, configure_backend
from rotkehlchen.sigil import SIGIL_BATCH_ENDPOINT

if TYPE_CHECKING:
    from mcp.server.session import ServerSession


class MockSession:
    pass


@pytest.fixture(autouse=True)
def fixture_no_frontend_client_id(monkeypatch) -> None:
    monkeypatch.setattr(usage_analytics, 'query_frontend_settings', dict)


def test_create_mcp_usage_analytics(monkeypatch) -> None:
    monkeypatch.setattr(usage_analytics, 'get_current_tier', lambda: 'Basic')
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
        'plan': 'Basic',
    }

    assert usage_analytics.create_mcp_usage_analytics(
        client_params=client_params,
        request_meta=RequestParams.Meta.model_validate({'model': 'gpt-5.6'}),
    )['model'] == 'gpt-5.6'


def test_create_mcp_usage_analytics_omits_plan_on_backend_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        usage_analytics,
        'get_current_tier',
        MagicMock(side_effect=BackendQueryError('backend unavailable')),
    )
    data = usage_analytics.create_mcp_usage_analytics(
        client_params=InitializeRequestParams.model_validate({
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'test-client', 'version': '1.0'},
        }),
        request_meta=None,
    )

    assert 'plan' not in data


async def _track_models(
        tracker: usage_analytics.McpUsageAnalyticsTracker,
        client_params: InitializeRequestParams,
) -> None:
    first_session = cast('ServerSession', MockSession())
    second_session = cast('ServerSession', MockSession())
    first_model = RequestParams.Meta.model_validate({'model': 'gpt-5.6'})
    second_model = RequestParams.Meta.model_validate({'model': 'claude-opus-4'})
    tracker.track(
        session=first_session,
        client_params=client_params,
        request_meta=first_model,
        tool_name='get_balances',
    )
    tracker.track(
        session=first_session,
        client_params=client_params,
        request_meta=first_model,
        tool_name='get_balances',
    )
    tracker.track(
        session=first_session,
        client_params=client_params,
        request_meta=second_model,
        tool_name='get_balances',
    )
    tracker.track(
        session=second_session,
        client_params=client_params,
        request_meta=first_model,
        tool_name='get_balances',
    )
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


async def _track_tools_and_gate(
        tracker: usage_analytics.McpUsageAnalyticsTracker,
        client_params: InitializeRequestParams,
) -> None:
    session = cast('ServerSession', MockSession())
    tracker.track(
        session=session,
        client_params=client_params,
        request_meta=None,
        tool_name='get_balances',
    )
    tracker.track(
        session=session,
        client_params=client_params,
        request_meta=None,
        tool_name='get_history',
    )
    tracker.track_gated(session=session, client_params=client_params, request_meta=None)
    tracker.track_gated(session=session, client_params=client_params, request_meta=None)
    await asyncio.sleep(0)


def test_mcp_usage_analytics_tracker_reports_distinct_tools_and_one_gate(monkeypatch) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', to_thread_mock := AsyncMock())
    client_params = InitializeRequestParams.model_validate({
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {'name': 'test-client', 'version': '1.0'},
    })

    asyncio.run(_track_tools_and_gate(
        tracker=usage_analytics.McpUsageAnalyticsTracker(),
        client_params=client_params,
    ))

    assert to_thread_mock.await_count == 3
    assert [call.args[1] for call in to_thread_mock.await_args_list] == [
        [('mcp_usage', {}), ('mcp_tool_used', {'toolName': 'get_balances'})],
        [('mcp_tool_used', {'toolName': 'get_history'})],
        [('mcp_gated', {})],
    ]


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
    monkeypatch.setattr(usage_analytics, 'get_current_tier', lambda: 'Basic')
    monkeypatch.setattr(
        usage_analytics,
        'query_frontend_settings',
        lambda: {'client_id': 'a7c1e0f2-5b3d-4c8e-9f10-2d4b6a8c0e12'},
    )
    client_params = InitializeRequestParams.model_validate({
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {
            'name': 'codex-mcp-client',
            'title': 'Codex',
            'version': '0.47.0',
        },
    })
    usage_analytics.maybe_submit_mcp_analytics(
        events=[('mcp_usage', {})],
        client_params=client_params,
        request_meta=RequestParams.Meta.model_validate({'model': 'gpt-5.6'}),
    )

    post_mock.assert_called_once()
    assert (kwargs := post_mock.call_args.kwargs)['url'] == SIGIL_BATCH_ENDPOINT
    assert kwargs['timeout'] == 3
    assert kwargs['headers']['Content-Type'] == 'application/json'
    assert kwargs['json'][0]['payload']['website'] == (
        usage_analytics.SIGIL_PRODUCTION_WEBSITE_ID
    )
    assert kwargs['json'][0]['payload']['name'] == 'mcp_usage'
    assert kwargs['json'][0]['payload']['id'] == 'a7c1e0f2-5b3d-4c8e-9f10-2d4b6a8c0e12'
    assert kwargs['json'][0]['payload']['data'] == {
        'clientName': 'codex-mcp-client',
        'clientTitle': 'Codex',
        'clientVersion': '0.47.0',
        'model': 'gpt-5.6',
        'plan': 'Basic',
    }


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

    monkeypatch.setattr(usage_analytics, 'get_current_tier', lambda: 'Free')
    monkeypatch.setattr(
        usage_analytics,
        'query_frontend_settings',
        MagicMock(side_effect=BackendQueryError('backend unavailable')),
    )
    usage_analytics.maybe_submit_mcp_analytics(
        events=[('mcp_usage', {})],
        client_params=InitializeRequestParams.model_validate({
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'test-client', 'version': '1.0'},
        }),
        request_meta=None,
    )

    assert post_mock.call_args.kwargs['json'][0]['payload']['website'] == (
        usage_analytics.SIGIL_DEVELOPMENT_WEBSITE_ID
    )
    assert 'id' not in post_mock.call_args.kwargs['json'][0]['payload']


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

    usage_analytics.maybe_submit_mcp_analytics(
        events=[('mcp_usage', {})],
        client_params=InitializeRequestParams.model_validate({
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'test-client', 'version': '1.0'},
        }),
        request_meta=None,
    )
    post_mock.assert_not_called()
    production_mock.assert_not_called()


def test_submit_mcp_usage_analytics_ignores_failures(monkeypatch) -> None:
    monkeypatch.setattr(usage_analytics, 'is_production', lambda: True)
    monkeypatch.setattr(
        usage_analytics,
        'query_settings',
        MagicMock(side_effect=BackendQueryError('backend unavailable')),
    )
    client_params = InitializeRequestParams.model_validate({
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {'name': 'test-client', 'version': '1.0'},
    })
    usage_analytics.maybe_submit_mcp_analytics(
        events=[('mcp_usage', {})],
        client_params=client_params,
        request_meta=None,
    )

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
    monkeypatch.setattr(usage_analytics, 'get_current_tier', lambda: 'Free')
    usage_analytics.maybe_submit_mcp_analytics(
        events=[('mcp_usage', {})],
        client_params=client_params,
        request_meta=None,
    )
