import pytest

from rotkehlchen.tests.utils.exchanges import create_test_binance


@pytest.fixture
def function_scope_binance(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    binance = create_test_binance(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return binance
