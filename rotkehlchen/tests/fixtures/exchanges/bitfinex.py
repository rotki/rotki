from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitfinex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.bitfinex import Bitfinex
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ApiKey, ApiSecret
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='bitfinex_api_key')
def fixture_bitfinex_api_key() -> ApiKey:
    return make_api_key()


@pytest.fixture(name='bitfinex_api_secret')
def fixture_bitfinex_api_secret() -> ApiSecret:
    return make_api_secret()


@pytest.fixture
def mock_bitfinex(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        bitfinex_api_key: ApiKey,
        bitfinex_api_secret: ApiSecret,
) -> Bitfinex:
    return create_test_bitfinex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=bitfinex_api_key,
        secret=bitfinex_api_secret,
    )
