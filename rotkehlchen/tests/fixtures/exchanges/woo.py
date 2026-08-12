from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_woo
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.woo import Woo
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ApiKey, ApiSecret
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='woo_api_key')
def fixture_woo_api_key() -> ApiKey:
    return make_api_key()


@pytest.fixture(name='woo_api_secret')
def fixture_woo_api_secret() -> ApiSecret:
    return make_api_secret()


@pytest.fixture
def mock_woo(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        woo_api_key: ApiKey,
        woo_api_secret: ApiSecret,
) -> Woo:
    return create_test_woo(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=woo_api_key,
        secret=woo_api_secret,
    )
