from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitcoinde

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.bitcoinde import Bitcoinde
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def function_scope_bitcoinde(
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        database: DBHandler,
) -> Bitcoinde:
    return create_test_bitcoinde(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
