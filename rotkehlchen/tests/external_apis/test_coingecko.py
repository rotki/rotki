
import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.assets import A_BNB, A_BTC, A_DAI, A_ETH, A_EUR, A_YFI
from rotkehlchen.errors.asset import UnsupportedAsset
from rotkehlchen.externalapis.coingecko import Coingecko, CoingeckoAssetData
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    Price,
    Timestamp,
)


def assert_coin_data_same(given, expected, compare_description=False):
    if compare_description:
        assert given == expected

    # else
    assert given.identifier == expected.identifier
    assert given.symbol == expected.symbol
    assert given.name == expected.name
    assert given.image_url == expected.image_url


@pytest.mark.vcr
def test_asset_data(session_coingecko):
    expected_data = CoingeckoAssetData(
        identifier='bitcoin',
        symbol='btc',
        name='Bitcoin',
        image_url='https://coin-images.coingecko.com/coins/images/1/small/bitcoin.png?1696501400',
    )
    data = session_coingecko.asset_data(A_BTC.resolve_to_asset_with_oracles().to_coingecko())
    assert_coin_data_same(data, expected_data)

    expected_data = CoingeckoAssetData(
        identifier='yearn-finance',
        symbol='yfi',
        name='yearn.finance',
        image_url='https://coin-images.coingecko.com/coins/images/11849/small/yearn.jpg?1696511720',
    )
    data = session_coingecko.asset_data(A_YFI.resolve_to_asset_with_oracles().to_coingecko())
    assert_coin_data_same(data, expected_data, compare_description=False)

    with pytest.raises(UnsupportedAsset):
        session_coingecko.asset_data(EvmToken('eip155:1/erc20:0x1844b21593262668B7248d0f57a220CaaBA46ab9').to_coingecko())  # PRL, a token without coingecko page  # noqa: E501


@pytest.mark.vcr
def test_coingecko_historical_price(session_coingecko):
    price = session_coingecko.query_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1704135600,
    )
    assert price == Price(FVal('2065.603754353392'))


@pytest.mark.vcr
@pytest.mark.freeze_time('2024-10-11 12:00:00 GMT')
def test_coingecko_with_api_key(database):
    with database.user_write() as write_cursor:  # add the api key to the DB
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.COINGECKO,
                api_key=ApiKey('123totallyrealapikey123'),
            )],
        )

    # assure initialization with the database argument work
    coingecko = Coingecko(database=database)
    data = coingecko.asset_data('zksync')
    assert data == CoingeckoAssetData(
        identifier='zksync',
        symbol='zk', name='ZKsync',
        image_url='https://coin-images.coingecko.com/coins/images/38043/small/ZKTokenBlack.png?1718614502',
    )
    result = coingecko.query_current_price(
        from_asset=A_ETH.resolve(),
        to_asset=A_BTC.resolve(),
    )
    assert result == FVal('0.03950436')

    result = coingecko.query_historical_price(
        from_asset=A_ETH.resolve(),
        to_asset=A_EUR.resolve(),
        timestamp=Timestamp(1712829246),

    )
    assert result == FVal('3295.1477375227337')


@pytest.mark.vcr
def test_coingecko_query_multiple_current_price(session_coingecko: 'Coingecko'):
    assert session_coingecko.query_multiple_current_price(
        from_assets=[
            A_BTC.resolve_to_asset_with_oracles(),
            A_DAI.resolve_to_asset_with_oracles(),
            A_BNB.resolve_to_asset_with_oracles(),
        ],
        to_asset=A_ETH.resolve_to_asset_with_oracles(),
    ) == {A_BTC: FVal(31.906046), A_DAI: FVal(0.0003068), A_BNB: FVal(0.21387074)}
