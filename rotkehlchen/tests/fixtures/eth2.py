from typing import TYPE_CHECKING, Any

import pytest

from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
from rotkehlchen.tests.utils.mock import patch_eth2_requests

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(name='eth2_mock_data')
def fixture_eth2_mock_data() -> dict[str, Any]:
    return {}


@pytest.fixture(name='beacon_rpc_endpoint')
def fixture_beacon_rpc_endpoint() -> None:
    return None


@pytest.fixture(name='eth2')
def fixture_eth2(
        ethereum_inquirer: Any,
        database: Any,
        messages_aggregator: Any,
        start_with_valid_premium: bool,
        rotki_premium_object: Any,
        beaconchain: Any,
        network_mocking: bool,
        eth2_mock_data: dict[str, Any],
        beacon_rpc_endpoint: Any,
        inquirer: Any,  # pylint: disable=unused-argument
) -> Generator[Eth2]:
    premium = rotki_premium_object if start_with_valid_premium else None
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
