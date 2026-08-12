from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitstamp
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.bitstamp import Bitstamp
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ApiKey, ApiSecret
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='bitstamp_api_key')
def fixture_bitstamp_api_key() -> ApiKey:
    return make_api_key()


@pytest.fixture(name='bitstamp_api_secret')
def fixture_bitstamp_api_secret() -> ApiSecret:
    return make_api_secret()


@pytest.fixture
def mock_bitstamp(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        bitstamp_api_key: ApiKey,
        bitstamp_api_secret: ApiSecret,
) -> Bitstamp:
    return create_test_bitstamp(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=bitstamp_api_key,
        secret=bitstamp_api_secret,
    )
