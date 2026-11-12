import socket
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import IPFSRemoteError, RemoteError
from rotkehlchen.externalapis.ipfs import (
    DEFAULT_IPFS_GATEWAYS,
    IPFSGateway,
    normalize_ipfs_gateway_url,
    redact_ipfs_gateway_url,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _fake_query_file(working: set[str]) -> tuple[list[str], Callable[..., dict[str, str]]]:
    """query_file replacement that records the urls asked and only serves the working gateways"""
    asked: list[str] = []

    def query_file(url: str, **_: object) -> dict[str, str]:
        asked.append(url)
        if any(url.startswith(x) for x in working):
            return {'url': url}
        raise RemoteError(
            f'File query for {url} failed with status code 429',
            cause=FailureCause.RATE_LIMITED,
        )

    return asked, query_file


def test_ipfs_gateway_order_and_fallback() -> None:
    """The custom gateway is tried first, failing ones are skipped and the first to serve wins"""
    asked, query_file = _fake_query_file(working={DEFAULT_IPFS_GATEWAYS[1]})
    with patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file):
        result = IPFSGateway(custom_gateway='https://my.node').query_json('cid')

    assert result == {'url': f'{DEFAULT_IPFS_GATEWAYS[1]}cid'}
    assert asked == [
        'https://my.node/ipfs/cid',
        f'{DEFAULT_IPFS_GATEWAYS[0]}cid',
        f'{DEFAULT_IPFS_GATEWAYS[1]}cid',  # stops at the first success
    ]


def test_ipfs_gateway_all_gateways_fail() -> None:
    """If no gateway serves the content a single error names every failure"""
    asked, query_file = _fake_query_file(working=set())
    with (
        patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file),
        pytest.raises(IPFSRemoteError) as exc_info,
    ):
        IPFSGateway(custom_gateway='https://my.node').query_json('cid')

    assert len(asked) == len(DEFAULT_IPFS_GATEWAYS) + 1  # the custom gateway plus the defaults
    assert all(x in str(exc_info.value) for x in asked)
    # every gateway was rate limited, so a later retry may succeed
    assert exc_info.value.cause == FailureCause.RATE_LIMITED


@pytest.mark.parametrize(('url', 'expected'), [
    ('https://my.node', 'https://my.node/ipfs/'),
    ('https://my.node/', 'https://my.node/ipfs/'),
    (' http://localhost:8080/ipfs ', 'http://localhost:8080/ipfs/'),
    ('https://my.node/some/path/ipfs/', 'https://my.node/some/path/ipfs/'),
    ('https://my.node?token=secret', 'https://my.node/ipfs/?token=secret'),
    ('https://my.node/ipfs?a=1&b=2', 'https://my.node/ipfs/?a=1&b=2'),
    ('https://my.node?token=s%20e%2Fc', 'https://my.node/ipfs/?token=s%20e%2Fc'),
])
def test_normalize_ipfs_gateway_url(url: str, expected: str) -> None:
    assert normalize_ipfs_gateway_url(url) == expected


@pytest.mark.parametrize('url', [
    'my.node',
    'ftp://my.node',
    'https://',
    'https://user:secret@my.node',
    'https://:secret@my.node',
    'https://my.node#secret',
    'https://my.node/ipfs;secret',
    # queries that requests would send in another form than the one redacted from errors
    'https://my.node?token=sec ret"x',
    'https://my.node?token=secr%2ft',
    'https://my.node?token=secr%74',
    'https://my.node?token=secrét',
])
def test_normalize_ipfs_gateway_url_rejects_invalid(url: str) -> None:
    """Non http(s) urls, credentials, fragments, path params and queries that are not
    in canonical percent-encoded form are refused without being echoed"""
    with pytest.raises(ValueError, match='IPFS gateway') as exc_info:
        normalize_ipfs_gateway_url(url)

    assert 'secr' not in str(exc_info.value)


@pytest.mark.parametrize(('url', 'expected'), [
    ('', ''),
    ('https://my.node/ipfs/', 'https://my.node/ipfs/'),
    (' https://my.node/ipfs?token=secret ', 'https://my.node/ipfs'),
])
def test_redact_ipfs_gateway_url(url: str, expected: str) -> None:
    assert redact_ipfs_gateway_url(url) == expected


def test_ipfs_gateway_query_is_sent_but_never_logged() -> None:
    """The cid goes into the path before the query, and the token is redacted from errors"""
    asked: list[str] = []

    def query_file(url: str, **_: object) -> dict[str, str]:
        asked.append(url)
        raise RemoteError(
            f'Failed to query file {url} due to: max retries',
            cause=FailureCause.NETWORK,
        )

    with (
        patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file),
        patch('rotkehlchen.externalapis.ipfs.log') as mock_log,
        pytest.raises(IPFSRemoteError) as exc_info,
    ):
        IPFSGateway(custom_gateway='https://my.node?token=secret').query_json('cid')

    assert asked[0] == 'https://my.node/ipfs/cid?token=secret'
    assert 'secret' not in str(exc_info.value)
    assert 'secret' not in str(mock_log.warning.call_args_list)
    assert 'https://my.node/ipfs/' in str(exc_info.value)


def test_ipfs_gateway_query_redacted_from_real_connection_error() -> None:
    """The connection error of requests holds the url as sent, which must match the query
    that is redacted. Uses a closed local port so the request fails without the network."""
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]

    with (
        patch('rotkehlchen.externalapis.ipfs.DEFAULT_IPFS_GATEWAYS', ()),
        patch('rotkehlchen.externalapis.ipfs.log') as mock_log,
        pytest.raises(IPFSRemoteError) as exc_info,
    ):
        IPFSGateway(
            custom_gateway=f'http://127.0.0.1:{port}/ipfs?token=zqx%20jkw%22vq',
        ).query_json('bafyCID')

    assert '/ipfs/bafyCID?<redacted>' in (error := str(exc_info.value))  # the url as sent
    assert 'zqx' not in error
    assert 'zqx' not in str(mock_log.warning.call_args_list)
