import pytest

from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_WETH
from rotkehlchen.typing import Price

from .utils import USD_PRICE_WETH


@pytest.mark.parametrize('mocked_current_prices', [{A_WETH: USD_PRICE_WETH}])
def test_known_asset_has_usd_price(mock_uniswap, inquirer):  # pylint: disable=unused-argument
    """Test `known_asset_price` contains the known asset address and USD
    price when Inquirer returns a price gt ZERO.
    """
    known_assets = {A_WETH}
    unknown_assets = set()

    known_asset_price = mock_uniswap._get_known_asset_price(
        known_assets=known_assets,
        unknown_assets=unknown_assets,
    )

    assert known_asset_price == {A_WETH.ethereum_address: USD_PRICE_WETH}
    assert unknown_assets == set()


@pytest.mark.parametrize('mocked_current_prices', [{A_WETH: Price(ZERO)}])
def test_known_asset_has_zero_usd_price(mock_uniswap, inquirer):  # pylint: disable=unused-argument
    """Test `known_asset_price` is empty and that an <UnknownEthereumToken>
    has been added in `unknown_assets` when Inquirer returns a price eq
    ZERO.
    """
    known_assets = {A_WETH}
    unknown_assets = set()

    known_asset_price = mock_uniswap._get_known_asset_price(
        known_assets=known_assets,
        unknown_assets=unknown_assets,
    )

    assert known_asset_price == {}
    assert unknown_assets == {
        UnknownEthereumToken(
            ethereum_address=A_WETH.ethereum_address,
            symbol=A_WETH.symbol,
            name=A_WETH.name,
            decimals=A_WETH.decimals,
        ),
    }
