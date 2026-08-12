from typing import TYPE_CHECKING

import pytest

from rotkehlchen.exchanges.manager import ExchangeManager

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='exchange_manager')
def fixture_exchange_manager(
        function_scope_messages_aggregator: MessagesAggregator,
        database: DBHandler,
) -> ExchangeManager:
    exchange_manager = ExchangeManager(msg_aggregator=function_scope_messages_aggregator)
    exchange_manager.initialize_exchanges(exchange_credentials={}, database=database)
    return exchange_manager
