from typing import TYPE_CHECKING

import pytest

from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.tests.utils.exchanges import create_test_bitmex
from rotkehlchen.types import ApiKey, ApiSecret
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer

TEST_BITMEX_API_KEY = ApiKey('XY98JYVL15Zn-iU9f7OsJeVf')
TEST_BITMEX_API_SECRET = ApiSecret(b'671tM6f64bt6KhteDakj2uCCNBt7HhZVEE7H5x16Oy4zb1ag')


@pytest.fixture
def mock_bitmex(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
) -> Bitmex:
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    return create_test_bitmex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.fixture
def sandbox_bitmex(database: DBHandler, inquirer: Inquirer) -> Bitmex:  # pylint: disable=unused-argument
    bitmex = Bitmex(
        name='bitmex',
        api_key=TEST_BITMEX_API_KEY,
        secret=TEST_BITMEX_API_SECRET,
        database=database,
        msg_aggregator=MessagesAggregator(),
    )
    bitmex.uri = 'https://testnet.bitmex.com'
    return bitmex
