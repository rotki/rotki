import pytest

from rotkehlchen.tests.utils.exchanges import create_test_kraken


@pytest.fixture(scope='session')
def kraken(
        session_inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
        session_database,
):
    return create_test_kraken(
        database=session_database,
        msg_aggregator=messages_aggregator,
    )


@pytest.fixture()
def function_scope_kraken(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_kraken(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
