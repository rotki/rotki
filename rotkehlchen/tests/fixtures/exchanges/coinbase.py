from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import (
    create_test_coinbase,
    create_test_coinbaseprime,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.coinbase import Coinbase
    from rotkehlchen.exchanges.coinbaseprime import Coinbaseprime
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def function_scope_coinbase(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator: MessagesAggregator,
) -> Coinbase:
    return create_test_coinbase(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.fixture
def function_scope_coinbaseprime(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator: MessagesAggregator,
) -> Coinbaseprime:
    return create_test_coinbaseprime(
        database=database,
        passphrase='Rotki123!',
        msg_aggregator=function_scope_messages_aggregator,
    )
