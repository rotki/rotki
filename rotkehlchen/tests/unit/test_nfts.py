import pytest
from rotkehlchen.db.filtering import NFTFilterQuery

TEST_ACC1 = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # yabir.eth
TEST_ACC2 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'  # lefteris.eth


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_addresses_queried_for_nfts(blockchain):
    """Tests that nfts are only queried for addresses stored in the database preventing the
    IntegrityError described in https://github.com/rotki/rotki/issues/4456
    """
    nft_module = blockchain.get_module('nfts')
    nft_module.query_balances(
        addresses=[TEST_ACC1, TEST_ACC2],
        uniswap_nfts=None,
    )
    balances = nft_module.get_db_nft_balances(filter_query=NFTFilterQuery.make())['entries']
    assert len(balances) == 1 and balances[0]['name'] == 'yabir.eth'
