from typing import TYPE_CHECKING

import pytest

from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
)
from rotkehlchen.tests.utils.exchanges import create_test_binance

if TYPE_CHECKING:
    from rotkehlchen.locations.types import LocationIdentifier


@pytest.fixture(name='binance_location')
def fixture_binance_location() -> LocationIdentifier:
    return LOCATION_BINANCE


@pytest.fixture
def function_scope_binance(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        binance_location,
):
    return create_test_binance(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        location=binance_location,
    )
