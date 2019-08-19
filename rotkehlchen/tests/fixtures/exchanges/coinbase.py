import pytest

from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockCoinbase(Coinbase):
    pass


@pytest.fixture(scope='session')
def coinbase(session_data_dir, session_inquirer, messages_aggregator):
    mock = MockCoinbase(
        api_key=make_api_key(),
        secret=make_api_secret(),
        user_directory=session_data_dir,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_coinbase(
        accounting_data_dir,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
):
    mock = MockCoinbase(
        api_key=make_api_key(),
        secret=make_api_secret(),
        user_directory=accounting_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
