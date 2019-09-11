import pytest

from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockCoinbase(Coinbase):
    pass


@pytest.fixture(scope='session')
def coinbase(session_database, session_inquirer, messages_aggregator):
    mock = MockCoinbase(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=session_database,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_coinbase(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
):
    mock = MockCoinbase(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
