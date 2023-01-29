import pytest

from rotkehlchen.tests.utils.exchanges import create_test_coinbase


@pytest.fixture()
def function_scope_coinbase(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
):
    mock = create_test_coinbase(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
