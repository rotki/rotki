from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_cryptocom
from rotkehlchen.types import ApiKey, ApiSecret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.cryptocom import Cryptocom
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='mock_cryptocom')
def fixture_cryptocom(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
) -> Cryptocom:
    return create_test_cryptocom(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=ApiKey('ddddddd'),
        secret=ApiSecret(b'secret'),
        name='MockCryptocom',
    )
