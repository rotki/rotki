from http import HTTPStatus
from typing import Any

import pytest
import requests

from rotkehlchen.mcp.backend import (
    BackendQueryError,
    configure_backend,
    get_backend_config,
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
