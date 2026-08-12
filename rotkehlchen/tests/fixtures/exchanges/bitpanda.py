from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitpanda
from rotkehlchen.tests.utils.factories import make_api_key

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.bitpanda import Bitpanda
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ApiKey
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='bitpanda_api_key')
def fixture_bitpanda_api_key() -> ApiKey:
    return make_api_key()


@pytest.fixture
def mock_bitpanda(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        bitpanda_api_key: ApiKey,
) -> Bitpanda:
    return create_test_bitpanda(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=bitpanda_api_key,
    )
