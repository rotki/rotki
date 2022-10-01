import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bittrex


@pytest.fixture(scope='session')
def bittrex(
        session_database,
        session_inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
):
    return create_test_bittrex(database=session_database, msg_aggregator=messages_aggregator)
