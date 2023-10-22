import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bittrex


@pytest.fixture(name='bittrex')
def fixture_bittrex(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    return create_test_bittrex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
