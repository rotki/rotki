import pytest

from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.mock import patch_eth2_requests


@pytest.fixture(name='eth2_mock_data')
def fixture_eth2_mock_data():
    return {}


@pytest.fixture(name='beacon_rpc_endpoint')
def fixture_beacon_rpc_endpoint():
    return None


@pytest.fixture(name='eth2')
def fixture_eth2(
        ethereum_inquirer,
        database,
        messages_aggregator,
        start_with_valid_premium,
        rotki_premium_credentials,
        beaconchain,
        network_mocking,
        eth2_mock_data,
        username,
        beacon_rpc_endpoint,
        inquirer,  # pylint: disable=unused-argument
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(
            credentials=rotki_premium_credentials,
            username=username,
            msg_aggregator=messages_aggregator,
            db=database,
        )
    eth2 = Eth2(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        premium=premium,
        msg_aggregator=messages_aggregator,
        beaconchain=beaconchain,
        beacon_rpc_endpoint=beacon_rpc_endpoint,
    )
    if network_mocking is True:
        with patch_eth2_requests(eth2, eth2_mock_data):
            yield eth2
    else:
        yield eth2
