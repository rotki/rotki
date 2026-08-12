from typing import TYPE_CHECKING

import pytest

from rotkehlchen.exchanges.gemini import Gemini
from rotkehlchen.types import ApiKey, ApiSecret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.user_messages import MessagesAggregator

SANDBOX_GEMINI_API_KEY = ApiKey('account-1eIn3XjiCdSZH2jizoNg')
SANDBOX_GEMINI_API_SECRET = ApiSecret(b'26NFMLWrVWf1TrHQtVExRFmBovnq')

# Key with wrong permissions (Trader instead of auditor)
SANDBOX_GEMINI_WP_API_KEY = ApiKey('account-TDwgWRVnQqvsHDphwCUD')
SANDBOX_GEMINI_WP_API_SECRET = ApiSecret(b'2ohngowRpWc2qnXpFj1TEur9xoww')


@pytest.fixture(name='gemini_sandbox_api_key')
def fixture_gemini_sandbox_api_key() -> ApiKey:
    return SANDBOX_GEMINI_API_KEY


@pytest.fixture(name='gemini_sandbox_api_secret')
def fixture_gemini_sandbox_api_secret() -> ApiSecret:
    return SANDBOX_GEMINI_API_SECRET


@pytest.fixture(name='gemini_test_base_uri')
def fixture_gemini_test_base_uri() -> str:
    return 'https://api.sandbox.gemini.com'


@pytest.fixture
def sandbox_gemini(
        database: DBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator: MessagesAggregator,
        gemini_sandbox_api_key: ApiKey,
        gemini_sandbox_api_secret: ApiSecret,
        gemini_test_base_uri: str,
) -> Gemini:
    return Gemini(
        name='gemini',
        api_key=gemini_sandbox_api_key,
        secret=gemini_sandbox_api_secret,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        base_uri=gemini_test_base_uri,
    )
