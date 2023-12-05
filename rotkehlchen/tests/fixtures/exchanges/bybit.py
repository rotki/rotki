import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bybit


@pytest.fixture(name='bybit_exchange')
def function_scope_bybit(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_bybit(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
