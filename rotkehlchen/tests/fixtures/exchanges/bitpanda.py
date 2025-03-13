import pytest

from rotkehlchen.tests.utils.exchanges import create_test_bitpanda
from rotkehlchen.tests.utils.factories import make_api_key


@pytest.fixture(name='bitpanda_api_key')
def fixture_bitpanda_api_key():
    return make_api_key()


@pytest.fixture
def mock_bitpanda(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        bitpanda_api_key,
):
    return create_test_bitpanda(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=bitpanda_api_key,
    )
