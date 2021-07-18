import pytest

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_YFI
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.externalapis.coingecko import CoingeckoAssetData
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Price


def assert_coin_data_same(given, expected, compare_description=False):
    if compare_description:
        assert given == expected

    # else
    assert given.identifier == expected.identifier
    assert given.symbol == expected.symbol
    assert given.name == expected.name
    assert given.image_url == expected.image_url


def test_asset_data(session_coingecko):
    expected_data = CoingeckoAssetData(
        identifier='bitcoin',
        symbol='btc',
        name='Bitcoin',
        description='',
        image_url='https://assets.coingecko.com/coins/images/1/small/bitcoin.png?1547033579',
    )
    data = session_coingecko.asset_data(A_BTC)
    assert_coin_data_same(data, expected_data)

    expected_data = CoingeckoAssetData(
        identifier='yearn-finance',
        symbol='yfi',
        name='yearn.finance',
        description='Management token for the yearn.finance ecosystem',
        image_url='https://assets.coingecko.com/coins/images/11849/small/yfi-192x192.png?1598325330',  # noqa: E501
    )
    data = session_coingecko.asset_data(A_YFI)
    assert_coin_data_same(data, expected_data, compare_description=False)

    with pytest.raises(UnsupportedAsset):
        session_coingecko.asset_data(EthereumToken('0x1844b21593262668B7248d0f57a220CaaBA46ab9'))  # PRL, a token without coingecko page  # noqa: E501


def test_coingecko_historical_price(session_coingecko):
    price = session_coingecko.query_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1483056100,
    )
    assert price == Price(FVal('7.7478028375650725'))
