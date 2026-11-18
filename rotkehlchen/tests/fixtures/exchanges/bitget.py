import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitget


@pytest.fixture(name='bitget_exchange')
def fixture_bitget_exchange(database, function_scope_messages_aggregator):
    return create_test_bitget(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
