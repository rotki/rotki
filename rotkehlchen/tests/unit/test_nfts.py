import pytest
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.aggregator import ChainsAggregator

from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress

TEST_ACC1 = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # yabir.eth
TEST_ACC2 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'  # lefteris.eth


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
    assert any(x['name'] == 'yabir.eth' for x in balances)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1143fd695a33ac740C84B93fd57f1f8396C1Af05']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nfts_floor_prices(
        blockchain: ChainsAggregator,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test that if the floor price is given in something else than ETH we correctly
    represent it.
    """
    nft_module = blockchain.get_module('nfts')
    assert nft_module is not None
    nfts = nft_module.opensea.get_account_nfts(ethereum_accounts[0])
    assert len(nfts) == 1
    assert nfts[0].collection is not None
    assert nfts[0].collection.floor_price == FVal(599)
    assert nfts[0].collection.floor_price_asset == Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')  # USDC.e on polygon # noqa: E501
