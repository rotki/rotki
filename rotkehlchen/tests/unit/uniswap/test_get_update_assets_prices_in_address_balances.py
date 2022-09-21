from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool, LiquidityPoolAsset
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_USDT, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price

from .utils import (
    A_CAR,
    A_SHL,
    EXP_LIQUIDITY_POOL_1,
    EXP_LIQUIDITY_POOL_2,
    TEST_ADDRESS_1,
    TEST_ADDRESS_2,
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
    # LIQUIDITY_POOL_1 with only the USDT USD price/value fields updated
    updated_liquidity_pool_2_only_usdt = (
        LiquidityPool(
            address=string_to_evm_address('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae'),
            assets=[
                LiquidityPoolAsset(
                    token=A_CAR,
                    total_amount=FVal('8898126.662476782539378895'),
                    user_balance=Balance(
                        amount=FVal('3773477.536528796798537134308'),
                        usd_value=ZERO,
                    ),
                    usd_price=Price(ZERO),
                ),
                LiquidityPoolAsset(
                    token=A_USDT,
                    total_amount=FVal('2351046.688852'),
                    user_balance=Balance(
                        amount=FVal('997021.3061952553312356558897'),
                        usd_value=FVal('996821.9019340162801694087585'),  # Updated
                    ),
                    usd_price=Price(FVal('0.9998')),  # Updated
                ),
            ],
            total_supply=FVal('4.565121916083260693'),
            user_balance=Balance(
                amount=FVal('1.935956370962755013'),
                usd_value=FVal('996821.9019340162801694087585'),  # Updated (USDT)
            ),
        )
    )

    address_balances = {TEST_ADDRESS_2: [EXP_LIQUIDITY_POOL_2]}
    known_asset_price = {A_USDT.resolve_to_evm_token().evm_address: USD_PRICE_USDT}
    unknown_asset_price = {}  # CAR not in it

    # Main call
    mock_uniswap._update_assets_prices_in_address_balances(
        address_balances=address_balances,
        known_asset_price=known_asset_price,
        unknown_asset_price=unknown_asset_price,
    )

    assert (
        address_balances[TEST_ADDRESS_2][0] ==
        updated_liquidity_pool_2_only_usdt
    )


def test_all_asset_prices_are_updated(mock_uniswap):
    """Test when all the assets prices are found either in
    `known_asset_price` or `unknown_asset_price`, all pool assets have
    their `usd_price` and `usd_value` updated, and the pool `usd_value` is
    updated with the total USD value.
    """
    # LIQUIDITY_POOL_1 with all the USD price/value fields updated
    updated_liquidity_pool_1 = (
        LiquidityPool(
            address=string_to_evm_address('0x260E069deAd76baAC587B5141bB606Ef8b9Bab6c'),
            assets=[
                LiquidityPoolAsset(
                    token=A_SHL,
                    total_amount=FVal('135433.787685858453561892'),
                    user_balance=Balance(
                        amount=FVal('2486.554982222884623101272349'),
                        usd_value=FVal('590.2826765927877283774165039'),  # Updated
                    ),
                    usd_price=Price(FVal('0.2373897544244518146892192714786454')),  # Updated
                ),
                LiquidityPoolAsset(
                    token=A_WETH,
                    total_amount=FVal('72.576018267058292417'),
                    user_balance=Balance(
                        amount=FVal('1.332490679729371260856256139'),
                        usd_value=FVal('588.7210321180308104715110873'),  # Updated
                    ),
                    usd_price=Price(FVal('441.82')),  # Updated
                ),
            ],
            total_supply=FVal('2885.30760350854829554'),
            user_balance=Balance(
                amount=FVal('52.974048199782328795'),
                usd_value=FVal('1179.003708710818538848927591'),  # Updated
            ),
        )
    )

    # LIQUIDITY_POOL_2 with all the USD price/value fields updated
    updated_liquidity_pool_2 = (
        LiquidityPool(
            address=string_to_evm_address('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae'),
            assets=[
                LiquidityPoolAsset(
                    token=A_CAR,
                    total_amount=FVal('8898126.662476782539378895'),
                    user_balance=Balance(
                        amount=FVal('3773477.536528796798537134308'),
                        usd_value=FVal('994528.3089000718252139634400'),  # Updated
                    ),
                    usd_price=Price(FVal('0.2635575008126147388714187358722384')),  # Updated
                ),
                LiquidityPoolAsset(
                    token=A_USDT,
                    total_amount=FVal('2351046.688852'),
                    user_balance=Balance(
                        amount=FVal('997021.3061952553312356558897'),
                        usd_value=FVal('996821.9019340162801694087585'),  # Updated
                    ),
                    usd_price=Price(FVal('0.9998')),  # Updated
                ),
            ],
            total_supply=FVal('4.565121916083260693'),
            user_balance=Balance(
                amount=FVal('1.935956370962755013'),
                usd_value=FVal('1991350.210834088105383372198'),  # Updated
            ),
        )
    )

    address_balances = {
        TEST_ADDRESS_1: [EXP_LIQUIDITY_POOL_1],
        TEST_ADDRESS_2: [EXP_LIQUIDITY_POOL_2],
    }
    known_asset_price = {
        A_WETH.resolve_to_evm_token().evm_address: USD_PRICE_WETH,
        A_USDT.resolve_to_evm_token().evm_address: USD_PRICE_USDT,
    }
    unknown_asset_price = {
        A_SHL.evm_address: USD_PRICE_SHL,
        A_CAR.evm_address: USD_PRICE_CAR,
    }

    # Main call
    mock_uniswap._update_assets_prices_in_address_balances(
        address_balances=address_balances,
        known_asset_price=known_asset_price,
        unknown_asset_price=unknown_asset_price,
    )

    assert address_balances[TEST_ADDRESS_1][0] == updated_liquidity_pool_1
    assert address_balances[TEST_ADDRESS_2][0] == updated_liquidity_pool_2
