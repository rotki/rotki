from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_iconomi

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.iconomi import Iconomi
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def function_scope_iconomi(
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        database: DBHandler,
) -> Iconomi:
    return create_test_iconomi(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
