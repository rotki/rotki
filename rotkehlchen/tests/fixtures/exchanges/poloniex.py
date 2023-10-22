import pytest

from rotkehlchen.tests.utils.exchanges import create_test_poloniex


@pytest.fixture(name='poloniex')
def fixture_poloniex(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    return create_test_poloniex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
