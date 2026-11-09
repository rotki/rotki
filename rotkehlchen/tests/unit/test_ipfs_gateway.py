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


def test_ipfs_gateway_falls_through_to_next_gateway():
    """A failing or rate limited gateway is skipped, and the first one that serves is used"""
    asked, query_file = _fake_query_file(working={DEFAULT_IPFS_GATEWAYS[2]})
    with patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file):
        result = IPFSGateway().query_json('cid')

    assert result == {'url': f'{DEFAULT_IPFS_GATEWAYS[2]}cid'}
    assert asked == [f'{x}cid' for x in DEFAULT_IPFS_GATEWAYS[:3]]  # stops at the first success


def test_ipfs_gateway_custom_gateway_is_tried_first():
    asked, query_file = _fake_query_file(working={'https://my.node/ipfs/'})
    with patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file):
        IPFSGateway(custom_gateway='https://my.node').query_json('cid')

    assert asked == ['https://my.node/ipfs/cid']


def test_ipfs_gateway_custom_gateway_falls_back_to_defaults():
    asked, query_file = _fake_query_file(working={DEFAULT_IPFS_GATEWAYS[0]})
    with patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file):
        IPFSGateway(custom_gateway='https://my.node/ipfs').query_json('cid')

    assert asked == ['https://my.node/ipfs/cid', f'{DEFAULT_IPFS_GATEWAYS[0]}cid']


def test_ipfs_gateway_does_not_repeat_a_custom_gateway_that_is_a_default():
    assert IPFSGateway(custom_gateway=DEFAULT_IPFS_GATEWAYS[1]).gateways == (
        DEFAULT_IPFS_GATEWAYS[1],
        *(x for x in DEFAULT_IPFS_GATEWAYS if x != DEFAULT_IPFS_GATEWAYS[1]),
    )


def test_ipfs_gateway_all_gateways_fail():
    """If no gateway serves the content a single RemoteError names every failure"""
    asked, query_file = _fake_query_file(working=set())
    with (
        patch('rotkehlchen.externalapis.ipfs.query_file', side_effect=query_file),
        pytest.raises(IPFSRemoteError) as exc_info,
    ):
        IPFSGateway(custom_gateway='https://my.node').query_json('cid')

    assert len(asked) == len(DEFAULT_IPFS_GATEWAYS) + 1
    assert all(x in str(exc_info.value) for x in asked)


@pytest.mark.parametrize(('url', 'expected'), [
    ('https://my.node', 'https://my.node/ipfs/'),
    ('https://my.node/', 'https://my.node/ipfs/'),
    (' http://localhost:8080/ipfs ', 'http://localhost:8080/ipfs/'),
    ('https://my.node/some/path/ipfs/', 'https://my.node/some/path/ipfs/'),
])
def test_normalize_ipfs_gateway_url(url: str, expected: str):
    assert normalize_ipfs_gateway_url(url) == expected


@pytest.mark.parametrize('url', ['my.node', 'ftp://my.node', 'https://', 'ipfs://cid'])
def test_normalize_ipfs_gateway_url_rejects_non_http(url: str):
    with pytest.raises(ValueError, match='must be an http'):
        normalize_ipfs_gateway_url(url)


@pytest.mark.parametrize('userinfo', ['user:secret', 'user', ':secret', ''])
def test_ipfs_gateway_rejects_credentials(userinfo: str) -> None:
    with pytest.raises(ValueError, match='credentials') as exc_info:
        IPFSGateway(custom_gateway=f'https://{userinfo}@gateway.example')

    assert 'secret' not in str(exc_info.value)
