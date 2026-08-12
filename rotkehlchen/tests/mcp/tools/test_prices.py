import asyncio
import selectors
from typing import Any

import pytest

from rotkehlchen.mcp import backend
from rotkehlchen.mcp.backend import BackendQueryError, configure_backend
from rotkehlchen.mcp.tools import prices


def test_query_historical_prices_should_query_cached_prices(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    expected_result = {
        'assets': {
            'BTC': {'1579543935': '30000'},
            'ETH': {'1579543935': '1400'},
        },
        'target_asset': 'USD',
    }

    def mock_request_api(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {'result': expected_result, 'message': ''}

    monkeypatch.setattr(backend, 'request_api', mock_request_api)
    configure_backend(base_url='http://backend/api/1', timeout=5)
    asset_timestamps = [('BTC', 1579543935), ('ETH', 1579543935)]

    assert backend.query_historical_prices(
        asset_timestamps=asset_timestamps,
        target_asset='USD',
        max_seconds_distance=1000,
    ) == expected_result
    assert captured == {
        'base_url': 'http://backend/api/1',
        'endpoint': 'assets/prices/historical',
        'timeout': 5,
        'json_data': {
            'assets_timestamp': asset_timestamps,
            'target_asset': 'USD',
            'only_cache_period': 1000,
        },
        'method': 'POST',
    }


def test_query_historical_prices_should_validate_arguments() -> None:
    with pytest.raises(ValueError, match='At least one asset and timestamp pair is required'):
        backend.query_historical_prices(
            asset_timestamps=[],
            target_asset='USD',
            max_seconds_distance=1000,
        )

    with pytest.raises(ValueError, match='Maximum seconds distance must be positive'):
        backend.query_historical_prices(
            asset_timestamps=[('BTC', 1579543935)],
            target_asset='USD',
            max_seconds_distance=0,
        )


@pytest.mark.parametrize(
    'result',
    [None, [], {}, {'assets': None, 'target_asset': 'USD'}, {'assets': {}, 'target_asset': None}],
)
def test_query_historical_prices_should_reject_unexpected_response(
        monkeypatch: pytest.MonkeyPatch,
        result: Any,
) -> None:
    monkeypatch.setattr(
        backend,
        'request_api',
        lambda **kwargs: {'result': result, 'message': ''},
    )

    with pytest.raises(BackendQueryError, match='unexpected historical prices response'):
        backend.query_historical_prices(
            asset_timestamps=[('BTC', 1579543935)],
            target_asset='USD',
            max_seconds_distance=1000,
        )


def test_get_historical_prices_should_run_query_in_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_result = {
        'assets': {'BTC': {'1579543935': '30000'}},
        'target_asset': 'USD',
    }
    monkeypatch.setattr(prices, 'query_historical_prices', lambda **kwargs: expected_result)

    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    try:
        assert loop.run_until_complete(prices.get_historical_prices(
            asset_timestamps=[('BTC', 1579543935)],
            target_asset='USD',
            max_seconds_distance=1000,
        )) == expected_result
    finally:
        loop.close()
