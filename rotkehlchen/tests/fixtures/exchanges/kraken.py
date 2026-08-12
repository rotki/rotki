from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_kraken

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.tests.utils.kraken import MockKraken
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='kraken')
def fixture_kraken(
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        database: DBHandler,
) -> MockKraken:
    return create_test_kraken(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
