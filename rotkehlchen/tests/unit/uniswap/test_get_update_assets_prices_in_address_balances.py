from rotkehlchen.constants.assets import A_USDT, A_WETH

from .utils import (
    A_CAR,
    A_SHL,
    EXP_LIQUIDITY_POOL_1,
    EXP_LIQUIDITY_POOL_2,
    TEST_ADDRESS_1,
    TEST_ADDRESS_2,
    UPDATED_LIQUIDITY_POOL_1,
    UPDATED_LIQUIDITY_POOL_2,
    UPDATED_LIQUIDITY_POOL_2_ONLY_USDT,
    USD_PRICE_CAR,
    USD_PRICE_SHL,
    USD_PRICE_USDT,
    USD_PRICE_WETH,
)


def test_half_asset_prices_are_updated(mock_uniswap):
    """Test when an asset price is not found in `known_asset_price`,
    nor in `unknown_asset_price`, its `usd_price` and `usd_value` remain 0,
    and the liquidity pool `usd_value` does not count it.

    Expected updates:
        - USDT pool asset is updated
        - CAR pool asset is not updated
        - Liquidity pool only counts USDT USD value
    """
    address_balances = {TEST_ADDRESS_2: [EXP_LIQUIDITY_POOL_2]}
    known_asset_price = {A_USDT.ethereum_address: USD_PRICE_USDT}
    unknown_asset_price = {}  # CAR not in it

    # Main call
    mock_uniswap._update_assets_prices_in_address_balances(
        address_balances=address_balances,
        known_asset_price=known_asset_price,
        unknown_asset_price=unknown_asset_price,
    )

    assert (
        address_balances[TEST_ADDRESS_2][0] ==
        UPDATED_LIQUIDITY_POOL_2_ONLY_USDT
    )


def test_all_asset_prices_are_updated(mock_uniswap):
    """Test when all the assets prices are found either in
    `known_asset_price` or `unknown_asset_price`, all pool assets have
    their `usd_price` and `usd_value` updated, and the pool `usd_value` is
    updated with the total USD value.
    """
    address_balances = {
        TEST_ADDRESS_1: [EXP_LIQUIDITY_POOL_1],
        TEST_ADDRESS_2: [EXP_LIQUIDITY_POOL_2],
    }
    known_asset_price = {
        A_WETH.ethereum_address: USD_PRICE_WETH,
        A_USDT.ethereum_address: USD_PRICE_USDT,
    }
    unknown_asset_price = {
        A_SHL.ethereum_address: USD_PRICE_SHL,
        A_CAR.ethereum_address: USD_PRICE_CAR,
    }

    # Main call
    mock_uniswap._update_assets_prices_in_address_balances(
        address_balances=address_balances,
        known_asset_price=known_asset_price,
        unknown_asset_price=unknown_asset_price,
    )

    assert address_balances[TEST_ADDRESS_1][0] == UPDATED_LIQUIDITY_POOL_1
    assert address_balances[TEST_ADDRESS_2][0] == UPDATED_LIQUIDITY_POOL_2
