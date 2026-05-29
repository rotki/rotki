import asyncio
from http import HTTPStatus
from typing import Any

import requests

from rotkehlchen.mcp.backend import configure_backend
from rotkehlchen.mcp.tools import info as info_tool


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


def test_info_should_return_backend_info(monkeypatch) -> None:
    def mock_get_info() -> dict[str, Any]:
        return {
            'mcp': {
                'version': '1.2.3',
            },
            'backend': {
                'connected': True,
                'unlocked': True,
                'url': 'http://127.0.0.1:4242/api/1',
                'message': None,
            },
        }

    monkeypatch.setattr(info_tool, 'get_info', mock_get_info)

    assert asyncio.run(info_tool.info()) == {
        'mcp': {
            'version': '1.2.3',
        },
        'backend': {
            'connected': True,
            'unlocked': True,
            'url': 'http://127.0.0.1:4242/api/1',
            'message': None,
        },
    }


def test_get_info_should_report_unlocked_backend(monkeypatch) -> None:
    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        if url.endswith('/ping'):
            return MockResponse({'result': True, 'message': ''})
        if url.endswith('/users'):
            return MockResponse({'result': {'alice': 'loggedin'}, 'message': ''})
        return MockResponse({
            'result': {'version': {'our_version': '1.2.3'}},
            'message': '',
        })

    monkeypatch.setattr(requests, 'get', mock_get)

    configure_backend(base_url='http://backend/api/1', timeout=5)
    result = info_tool.get_info()

    assert result['backend'] == {
        'url': 'http://backend/api/1',
        'connected': True,
        'unlocked': True,
        'message': None,
        'version': '1.2.3',
    }
    assert isinstance(result['mcp']['version'], str)


def test_get_info_should_report_locked_backend(monkeypatch) -> None:
    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        if url.endswith('/users'):
            return MockResponse({'result': {'alice': 'loggedout'}, 'message': ''})
        return MockResponse({'result': True, 'message': ''})

    monkeypatch.setattr(requests, 'get', mock_get)

    configure_backend(base_url='http://backend/api/1', timeout=5)
    result = info_tool.get_info()

    assert result['backend']['connected'] is True
    assert result['backend']['unlocked'] is False
    assert result['backend']['message'] == (
        'rotki backend is reachable but no user database is unlocked'
    )


def test_get_info_should_report_connection_failure(monkeypatch) -> None:
    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        raise requests.exceptions.ConnectionError('connection refused')

    monkeypatch.setattr(requests, 'get', mock_get)

    configure_backend(base_url='http://backend/api/1', timeout=5)
    result = info_tool.get_info()

    assert result['backend']['connected'] is False
    assert result['backend']['unlocked'] is False
    assert 'Could not connect to rotki backend' in str(result['backend']['message'])
