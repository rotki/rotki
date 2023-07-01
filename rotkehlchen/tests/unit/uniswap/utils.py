
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    LiquidityPool,
    LiquidityPoolAsset,
    LiquidityPoolEventsBalance,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_DOLLAR_BASED
from rotkehlchen.types import AssetAmount, Price

# Logic: Get balances

# Addresses
TEST_ADDRESS_1 = string_to_evm_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
TEST_ADDRESS_2 = string_to_evm_address('0xcf2B8EeC2A9cE682822b252a1e9B78EedebEFB02')
TEST_ADDRESS_3 = string_to_evm_address('0x7777777777777777777777777777777777777777')


# Tokens without oracle data (unknown tokens)
A_SHL = Asset('eip155:1/erc20:0x8542325B72C6D9fC0aD2Ca965A78435413a915A0')
A_CAR = Asset('eip155:1/erc20:0x4D9e23a3842fE7Eb7682B9725cF6c507C424A41B')


def const_lp_1_events_balance() -> LiquidityPoolEventsBalance:
    return LiquidityPoolEventsBalance(
        pool_address=string_to_evm_address('0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89'),
        token0=A_DOLLAR_BASED.resolve_to_evm_token(),
        token1=A_WETH.resolve_to_evm_token(),
        profit_loss0=AssetAmount(FVal('35.489683548121546956')),
        profit_loss1=AssetAmount(FVal('-0.059966416263997186')),
        usd_profit_loss=FVal('35.429717131857549770'),
    )


def const_lp_2_events_balance() -> LiquidityPoolEventsBalance:
    return LiquidityPoolEventsBalance(
        pool_address=string_to_evm_address('0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55'),
        token0=A_WETH.resolve_to_evm_token(),
        token1=EvmToken('eip155:1/erc20:0xCF67CEd76E8356366291246A9222169F4dBdBe64'),
        profit_loss0=AssetAmount(FVal('-0.610130605729210250')),
        profit_loss1=AssetAmount(FVal('1.971799615456732408')),
        usd_profit_loss=FVal('1.361669009727522158'),
    )


def const_lp_3_balance() -> LiquidityPool:
    return LiquidityPool(
        address=string_to_evm_address('0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89'),
        assets=[
            LiquidityPoolAsset(
                token=A_DOLLAR_BASED.resolve_to_evm_token(),
                total_amount=FVal('13364.706850726724616147'),
                user_balance=Balance(
                    amount=FVal('5'),
                    usd_value=FVal('0.876854'),  # Updated
                ),
                usd_price=Price(FVal('4.38427')),  # Updated
            ),
            LiquidityPoolAsset(
                token=A_WETH.resolve_to_evm_token(),
                total_amount=FVal('24.831854200785672749'),
                user_balance=Balance(
                    amount=FVal('0.05'),
                    usd_value=FVal('23.573'),  # Updated
                ),
                usd_price=Price(FVal('471.46')),  # Updated
            ),
        ],
        total_supply=FVal('27.12436225218922874'),
        user_balance=Balance(
            amount=FVal('0.11'),
            usd_value=FVal('36.23'),  # Updated
        ),
    )


def const_lp_3_events_balance() -> LiquidityPoolEventsBalance:
    return LiquidityPoolEventsBalance(
        pool_address=string_to_evm_address('0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89'),
        token0=A_DOLLAR_BASED.resolve_to_evm_token(),
        token1=A_WETH.resolve_to_evm_token(),
        profit_loss0=AssetAmount(FVal('35.489683548121546956')),
        profit_loss1=AssetAmount(FVal('-0.059966416263997186')),
        usd_profit_loss=FVal('35.429717131857549770'),
    )
