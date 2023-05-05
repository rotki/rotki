import pytest

from rotkehlchen.tests.utils.exchanges import create_test_binance
from rotkehlchen.types import Location


@pytest.fixture(name='binance_location')
def fixture_binance_location() -> Location:
    return Location.BINANCE


@pytest.fixture()
def function_scope_binance(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        binance_location,
):
    binance = create_test_binance(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        location=binance_location,
    )
    return binance
