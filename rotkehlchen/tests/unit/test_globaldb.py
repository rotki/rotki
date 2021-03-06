import pytest

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
from rotkehlchen.tests.utils.globaldb import INITIAL_TOKENS


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_get_ethereum_token_identifier(globaldb):
    assert globaldb.get_ethereum_token_identifier('0xnotexistingaddress') is None
    token_0_id = globaldb.get_ethereum_token_identifier(INITIAL_TOKENS[0].address)
    assert token_0_id == ETHEREUM_DIRECTIVE + INITIAL_TOKENS[0].address
