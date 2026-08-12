from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_kucoin
from rotkehlchen.tests.utils.factories import (
    make_api_key,
    make_api_secret,
    make_random_uppercasenumeric_string,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.kucoin import Kucoin
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.types import ApiKey, ApiSecret
    from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='kucoin_api_key')
def fixture_kucoin_api_key() -> ApiKey:
    return make_api_key()


@pytest.fixture(name='kucoin_api_secret')
def fixture_kucoin_api_secret() -> ApiSecret:
    return make_api_secret()


@pytest.fixture(name='kucoin_passphrase')
def fixture_kucoin_passphrase() -> str:
    return make_random_uppercasenumeric_string(size=6)


@pytest.fixture
def mock_kucoin(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        kucoin_api_key: ApiKey,
        kucoin_api_secret: ApiSecret,
        kucoin_passphrase: str,
) -> Kucoin:
    return create_test_kucoin(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=kucoin_api_key,
        secret=kucoin_api_secret,
        passphrase=kucoin_passphrase,
    )
