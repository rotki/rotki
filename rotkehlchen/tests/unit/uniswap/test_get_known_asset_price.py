import pytest

from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.constants import ZERO
from rotkehlchen.typing import Price

from .utils import ASSET_WETH, USD_PRICE_WETH


@pytest.mark.parametrize('mocked_current_prices', [{ASSET_WETH: USD_PRICE_WETH}])
def test_known_asset_has_usd_price(mock_uniswap, inquirer):  # pylint: disable=unused-argument
    """Test `known_asset_price` contains the known asset address and USD
    price when Inquirer returns a price gt ZERO.
    """
    known_assets = {ASSET_WETH}
    unknown_assets = set()

    known_asset_price = mock_uniswap._get_known_asset_price(
        known_assets=known_assets,
        unknown_assets=unknown_assets,
    )

    assert known_asset_price == {ASSET_WETH.ethereum_address: USD_PRICE_WETH}
    assert unknown_assets == set()


@pytest.mark.parametrize('mocked_current_prices', [{ASSET_WETH: Price(ZERO)}])
def test_known_asset_has_zero_usd_price(mock_uniswap, inquirer):  # pylint: disable=unused-argument
    """Test `known_asset_price` is empty and that an <UnknownEthereumToken>
    has been added in `unknown_assets` when Inquirer returns a price eq
    ZERO.
    """
    known_assets = {ASSET_WETH}
    unknown_assets = set()

    known_asset_price = mock_uniswap._get_known_asset_price(
        known_assets=known_assets,
        unknown_assets=unknown_assets,
    )

    assert known_asset_price == {}
    assert unknown_assets == {
        UnknownEthereumToken(
            ethereum_address=ASSET_WETH.ethereum_address,
            symbol=ASSET_WETH.symbol,
            name=ASSET_WETH.name,
            decimals=ASSET_WETH.decimals,
        ),
    }
