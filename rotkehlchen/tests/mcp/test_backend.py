from http import HTTPStatus
from typing import Any

import pytest
import requests
from mcp.server.auth.provider import AccessToken

from rotkehlchen.api.session_token import MCP_BACKEND_PROOF_HEADER, create_mcp_backend_proof
from rotkehlchen.mcp.backend import (
    BackendQueryError,
    configure_backend,
    get_backend_config,
    query_historical_prices,
    query_settings,
    request_api,
)


class MockResponse:
    def __init__(
            self,
            payload: dict[str, Any],
            status_code: HTTPStatus = HTTPStatus.OK,
            text: str = '',
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> dict[str, Any]:
        return self.payload


def test_configure_backend_should_update_config() -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5)
    backend_config = get_backend_config()

    assert backend_config.base_url == 'http://backend/api/1'
    assert backend_config.timeout == 5


def test_request_api_should_raise_query_error_on_connection_failure(monkeypatch) -> None:
    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        raise requests.exceptions.ConnectionError('connection refused')

    monkeypatch.setattr(requests, 'get', mock_get)

    with pytest.raises(BackendQueryError, match='Could not connect to rotki backend'):
        request_api(base_url='http://backend/api/1', endpoint='ping', timeout=5)


def test_request_api_should_return_payload(monkeypatch) -> None:
    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        return MockResponse({'result': True, 'message': ''})

    monkeypatch.setattr(requests, 'get', mock_get)

    assert request_api(base_url='http://backend/api/1', endpoint='ping', timeout=5) == {
        'result': True,
        'message': '',
    }


def test_request_api_should_delegate_bearer_with_internal_proof(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    session_key = b'session-key'

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        captured.update(kwargs)
        return MockResponse({'result': True, 'message': ''})

    monkeypatch.setattr(requests, 'get', mock_get)
    monkeypatch.setattr(
        'rotkehlchen.mcp.backend.get_access_token',
        lambda: AccessToken(
            token='mcp-bearer',
            client_id='rotki-backend',
            scopes=['mcp'],
        ),
    )
    configure_backend(
        base_url='http://backend/api/1',
        timeout=5,
        session_key=session_key,
    )

    request_api(base_url='http://backend/api/1', endpoint='settings', timeout=5)

    assert captured['headers'] == {
        'Authorization': 'Bearer mcp-bearer',
        MCP_BACKEND_PROOF_HEADER: create_mcp_backend_proof(
            key=session_key,
            token='mcp-bearer',
        ),
    }


def test_request_api_should_post_json_body(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def mock_post(url: str, **kwargs: Any) -> MockResponse:
        captured['url'] = url
        captured['json'] = kwargs.get('json')
        return MockResponse({'result': {'entries': []}, 'message': ''})

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        raise AssertionError('POST request must not fall back to GET')

    monkeypatch.setattr(requests, 'post', mock_post)
    monkeypatch.setattr(requests, 'get', mock_get)

    assert request_api(
        base_url='http://backend/api/1',
        endpoint='history/events',
        timeout=5,
        json_data={'limit': 10},
        method='POST',
    ) == {'result': {'entries': []}, 'message': ''}
    assert captured['url'] == 'http://backend/api/1/history/events'
    assert captured['json'] == {'limit': 10}


def test_query_settings_should_return_main_currency(monkeypatch) -> None:
    monkeypatch.setattr(
        requests,
        'get',
        lambda url, **kwargs: MockResponse({'result': {'main_currency': 'EUR'}, 'message': ''}),
    )
    configure_backend(base_url='http://backend/api/1', timeout=5)

    assert query_settings()['main_currency'] == 'EUR'


def test_query_settings_should_reject_non_dict_result(monkeypatch) -> None:
    monkeypatch.setattr(
        requests,
        'get',
        lambda url, **kwargs: MockResponse({'result': True, 'message': ''}),
    )
    configure_backend(base_url='http://backend/api/1', timeout=5)

    with pytest.raises(BackendQueryError, match='unexpected settings response'):
        query_settings()


def test_historical_prices_should_always_send_only_cache_period(monkeypatch) -> None:
    """``only_cache_period`` is what confines the endpoint to rotki's stored prices. Without
    it the backend falls through to ``query_multiple_prices`` and hits remote oracles, which
    the MCP must never do on an agent's behalf.
    """
    captured: dict[str, Any] = {}

    def mock_post(url: str, **kwargs: Any) -> MockResponse:
        captured['json'] = kwargs.get('json')
        return MockResponse({'result': {'assets': {}, 'target_asset': 'EUR'}, 'message': ''})

    monkeypatch.setattr(requests, 'post', mock_post)
    configure_backend(base_url='http://backend/api/1', timeout=5)

    query_historical_prices(
        asset_timestamps=[('ETH', 1614556800)],
        target_asset='EUR',
        max_seconds_distance=3600,
    )
    assert captured['json'] == {
        'assets_timestamp': [('ETH', 1614556800)],
        'target_asset': 'EUR',
        'only_cache_period': 3600,
    }
