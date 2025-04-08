import pytest

from rotkehlchen.tests.utils.exchanges import create_test_kucoin
from rotkehlchen.tests.utils.factories import (
    make_api_key,
    make_api_secret,
    make_random_uppercasenumeric_string,
)


@pytest.fixture(name='kucoin_api_key')
def fixture_kucoin_api_key():
    return make_api_key()


@pytest.fixture(name='kucoin_api_secret')
def fixture_kucoin_api_secret():
    return make_api_secret()


@pytest.fixture(name='kucoin_passphrase')
def fixture_kucoin_passphrase():
    return make_random_uppercasenumeric_string(size=6)


@pytest.fixture
def mock_kucoin(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        kucoin_api_key,
        kucoin_api_secret,
        kucoin_passphrase,
):
    return create_test_kucoin(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=kucoin_api_key,
        secret=kucoin_api_secret,
        passphrase=kucoin_passphrase,
    )
