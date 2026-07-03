import asyncio
import selectors
from typing import Any

import pytest

from rotkehlchen.mcp import backend
from rotkehlchen.mcp.backend import BackendQueryError, configure_backend
from rotkehlchen.mcp.tools import assets


def test_query_asset_details_should_query_globaldb_assets(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    expected_result = {
        'entries': [{
            'identifier': 'eip155:1/erc20:0x123',
            'asset_type': 'evm token',
            'name': 'Test Token',
            'symbol': 'TEST',
            'decimals': 18,
        }],
        'entries_found': 1,
        'entries_total': 100,
        'entries_limit': -1,
    }

    def mock_request_api(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {'result': expected_result, 'message': ''}

    monkeypatch.setattr(backend, 'request_api', mock_request_api)
    configure_backend(base_url='http://backend/api/1', timeout=5)

    assert backend.query_asset_details(['eip155:1/erc20:0x123']) == expected_result
    assert captured == {
        'base_url': 'http://backend/api/1',
        'endpoint': 'assets/all',
        'timeout': 5,
        'json_data': {'identifiers': ['eip155:1/erc20:0x123']},
        'method': 'POST',
    }


def test_query_asset_details_should_require_an_identifier() -> None:
    with pytest.raises(ValueError, match='At least one asset identifier is required'):
        backend.query_asset_details([])


@pytest.mark.parametrize('result', [None, [], {}, {'entries': None}])
def test_query_asset_details_should_reject_unexpected_response(
        monkeypatch,
        result: Any,
) -> None:
    monkeypatch.setattr(
        backend,
        'request_api',
        lambda **kwargs: {'result': result, 'message': ''},
    )

    with pytest.raises(BackendQueryError, match='unexpected assets response'):
        backend.query_asset_details(['BTC'])


def test_get_asset_details_should_run_query_in_thread(monkeypatch) -> None:
    expected_result = {
        'entries': [{'identifier': 'BTC', 'name': 'Bitcoin', 'symbol': 'BTC'}],
        'entries_found': 1,
    }
    monkeypatch.setattr(assets, 'query_asset_details', lambda identifiers: expected_result)

    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    try:
        assert loop.run_until_complete(assets.get_asset_details(['BTC'])) == expected_result
    finally:
        loop.close()
