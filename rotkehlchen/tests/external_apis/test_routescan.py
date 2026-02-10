from http import HTTPStatus
from unittest.mock import _patch, patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import DAY_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi, HasChainActivity
from rotkehlchen.externalapis.routescan import ROUTESCAN_SUPPORTED_CHAINS, Routescan
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, Timestamp, deserialize_evm_tx_hash


@pytest.fixture(name='routescan')
def fixture_routescan(database, messages_aggregator):
    return Routescan(
        database=database,
        msg_aggregator=messages_aggregator,
    )


def test_routescan_url_formatting(routescan: Routescan) -> None:
    formatted_url = routescan._get_url(chain_id=ChainID.ETHEREUM)
    assert formatted_url == 'https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api'

    formatted_url = routescan._get_url(chain_id=ChainID.OPTIMISM)
    assert formatted_url == 'https://api.routescan.io/v2/network/mainnet/evm/10/etherscan/api'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_routescan_has_activity(routescan: Routescan) -> None:
    for chain in ROUTESCAN_SUPPORTED_CHAINS:
        assert routescan.has_activity(
            chain_id=chain,
            account=string_to_evm_address('0x56a1A34F0d33788ebA53e2706854A37A5F275536'),
        ) == HasChainActivity.TRANSACTIONS  # nicholasyoder.eth - has txs in all chains supported by routescan  # noqa: E501
        assert routescan.has_activity(
            chain_id=chain,
            account=string_to_evm_address('0x84e8EE8911c147755bD70084b6b4D1a5A8351476'),
        ) == HasChainActivity.NONE  # random address with no activity


def test_routescan_rate_limits(routescan: Routescan) -> None:
    """Test that we properly handle rate limits from routescan."""

    def _make_rate_limit_patch(
            minute_remaining: int = 300,
            minute_reset: int = 60,
            day_remaining: int = 10000,
            day_reset: int = DAY_IN_SECONDS,
    ) -> _patch:
        return patch.object(routescan.session, 'get', return_value=MockResponse(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            text='',
            headers={
                'x-ratelimit-rpm-limit': '300',
                'x-ratelimit-rpm-remaining': str(minute_remaining),
                'x-ratelimit-rpm-reset': str(minute_reset),
                'x-ratelimit-rpd-limit': '100000',
                'x-ratelimit-rpd-remaining': str(day_remaining),
                'x-ratelimit-rpd-reset': str(day_reset),
            },
        ))

    for request_patch, expected_msg in ((
        _make_rate_limit_patch(minute_remaining=0, minute_reset=30),
        'Per minute rate limit reached for Routescan on Ethereum with 30 seconds until reset',
    ), (
        _make_rate_limit_patch(day_remaining=0, day_reset=4500),
        'Daily rate limit reached for Routescan on Ethereum with 4500 seconds until reset',
    ), (
        _make_rate_limit_patch(),
        'Unexpected rate limit response from Routescan on Ethereum. Check logs for details.',
    )):
        with (
            request_patch,
            pytest.raises(RemoteError, match=expected_msg),
        ):
            routescan.get_blocknumber_by_time(chain_id=ChainID.ETHEREUM, ts=Timestamp(1700000000))


@pytest.mark.parametrize('action', ['txlist', None])
def test_routescan_account_queries_use_explicit_pagination(
        routescan: Routescan,
        action: str | None,
) -> None:
    """RouteScan account endpoints should always include explicit page and offset."""
    with patch.object(EtherscanLikeApi, '_query', return_value=[]) as query_mock:
        account = string_to_evm_address('0x56a1A34F0d33788ebA53e2706854A37A5F275536')
        if action is None:
            list(routescan.get_token_transaction_hashes(
                chain_id=ChainID.ETHEREUM,
                account=account,
            ))
        else:
            list(routescan.get_transactions(
                chain_id=ChainID.ETHEREUM,
                account=account,
                action='txlist',
            ))

    query_options = query_mock.call_args.kwargs['options']
    assert query_options['page'] == '1'
    assert query_options['offset'] == str(routescan.pagination_limit)


def test_routescan_internal_by_txhash_uses_lower_offset(routescan: Routescan) -> None:
    with patch.object(EtherscanLikeApi, '_query', return_value=[]) as query_mock:
        list(routescan.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=None,
            action='txlistinternal',
            period_or_hash=deserialize_evm_tx_hash(
                '0x2cb9dcf83b3fd1bbbec4cd5f8d0b688bfc3f6aadd99081f28eaccafcd26c4243',
            ),
        ))

    query_options = query_mock.call_args.kwargs['options']
    assert query_options['page'] == '1'
    assert query_options['offset'] == '100'


def test_routescan_maybe_paginate_uses_request_offset(routescan: Routescan) -> None:
    result = [{'blockNumber': str(i)} for i in range(100)]
    options = {'offset': '100'}

    new_options = routescan._maybe_paginate(result=result, options=options)

    assert new_options is not None
    assert new_options['startblock'] == '99'
