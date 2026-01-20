import pytest

from rotkehlchen.exchanges.manager import ExchangeManager


@pytest.fixture(name='exchange_manager')
def fixture_exchange_manager(function_scope_messages_aggregator, database) -> ExchangeManager:
    exchange_manager = ExchangeManager(msg_aggregator=function_scope_messages_aggregator)
    exchange_manager.initialize_exchanges(exchange_credentials={}, database=database)
    return exchange_manager
