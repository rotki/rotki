import pytest

from rotkehlchen.tests.utils.exchanges import create_test_ftx


@pytest.fixture()
def mock_ftx(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
):
    mock = create_test_ftx(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
