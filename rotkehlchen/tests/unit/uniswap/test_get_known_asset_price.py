from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.constants import ZERO
from rotkehlchen.typing import Price

from .utils import (
    ASSET_WETH,
    USD_PRICE_WETH,
)


def test_known_asset_has_usd_price(uniswap_module):
    """Test `known_asset_price` contains the known asset address and USD
    price when Inquirer returns a price gt ZERO.
    """
    def fake_price_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return USD_PRICE_WETH

    known_assets = {ASSET_WETH}
    unknown_assets = set()

    # Main call
    known_asset_price = uniswap_module._get_known_asset_price(
        known_assets=known_assets,
        unknown_assets=unknown_assets,
        price_query=fake_price_query,
    )

    assert known_asset_price == {ASSET_WETH.ethereum_address: USD_PRICE_WETH}
    assert unknown_assets == set()


def test_known_asset_has_zero_usd_price(uniswap_module):
    """Test `known_asset_price` is empty and that an <UnknownEthereumToken>
    has been added in `unknown_assets` when Inquirer returns a price eq
    ZERO.
    """
    def fake_price_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return Price(ZERO)

    known_assets = {ASSET_WETH}
    unknown_assets = set()

    # Main call
    known_asset_price = uniswap_module._get_known_asset_price(
        known_assets=known_assets,
        unknown_assets=unknown_assets,
        price_query=fake_price_query,
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
