import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitstamp


@pytest.fixture
def mock_bitstamp(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    return create_test_bitstamp(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
