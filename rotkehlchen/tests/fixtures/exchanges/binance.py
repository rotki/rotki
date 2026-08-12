from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_binance
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.binance import Binance
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='binance_location')
def fixture_binance_location() -> Location:
    return Location.BINANCE


@pytest.fixture
def function_scope_binance(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        binance_location: Location,
) -> Binance:
    return create_test_binance(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        location=binance_location,
    )
