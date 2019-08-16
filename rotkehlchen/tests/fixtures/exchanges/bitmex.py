import pytest

from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.user_messages import MessagesAggregator

TEST_BITMEX_API_KEY = b'XY98JYVL15Zn-iU9f7OsJeVf'
TEST_BITMEX_API_SECRET = b'671tM6f64bt6KhteDakj2uCCNBt7HhZVEE7H5x16Oy4zb1ag'


@pytest.fixture
def mock_bitmex(accounting_data_dir, inquirer):  # pylint: disable=unused-argument
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    bitmex = Bitmex(
        api_key=b'LAqUlngMIQkIUjXMUreyu3qn',
        secret=b'chNOOS4KvNXR_Xq4k4c9qsfoKWvnDecLATCRlcBwyKDYnWgO',
        user_directory=accounting_data_dir,
        msg_aggregator=MessagesAggregator(),
    )

    bitmex.first_connection_made = True
    return bitmex


@pytest.fixture
def test_bitmex(accounting_data_dir, inquirer):  # pylint: disable=unused-argument
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    bitmex = Bitmex(
        api_key=TEST_BITMEX_API_KEY,
        secret=TEST_BITMEX_API_SECRET,
        user_directory=accounting_data_dir,
        msg_aggregator=MessagesAggregator(),
    )
    bitmex.uri = 'https://testnet.bitmex.com'
    return bitmex
