from collections.abc import Generator
from http import HTTPStatus
from typing import Any

import pytest
import requests

from rotkehlchen.mcp import premium
from rotkehlchen.mcp.backend import configure_backend


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


@pytest.fixture(autouse=True)
def reset_cache() -> Generator[None]:
    premium.reset_premium_cache()
    yield
    premium.reset_premium_cache()


def _mock_tier(monkeypatch, tier: str) -> list[str]:
    """Patch requests.get to return the given premium tier, tracking each call."""
    calls: list[str] = []

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        calls.append(url)
        return MockResponse({'result': {'current_tier': tier}, 'message': ''})

    monkeypatch.setattr(requests, 'get', mock_get)
    configure_backend(base_url='http://backend/api/1', timeout=5)
    return calls


@pytest.mark.parametrize('tier', ['Basic', 'Advanced'])
def test_has_mcp_access_should_be_true_for_basic_and_up(monkeypatch, tier: str) -> None:
    _mock_tier(monkeypatch, tier)
    assert premium.has_mcp_access() is True


@pytest.mark.parametrize('tier', ['Free', 'Supporter'])
def test_has_mcp_access_should_be_false_for_free_and_supporter(monkeypatch, tier: str) -> None:
    _mock_tier(monkeypatch, tier)
    assert premium.has_mcp_access() is False


def test_has_mcp_access_should_cache_result(monkeypatch) -> None:
    calls = _mock_tier(monkeypatch, 'Advanced')
    assert premium.has_mcp_access() is True
    assert premium.has_mcp_access() is True
    assert len(calls) == 1  # second call served from the cache, no extra backend hit


def test_premium_gate_should_allow_basic_backend(monkeypatch) -> None:
    _mock_tier(monkeypatch, 'Basic')
    assert premium.premium_gate() is None


@pytest.mark.parametrize('tier', ['Free', 'Supporter'])
def test_premium_gate_should_block_free_and_supporter(monkeypatch, tier: str) -> None:
    _mock_tier(monkeypatch, tier)
    error = premium.premium_gate()
    assert error is not None
    assert error['error'] == 'premium_required'
    assert error['upgrade_url'] == premium.UPGRADE_URL


def test_premium_gate_should_fail_closed_when_backend_unreachable(monkeypatch) -> None:
    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        raise requests.exceptions.ConnectionError('connection refused')

    monkeypatch.setattr(requests, 'get', mock_get)
    configure_backend(base_url='http://backend/api/1', timeout=5)

    error = premium.premium_gate()
    assert error is not None
    assert error['error'] == 'premium_check_failed'
    assert 'Could not verify rotki premium subscription' in error['message']
