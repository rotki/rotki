import pytest

from rotkehlchen.tests.utils.exchanges import create_test_poloniex


@pytest.fixture(scope='session')
def poloniex(
        session_database,
        session_inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
):
    return create_test_poloniex(
        database=session_database,
        msg_aggregator=messages_aggregator,
    )


@pytest.fixture()
def function_scope_poloniex(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    return create_test_poloniex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
