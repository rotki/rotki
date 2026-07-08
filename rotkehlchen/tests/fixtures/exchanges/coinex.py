import pytest

from rotkehlchen.tests.utils.exchanges import create_test_coinex


@pytest.fixture(name='coinex_exchange')
def function_scope_coinex(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_coinex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
