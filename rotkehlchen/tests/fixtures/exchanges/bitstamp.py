import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitstamp
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


@pytest.fixture(name='bitstamp_api_key')
def fixture_bitstamp_api_key():
    return make_api_key()


@pytest.fixture(name='bitstamp_api_secret')
def fixture_bitstamp_api_secret():
    return make_api_secret()


@pytest.fixture()
def mock_bitstamp(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        bitstamp_api_key,
        bitstamp_api_secret,
):
    return create_test_bitstamp(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=bitstamp_api_key,
        secret=bitstamp_api_secret,
    )
