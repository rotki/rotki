import pytest

from rotkehlchen.exchanges.krakenfutures import Krakenfutures
from rotkehlchen.tests.utils.exchanges import create_test_kraken

DEMO_KRAKEN_FUTURES_API_KEY = 'QjqMVj9JlFgU6OWQBJ07gTcc6k14coxcT1CsjE31AujndTdPRlHcpxCt'
DEMO_KRAKEN_FUTURES_API_SECRET = b'Wqdz0U+SNcnqa3NKUAeHyjFWa7uE5ecQzgjbftH8pw+E5KptJDN6WBweGx7V0Kvi6clJJpIwhz+0CDJ4lJGkPsXD'  # noqa: E501


@pytest.fixture(name='kraken_demo_api_key')
def fixture_kraken_demo_api_key():
    return DEMO_KRAKEN_FUTURES_API_KEY


@pytest.fixture(name='kraken_demo_api_secret')
def fixture_kraken_demo_api_secret():
    return DEMO_KRAKEN_FUTURES_API_SECRET


@pytest.fixture(name='kraken_futures_test_base_uri')
def fixture_kraken_futures_test_base_uri():
    return 'https://demo-futures.kraken.com'


@pytest.fixture(name='kraken')
def fixture_kraken(
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        database,
):
    return create_test_kraken(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.fixture(name='demo_kraken_futures')
def fixture_demo_kraken_futures(
        function_scope_messages_aggregator,
        database,
        kraken_demo_api_key,
        kraken_demo_api_secret,
        kraken_futures_test_base_uri,
):
    return Krakenfutures(
        name='demo_kraken',
        api_key=kraken_demo_api_key,
        secret=kraken_demo_api_secret,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        base_uri=kraken_futures_test_base_uri,
    )
