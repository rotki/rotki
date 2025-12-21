import warnings as test_warnings
from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.modules.eth2.utils import calculate_query_chunks
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now


def test_query_chunks_empty_list():
    """Test that one of the endpoints works with empty list"""
    assert calculate_query_chunks([]) == []


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_eth1_validator_indices_single(beaconchain):
    address = '0x2bCF6fE9F95Fe5eCec37f69dFE00Bfb4668ac35D'
    validators = beaconchain.get_eth1_address_validators(address=address)
    if len(validators) != 1:
        msg = (
            f'Eth1 address {address} has more than 1 validator. We have to amend the test '
            f'because this test is to check this endpoint works with a non-list return'
        )
        test_warnings.warn(UserWarning(msg))

    assert validators[0].index == 178585
    assert validators[0].public_key == '0xadefb3de3c892823aa8d389a4b9582f56f64463db2b72b4d77c515d268cf695f9047604371eb73d2a514c8f711ae7eba'  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_eth1_validator_indices_multiple(beaconchain):
    address = '0x3266F3546a1e5Dc6A15588f3324741A0E20a3B6c'
    validators = beaconchain.get_eth1_address_validators(address=address)

    expected_results = [
        (993, '0x90b2f65cb43d9cdb2279af9f76010d667b9d8d72e908f2515497a7102820ce6bb15302fe2b8dc082fce9718569344ad8'),  # noqa: E501
        (994, '0xb4610a24815f1874a12eba7ea9b77126ca16c0aa29a127ba14ba4ee179834f4feb0aa4497baaa50985ad748d15a286cf'),  # noqa: E501
        (995, '0xa96352b921bcc4b1a90a7aeb68739b6a5508079a63158ca84786241da247142173f9b38d553de899c1778de4f83e6c6c'),  # noqa: E501
        (996, '0x911cba78efe677a502a3995060e2389e2d16d03f989c87f1a0fdf82345a77dfd3b9476720825ea5f5a374bd386301b60'),  # noqa: E501
        (997, '0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35'),  # noqa: E501
        (998, '0x89da8cb17b203eefacc8346e1ee718a305b622028dc77913d3b26f2034f92693d305a630f45c76b781ef68cd4640253e'),  # noqa: E501
        (999, '0x930a90c7f0b00ce4c7d7994652f1e301753c084d5499de31abadb2e3913cba2eb4026de8d49ea35294db10119b83b2e1'),  # noqa: E501
        (1000, '0xb18e1737e1a1a76b8dff905ba7a4cb1ff5c526a4b7b0788188aade0488274c91e9c797e75f0f8452384ff53d44fad3df'),  # noqa: E501
        (1040, '0x976c5c76f3cbc10d22ac50c27f816b82d91192f6b6177857a89a0349fcecaa8301469ab1d303e381e630c591456e0e54'),  # noqa: E501
        (1041, '0x85a82370ef68f52209d3a07f5cca32b0bbe4d2d39574f39beab746d54e696831a02a95f3dcea25f1fba766bdb5048a09'),  # noqa: E501
        (1042, '0xb347f7421cec107e1cdf3ae9b6308c577fc6c1c254fa44552be97db3eccdac667dc6d6e5409f8e546c9dcbcef47c83f3'),  # noqa: E501
        (1043, '0x965f40c2a6f004d4457a89e7b49ea5d101367cd31c86836d6551ea504e55ee3e32aed8b2615ee1c13212db46fb411a7a'),  # noqa: E501
        (1044, '0x90d4b57b88eb613737c1bb2e79f8ed8f2abd1c5e31cea9aa741f16cb777716d2fc1cabf9e15d3c15edf8091533916eb5'),  # noqa: E501
        (1045, '0x92a5d445d10ce8d413c506a012ef92719ca230ab0fd4066e2968df8adb52bb112ee080a3267f282f09db94dc59a3ec77'),  # noqa: E501
        (1046, '0xb44383a9ce75b90cc8248bdd46d02a2a309117bbfdbe9fd05743def6d483549072c3285ae4953f48b1d17c9787697764'),  # noqa: E501
    ]
    for idx, validator in enumerate(validators):
        assert validator.index == expected_results[idx][0]
        assert validator.public_key == expected_results[idx][1]


