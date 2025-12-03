from http import HTTPStatus
from unittest.mock import _patch, patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import DAY_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.externalapis.routescan import ROUTESCAN_SUPPORTED_CHAINS, Routescan
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, Timestamp


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
