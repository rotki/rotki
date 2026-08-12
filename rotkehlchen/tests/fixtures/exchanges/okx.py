from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.exchanges import create_test_okx
from rotkehlchen.types import ApiKey, ApiSecret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.okx import Okx
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator

OKX_API_KEY = ApiKey('f32f48d7-74ad-41ce-8028-fcc4e4589f9c')
OKX_API_SECRET = ApiSecret(b'3DC350723E8200C236792784644E17A0')
OKX_PASSPHRASE = 'Rotki123!'


@pytest.fixture(name='okx_api_key')
def fixture_okx_api_key() -> ApiKey:
    return OKX_API_KEY


@pytest.fixture(name='okx_api_secret')
def fixture_okx_api_secret() -> ApiSecret:
    return OKX_API_SECRET


@pytest.fixture(name='okx_passphrase')
def fixture_okx_passphrase() -> str:
    return OKX_PASSPHRASE


@pytest.fixture
def mock_okx(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        okx_api_key: ApiKey,
        okx_api_secret: ApiSecret,
        okx_passphrase: str,
) -> Okx:
    return create_test_okx(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=okx_api_key,
        secret=okx_api_secret,
        passphrase=okx_passphrase,
    )
