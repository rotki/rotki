import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitvavo


@pytest.fixture(name='bitvavo_exchange')
def function_scope_bitvavo(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_bitvavo(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
