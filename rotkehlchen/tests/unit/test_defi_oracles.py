import pytest

from rotkehlchen.constants.assets import A_1INCH, A_AAVE, A_BTC, A_DOGE, A_ETH, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors import PriceQueryUnsupportedAsset
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
    aave_price = inquirer_defi.find_usd_price(A_AAVE)
    inquirer_defi.set_oracles_order(oracles=[CurrentPriceOracle.UNISWAPV2])

    price = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_AAVE)
    assert price != Price(ZERO)
    assert (inch_price / aave_price).is_close(price, max_diff='0.01')

    inquirer_defi.set_oracles_order(oracles=[CurrentPriceOracle.UNISWAPV3])
    price = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_AAVE)
    assert (inch_price / aave_price).is_close(price, max_diff='0.01')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_special_cases(inquirer_defi):
    """
    Test special cases for the uniswap oracles
    """
    # ETH/WETH is handled correctly
    inquirer_defi.set_oracles_order(oracles=[CurrentPriceOracle.UNISWAPV2])
    inch_weth = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_WETH)
    inch_eth = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_ETH)
    assert inch_eth.is_close(inch_weth)
    # Non eth tokens
    with pytest.raises(PriceQueryUnsupportedAsset):
        inquirer_defi._uniswapv2.query_current_price(A_BTC, A_DOGE)
    # Same asset
    assert inquirer_defi._uniswapv2.query_current_price(A_ETH, A_WETH) == Price(ONE)
