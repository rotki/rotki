import pytest

from rotkehlchen.tests.utils.exchanges import create_test_kraken


@pytest.fixture(name='kraken')
def fixture_kraken(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_kraken(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
