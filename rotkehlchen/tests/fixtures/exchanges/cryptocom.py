import pytest

from rotkehlchen.tests.utils.exchanges import create_test_cryptocom


@pytest.fixture(name='mock_cryptocom')
def fixture_cryptocom(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    return create_test_cryptocom(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key='ddddddd',
        secret=b'secret',
        name='MockCryptocom',
    )
