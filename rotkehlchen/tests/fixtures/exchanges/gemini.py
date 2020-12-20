import pytest

from rotkehlchen.exchanges.gemini import Gemini
from rotkehlchen.tests.utils.exchanges import create_test_gemini

SANDBOX_GEMINI_API_KEY = 'account-1eIn3XjiCdSZH2jizoNg'
SANDBOX_GEMINI_API_SECRET = b'26NFMLWrVWf1TrHQtVExRFmBovnq'

# Key with wrong permissions (Trader instead of auditor)
SANDBOX_GEMINI_WP_API_KEY = 'account-TDwgWRVnQqvsHDphwCUD'
SANDBOX_GEMINI_WP_API_SECRET = b'2ohngowRpWc2qnXpFj1TEur9xoww'


@pytest.fixture
def mock_gemini(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        base_uri,
):
    gemini = create_test_gemini(
        api_key='account-1aIn3XkiCdSZH2jiooMg',
        api_secret=b'361FMLZrVWf2TrHPtVEmRFmBovyq',
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        base_uri=base_uri,
    )
    gemini.first_connection_made = True
    return gemini


@pytest.fixture(name='gemini_sandbox_api_key')
def fixture_gemini_sandbox_api_key():
    return SANDBOX_GEMINI_API_KEY


@pytest.fixture(name='gemini_sandbox_api_secret')
def fixture_gemini_sandbox_api_secret():
    return SANDBOX_GEMINI_API_SECRET


@pytest.fixture(name='gemini_test_base_uri')
def fixture_gemini_test_base_uri():
    return 'https://api.sandbox.gemini.com'


@pytest.fixture
def sandbox_gemini(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        gemini_sandbox_api_key,
        gemini_sandbox_api_secret,
        gemini_test_base_uri,
):
    gemini = Gemini(
        api_key=gemini_sandbox_api_key,
        secret=gemini_sandbox_api_secret,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        base_uri=gemini_test_base_uri,
    )
    return gemini
