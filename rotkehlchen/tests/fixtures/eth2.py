import pytest

from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.mock import patch_eth2_requests


@pytest.fixture(name='eth2_mock_data')
def fixture_eth2_mock_data():
    return {}


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
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)
    eth2 = Eth2(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        premium=premium,
        msg_aggregator=messages_aggregator,
        beaconchain=beaconchain,
    )
    if network_mocking is True:
        with patch_eth2_requests(eth2, eth2_mock_data):
            yield eth2
    else:
        yield eth2
