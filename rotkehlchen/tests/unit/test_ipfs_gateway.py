from unittest.mock import patch

import pytest

from rotkehlchen.errors.misc import IPFSRemoteError, RemoteError
from rotkehlchen.externalapis.ipfs import (
    DEFAULT_IPFS_GATEWAYS,
    IPFSGateway,
    normalize_ipfs_gateway_url,
)


def _fake_query_file(working: set[str]):
    """query_file replacement that records the urls asked and only serves the working gateways"""
    asked: list[str] = []

    def query_file(url: str, **_: object) -> dict[str, str]:
        asked.append(url)
        if any(url.startswith(x) for x in working):
            return {'url': url}
        raise RemoteError(f'File query for {url} failed with status code 429')

    return asked, query_file


def test_ipfs_gateway_order_and_fallback():
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


def test_ipfs_gateway_all_gateways_fail():
    """If no gateway serves the content a single error names every failure"""
    asked, query_file = _fake_query_file(working=set())
    with (
        patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file),
        pytest.raises(IPFSRemoteError) as exc_info,
    ):
        IPFSGateway(custom_gateway='https://my.node').query_json('cid')

    assert len(asked) == len(DEFAULT_IPFS_GATEWAYS) + 1  # the custom gateway plus the defaults
    assert all(x in str(exc_info.value) for x in asked)


@pytest.mark.parametrize(('url', 'expected'), [
    ('https://my.node', 'https://my.node/ipfs/'),
    ('https://my.node/', 'https://my.node/ipfs/'),
    (' http://localhost:8080/ipfs ', 'http://localhost:8080/ipfs/'),
    ('https://my.node/some/path/ipfs/', 'https://my.node/some/path/ipfs/'),
    ('https://my.node?token=secret', 'https://my.node/ipfs/?token=secret'),
    ('https://my.node/ipfs?a=1&b=2', 'https://my.node/ipfs/?a=1&b=2'),
])
def test_normalize_ipfs_gateway_url(url: str, expected: str):
    assert normalize_ipfs_gateway_url(url) == expected


@pytest.mark.parametrize('url', [
    'my.node',
    'ftp://my.node',
    'https://',
    'https://user:secret@my.node',
    'https://:secret@my.node',
    'https://my.node#secret',
    'https://my.node/ipfs;secret',
])
def test_normalize_ipfs_gateway_url_rejects_invalid(url: str):
    """Non http(s) urls, credentials, fragments and path params are refused without being echoed"""
    with pytest.raises(ValueError, match='IPFS gateway') as exc_info:
        normalize_ipfs_gateway_url(url)

    assert 'secret' not in str(exc_info.value)


def test_ipfs_gateway_query_is_sent_but_never_logged():
    """The cid goes into the path before the query, and the token is redacted from errors"""
    asked: list[str] = []

    def query_file(url: str, **_: object) -> dict[str, str]:
        asked.append(url)
        raise RemoteError(f'Failed to query file {url} due to: max retries')

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
