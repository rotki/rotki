import pytest

from rotkehlchen.exchanges.kucoin import Kucoin
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


@pytest.fixture(name='kucoin_sandbox_api_key')
def fixture_kucoin_sandbox_api_key():
    # General permission (aka read-only)
    return '6023e471a2644e00063aa8bb'


@pytest.fixture(name='kucoin_sandbox_api_secret')
def fixture_kucoin_sandbox_api_secret():
    # General permission (aka read-only)
    return b'3a817593-eceb-47f3-90d4-26de79de588a'


@pytest.fixture(name='kucoin_sandbox_passphrase')
def fixture_kucoin_sandbox_passphrase():
    # General permission (aka read-only)
    return 'rotkidev'


@pytest.fixture(name='kucoin_sandbox_base_uri')
def fixture_kucoin_sandbox_base_uri():
    return 'https://openapi-sandbox.kucoin.com'


@pytest.fixture
def sandbox_kuckoin(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        kucoin_sandbox_api_key,
        kucoin_sandbox_api_secret,
        kucoin_sandbox_passphrase,
        kucoin_sandbox_base_uri,
):
    kucoin = Kucoin(
        api_key=kucoin_sandbox_api_key,
        secret=kucoin_sandbox_api_secret,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        passphrase=kucoin_sandbox_passphrase,
        base_uri=kucoin_sandbox_base_uri,
    )
    return kucoin
