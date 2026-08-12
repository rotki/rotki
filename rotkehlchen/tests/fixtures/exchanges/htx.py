from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_htx

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.htx import Htx
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='htx_exchange')
def function_scope_htx(
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        database: DBHandler,
) -> Htx:
    return create_test_htx(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
