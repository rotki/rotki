import pytest
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.externalapis.coingecko import CoingeckoAssetData, CoingeckoImageURLs
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_EUR
from rotkehlchen.typing import Price
from rotkehlchen.errors import UnsupportedAsset


def assert_coin_data_same(given, expected, compare_description=False):
    if compare_description:
        assert given == expected

    # else
    assert given.identifier == expected.identifier
    assert given.symbol == expected.symbol
    assert given.name == expected.name
    assert given.images.thumb == expected.images.thumb
    assert given.images.small == expected.images.small
    assert given.images.large == expected.images.large


def test_asset_data(session_coingecko):
    expected_data = CoingeckoAssetData(
        identifier='bitcoin',
        symbol='btc',
        name='Bitcoin',
        description='',
        images=CoingeckoImageURLs(
            thumb='https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png?1547033579',
            small='https://assets.coingecko.com/coins/images/1/small/bitcoin.png?1547033579',
            large='https://assets.coingecko.com/coins/images/1/large/bitcoin.png?1547033579',
        ),
    )
    data = session_coingecko.asset_data(A_BTC)
    assert_coin_data_same(data, expected_data)

    expected_data = CoingeckoAssetData(
        identifier='yearn-finance',
        symbol='yfi',
        name='yearn.finance',
        description='Management token for the yearn.finance ecosystem',
        images=CoingeckoImageURLs(
            thumb='https://assets.coingecko.com/coins/images/11849/thumb/yfi-192x192.png?1598325330',  # noqa: E501
            small='https://assets.coingecko.com/coins/images/11849/small/yfi-192x192.png?1598325330',  # noqa: E501
            large='https://assets.coingecko.com/coins/images/11849/large/yfi-192x192.png?1598325330',  # noqa: E501
        ),
    )
    data = session_coingecko.asset_data(Asset('YFI'))
    assert_coin_data_same(data, expected_data, compare_description=False)

    with pytest.raises(UnsupportedAsset):
        session_coingecko.asset_data(Asset('PRL'))


def test_coingecko_historical_price(session_coingecko):
    price = session_coingecko.query_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1483056100,
    )
    assert price == Price(FVal('7.7478028375650725'))
