import pytest

from rotkehlchen.exchanges.gemini import Gemini

SANDBOX_GEMINI_API_KEY = 'account-1eIn3XjiCdSZH2jizoNg'
SANDBOX_GEMINI_API_SECRET = b'26NFMLWrVWf1TrHQtVExRFmBovnq'


def _make_test_gemini(
        api_key,
        api_secret,
        database,
        msg_aggregator,
        base_uri,
):
    return Gemini(
        api_key=api_key,
        secret=api_secret,
        database=database,
        msg_aggregator=msg_aggregator,
        base_uri=base_uri,
    )


@pytest.fixture
def mock_gemini(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    gemini = _make_test_gemini(
        api_key='account-1aIn3XkiCdSZH2jiooMg',
        secret=b'361FMLZrVWf2TrHPtVEmRFmBovyq',
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        base_uri='https://api.sandbox.gemini.com',
    )
    gemini.first_connection_made = True
    return gemini


@pytest.fixture
def gemini_sandbox_api_key():
    return 'account-1eIn3XjiCdSZH2jizoNg'


@pytest.fixture
def gemini_sandbox_api_secret():
    return b'26NFMLWrVWf1TrHQtVExRFmBovnq'


@pytest.fixture
def sandbox_gemini(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        gemini_sandbox_api_key,
        gemini_sandbox_api_secret,
):
    gemini = Gemini(
        api_key=gemini_sandbox_api_key,
        secret=gemini_sandbox_api_secret,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        base_uri='https://api.sandbox.gemini.com',
    )
    return gemini
