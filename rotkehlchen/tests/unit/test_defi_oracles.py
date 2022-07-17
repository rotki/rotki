from copy import deepcopy
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.assets import A_1INCH, A_BTC, A_DOGE, A_ETH, A_LINK, A_USDC, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.types import Price


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_asset_to_asset(inquirer_defi):
    """
    Test that the uniswap oracles return a price close to the one reported by
    coingecko.
    """
    inch_price = inquirer_defi.find_usd_price(A_1INCH)
    link_price = inquirer_defi.find_usd_price(A_LINK)

    for oracle in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3):
        if oracle == CurrentPriceOracle.UNISWAPV2:
            price_instance = inquirer_defi._uniswapv2
        else:
            price_instance = inquirer_defi._uniswapv3
        inquirer_defi.set_oracles_order(oracles=[oracle])
        price = price_instance.query_current_price(A_1INCH, A_LINK)
        assert price != Price(ZERO)
        assert (inch_price / link_price).is_close(price, max_diff='0.01')
        defi_price = inquirer_defi.find_usd_price(A_LINK, ignore_cache=True)
        assert abs(defi_price - link_price) / link_price < FVal(0.1), f'{defi_price=} and {link_price=} have more than 10% difference'  # noqa: E501

        # test with ethereum tokens but as assets instead of instance of the EvmToken class
        a1inch = Asset(A_1INCH.identifier)
        alink = Asset(A_LINK.identifier)
        price_as_assets = price_instance.query_current_price(a1inch, alink)
        assert price_as_assets.is_close(price, max_diff='0.01')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_special_cases(inquirer_defi):
    """
    Test special cases for the uniswap oracles
    """
    # ETH/WETH is handled correctly
    for oracle in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3):
        inquirer_defi.set_oracles_order(oracles=[oracle])
        inch_weth = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_WETH)
        inch_eth = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_ETH)
        assert inch_eth.is_close(inch_weth)
        # Non eth tokens
        with pytest.raises(PriceQueryUnsupportedAsset):
            inquirer_defi._uniswapv2.query_current_price(A_BTC, A_DOGE)
        # Same asset
        assert inquirer_defi._uniswapv2.query_current_price(A_ETH, A_WETH) == Price(ONE)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_no_decimals(inquirer_defi):
    """Test that if a token has no information about the number of decimals a proper error
    is raised"""
    asset_resolver = AssetResolver()
    original_getter = asset_resolver.get_asset_data

    def fake_weth_token():
        """Make sure that the weth token has no decimals fields and any other token
        is loaded properly
        """
        def mocked_asset_getter(asset_identifier: str, form_with_incomplete_data: bool = False):
            if asset_identifier == A_WETH.identifier:
                fake_weth = deepcopy(A_WETH)
                object.__setattr__(fake_weth, 'decimals', None)
                return fake_weth
            return original_getter(asset_identifier, form_with_incomplete_data)
        return patch.object(asset_resolver, 'get_asset_data', wraps=mocked_asset_getter)

    with fake_weth_token():
        weth = EvmToken(A_WETH.identifier)
        assert weth.decimals is None
        with pytest.raises(DefiPoolError):
            inquirer_defi._uniswapv2.query_current_price(weth, A_USDC)
        with pytest.raises(DefiPoolError):
            inquirer_defi._uniswapv3.query_current_price(weth, A_USDC)
