import pytest
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.aggregator import ChainsAggregator

from rotkehlchen.constants.assets import A_ETH, A_USDC
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


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
@pytest.mark.parametrize('mocked_current_prices', [{A_USDC.identifier: 1, A_ETH: 3600}])
def test_sorting_nfts(blockchain: ChainsAggregator):
    """Test that if we have NFTs priced using different currencies then they are properly sorted
    by usd price when queried from the database.
    Regression test for https://github.com/rotki/rotki/issues/8022
    """
    with blockchain.database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO assets(identifier) VALUES(?)',
            (
                ('_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65',),
                ('_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041',),
            ),
        )
        write_cursor.executemany(
            'INSERT INTO nfts ("identifier", "name", "last_price", "last_price_asset", '
            '"manual_price", "owner_address", "is_lp", "image_url", '
            '"collection_name", "usd_price") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                ('_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'GasHawk Nest NFT', '1', 'ETH', '0', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'https://ipfs.io/ipfs/bafkreiadpakefxttuc5ry74hoswmlcp7ju5tq25lyghw2epa64u4nag3k4', 'GasHawk NFTs', '0.0'),  # noqa: E501
                ('_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041', 'yabir.eth', '20', 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', '1', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x3ad5e1887ef8024efa6d5070ccfda4868783a5343e1089e47fda9b4f7ce4f2b9/image', 'ENS: Ethereum Name Service', '0.0'),  # noqa: E501
            ],
        )

    nft_module = blockchain.get_module('nfts')
    balances = nft_module.get_db_nft_balances(filter_query=NFTFilterQuery.make(order_by_rules=[('usd_price', False)]))['entries']  # type: ignore  # noqa: E501
    assert balances[0]['id'] == '_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # gashawk with higher price first # noqa: E501
    assert balances[1]['id'] == '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041'  # noqa: E501
