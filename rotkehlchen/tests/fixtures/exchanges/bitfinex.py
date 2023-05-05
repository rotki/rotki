import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitfinex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


@pytest.fixture(name='bitfinex_api_key')
def fixture_bitfinex_api_key():
    return make_api_key()


@pytest.fixture(name='bitfinex_api_secret')
def fixture_bitfinex_api_secret():
    return make_api_secret()


@pytest.fixture()
def mock_bitfinex(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        bitfinex_api_key,
        bitfinex_api_secret,
):
    return create_test_bitfinex(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=bitfinex_api_key,
        secret=bitfinex_api_secret,
    )
