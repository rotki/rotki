import pytest

from rotkehlchen.exchanges.coinbasepro import Coinbasepro
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockCoinbasepro(Coinbasepro):
    pass


@pytest.fixture(scope='session')
def coinbasepro_passphrase():
    return 'supersecretpassphrase'


@pytest.fixture(scope='session')
def coinbasepro(
        session_database,
        session_inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
        coinbasepro_passphrase,
):
    mock = MockCoinbasepro(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=session_database,
        msg_aggregator=messages_aggregator,
        passphrase=coinbasepro_passphrase,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_coinbasepro(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
        coinbasepro_passphrase,
):
    mock = MockCoinbasepro(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        passphrase=coinbasepro_passphrase,
    )
    return mock
