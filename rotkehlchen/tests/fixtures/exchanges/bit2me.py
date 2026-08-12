"""Fixtures for Bit2me exchange tests."""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.exchanges.bit2me import Bit2me
from rotkehlchen.types import ApiKey, ApiSecret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='bit2me')
def fixture_bit2me(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
) -> Bit2me:
    """Create a Bit2me exchange instance."""
    return Bit2me(
        name='bit2me',
        api_key=ApiKey('test_api_key'),
        secret=ApiSecret(b'test_secret'),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
