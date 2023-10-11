import pytest

from rotkehlchen.tests.utils.exchanges import create_test_woo
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


@pytest.fixture(name='woo_api_key')
def fixture_woo_api_key():
    return make_api_key()


@pytest.fixture(name='woo_api_secret')
def fixture_woo_api_secret():
    return make_api_secret()


@pytest.fixture()
def mock_woo(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        woo_api_key,
        woo_api_secret,
):
    return create_test_woo(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=woo_api_key,
        secret=woo_api_secret,
    )
