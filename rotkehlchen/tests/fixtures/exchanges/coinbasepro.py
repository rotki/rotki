import pytest

from rotkehlchen.tests.utils.exchanges import create_test_coinbasepro


@pytest.fixture(scope='session', name='coinbasepro_passphrase')
def fixture_coinbasepro_passphrase():
    return 'supersecretpassphrase'


@pytest.fixture(scope='session')
def coinbasepro(
        session_database,
        session_inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
        coinbasepro_passphrase,
):
    return create_test_coinbasepro(
        database=session_database,
        msg_aggregator=messages_aggregator,
        passphrase=coinbasepro_passphrase,
    )


@pytest.fixture(scope='function')
def function_scope_coinbasepro(
        database,
        inquirer,  # pylint: disable=unused-argument,
        function_scope_messages_aggregator,
        coinbasepro_passphrase,
):
    return create_test_coinbasepro(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        passphrase=coinbasepro_passphrase,
    )
