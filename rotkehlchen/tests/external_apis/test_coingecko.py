import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.externalapis.coingecko import Coingecko, CoingeckoAssetData, CoingeckoImageURLs


@pytest.fixture(scope='session')
def session_coingecko():
    return Coingecko()


def test_asset_data(session_coingecko):
    expected_data = CoingeckoAssetData(
        identifier='bitcoin',
        symbol='btc',
        name='Bitcoin',
        images=CoingeckoImageURLs(
            thumb='https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png?1547033579',
            small='https://assets.coingecko.com/coins/images/1/small/bitcoin.png?1547033579',
            large='https://assets.coingecko.com/coins/images/1/large/bitcoin.png?1547033579',
        ),
    )
    data = session_coingecko.asset_data(A_BTC)
    assert data == expected_data

    expected_data = CoingeckoAssetData(
        identifier='yearn-finance',
        symbol='yfi',
        name='yearn.finance',
        images=CoingeckoImageURLs(
            thumb='https://assets.coingecko.com/coins/images/11849/thumb/yearn-finance.png?1595602501',  # noqa: E501
            small='https://assets.coingecko.com/coins/images/11849/small/yearn-finance.png?1595602501',  # noqa: E501
            large='https://assets.coingecko.com/coins/images/11849/large/yearn-finance.png?1595602501',  # noqa: E501
        ),
    )
    data = session_coingecko.asset_data(Asset('YFI'))
    assert data == expected_data
