import pytest

from rotkehlchen.chain.ethereum.modules.eth2 import Eth2
from rotkehlchen.premium.premium import Premium


@pytest.fixture(name='eth2')
def fixture_eth2(
        ethereum_manager,
        database,
        messages_aggregator,
        start_with_valid_premium,
        rotki_premium_credentials,
        beaconchain,
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)
    return Eth2(
        ethereum_manager=ethereum_manager,
        database=database,
        premium=premium,
        msg_aggregator=messages_aggregator,
        beaconchain=beaconchain,
    )
