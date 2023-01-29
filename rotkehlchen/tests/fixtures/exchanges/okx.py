import pytest

from rotkehlchen.tests.utils.exchanges import create_test_okx


OKX_API_KEY = 'f32f48d7-74ad-41ce-8028-fcc4e4589f9c'
OKX_API_SECRET = b'3DC350723E8200C236792784644E17A0'
OKX_PASSPHRASE = 'Rotki123!'


@pytest.fixture(name='okx_api_key')
def fixture_okx_api_key():
    return OKX_API_KEY


@pytest.fixture(name='okx_api_secret')
def fixture_okx_api_secret():
    return OKX_API_SECRET


@pytest.fixture(name='okx_passphrase')
def fixture_okx_passphrase():
    return OKX_PASSPHRASE


@pytest.fixture()
def mock_okx(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
        okx_api_key,
        okx_api_secret,
        okx_passphrase,
):
    return create_test_okx(
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        api_key=okx_api_key,
        secret=okx_api_secret,
        passphrase=okx_passphrase,
    )