@pytest.mark.freeze_time('2025-03-03 17:00:00 GMT')
def test_rate_limit(beaconchain: BeaconChain, freezer):
    """Tests the rate limit logic ensuring that we don't retry beaconchain calls
    if we are rate limited by them.
    """
    requests_made = 0

    def mock_session_get(url: str, **kwargs: dict[str, Any]) -> MockResponse:  # pylint: disable=unused-argument
        nonlocal requests_made
        requests_made += 1
        return MockResponse(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            headers={'retry-after': 1000},
            text='Too many requests',
        )

    with (
        patch.object(beaconchain.session, 'request', mock_session_get),
        pytest.raises(RemoteError),
    ):
        beaconchain._query(
            method='GET',
            module='execution',
            endpoint='produced',
            encoded_args='130,131',
        )

    assert beaconchain.ratelimited_until == Timestamp(ts_now() + 1000)
    with (  # if we query again we won't try to make a request
        patch.object(beaconchain.session, 'request', mock_session_get),
        pytest.raises(RemoteError),
    ):
        beaconchain._query(
            method='GET',
            module='execution',
            endpoint='produced',
            encoded_args='130,131',
        )

    assert requests_made == 1

    freezer.tick(1200)  # move the time. We should be able to query again
    with (
        patch.object(beaconchain.session, 'request', mock_session_get),
        pytest.raises(RemoteError),
    ):
        beaconchain._query(
            method='GET',
            module='execution',
            endpoint='produced',
            encoded_args='130,131',
        )

    assert beaconchain.ratelimited_until == Timestamp(ts_now() + 1000)
    assert requests_made == 2


@pytest.mark.freeze_time('2025-03-03 17:00:00 GMT')
def test_rate_limit_notification_throttling(beaconchain: BeaconChain, freezer):
    """Tests that rate limit notifications are throttled to once every 5 minutes."""
    # Track notification calls
    notification_calls = []
    original_add_error = beaconchain.msg_aggregator.add_error
    
    def mock_add_error(msg: str) -> None:
        notification_calls.append(msg)
        original_add_error(msg)
    
    beaconchain.msg_aggregator.add_error = mock_add_error
    
    # First rate limit error - should send notification
    error_msg = 'Beaconcha.in is rate limited until 2025-03-03T17:10:00Z. Check logs for more details'
    beaconchain._maybe_notify_rate_limit(error_msg)
    assert len(notification_calls) == 1
    assert notification_calls[0] == f'Rate limited by beaconcha.in: {error_msg}'
    assert beaconchain.last_rate_limit_notification_ts == Timestamp(ts_now())
    
    # Second rate limit error within 5 minutes - should NOT send notification
    freezer.tick(60)  # 1 minute later
    beaconchain._maybe_notify_rate_limit(error_msg)
    assert len(notification_calls) == 1  # Still only 1 notification
    
    # Third rate limit error still within 5 minutes - should NOT send notification
    freezer.tick(120)  # 2 more minutes (3 minutes total)
    beaconchain._maybe_notify_rate_limit(error_msg)
    assert len(notification_calls) == 1  # Still only 1 notification
    
    # After 5 minutes (300 seconds) - should send notification again
    freezer.tick(180)  # 3 more minutes (6 minutes total from start)
    beaconchain._maybe_notify_rate_limit(error_msg)
    assert len(notification_calls) == 2  # Now 2 notifications
    assert notification_calls[1] == f'Rate limited by beaconcha.in: {error_msg}'
    
    # Restore original method
    beaconchain.msg_aggregator.add_error = original_add_error
