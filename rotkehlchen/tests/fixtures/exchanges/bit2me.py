"""Fixtures for Bit2me exchange tests."""
import pytest

from rotkehlchen.exchanges.bit2me import Bit2me


@pytest.fixture(name='bit2me')
def fixture_bit2me(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    """Create a Bit2me exchange instance."""
    return Bit2me(
        name='bit2me',
        api_key='test_api_key',
        secret=b'test_secret',
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
