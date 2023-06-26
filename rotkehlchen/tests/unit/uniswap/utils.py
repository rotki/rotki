import functools

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    LiquidityPool,
    LiquidityPoolAsset,
    LiquidityPoolEventsBalance,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_USDT, A_WETH
from rotkehlchen.constants.misc import ZERO, ZERO_PRICE
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
A_BTR = Asset('eip155:1/erc20:0xcbf15FB8246F679F9Df0135881CB29a3746f734b')

# Method: `_get_balances_graph`
# 'liquidityPositions' subgraph response data for TEST_ADDRESS_1
LIQUIDITY_POSITION_1 = {
    'id': '0x260e069dead76baac587b5141bb606ef8b9bab6c-0xfef0e7635281ef8e3b705e9c5b86e1d3b0eab397',
    'liquidityTokenBalance': '52.974048199782328795',
    'pair': {
        'id': '0x260e069dead76baac587b5141bb606ef8b9bab6c',
        'reserve0': '135433.787685858453561892',
        'reserve1': '72.576018267058292417',
        'token0': {
            'decimals': '18',
            'id': '0x8542325b72c6d9fc0ad2ca965a78435413a915a0',
            'name': 'Oyster Shell',
            'symbol': 'SHL',
        },
        'token1': {
            'decimals': '18',
            'id': '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
            'name': 'Wrapped Ether',
            'symbol': 'WETH',
        },
        'totalSupply': '2885.30760350854829554',
    },
    'user': {
        'id': TEST_ADDRESS_1,
    },
}

# 'liquidityPositions' subgraph response data for TEST_ADDRESS_2
LIQUIDITY_POSITION_2 = {
    'id': '0x318be2aa088ffb991e3f6e61afb276744e36f4ae-0xcf2b8eec2a9ce682822b252a1e9b78eedebefb02',
    'liquidityTokenBalance': '1.935956370962755013',
    'pair': {
        'id': '0x318be2aa088ffb991e3f6e61afb276744e36f4ae',
        'reserve0': '8898126.662476782539378895',
        'reserve1': '2351046.688852',
        'token0': {
            'decimals': '18',
            'id': '0x4d9e23a3842fe7eb7682b9725cf6c507c424a41b',
            'name': 'CarBlock',
            'symbol': 'CAR',
        },
        'token1': {
            'decimals': '6',
            'id': '0xdac17f958d2ee523a2206206994597c13d831ec7',
            'name': 'Tether USD',
            'symbol': 'USDT',
        },
        'totalSupply': '4.565121916083260693',
    },
    'user': {
        'id': TEST_ADDRESS_2,
    },
}


# Expected <LiquidityPool> for LIQUIDITY_POSITION_1
def const_exp_liquidity_pool_1():
    return (
        LiquidityPool(
            address=string_to_evm_address('0x260E069deAd76baAC587B5141bB606Ef8b9Bab6c'),
            assets=[
                LiquidityPoolAsset(
                    token=A_SHL.resolve_to_evm_token(),
                    total_amount=FVal('135433.787685858453561892'),
                    user_balance=Balance(
                        amount=FVal('2486.554982222884623101272349'),
                        usd_value=ZERO,
                    ),
                    usd_price=ZERO_PRICE,
                ),
                LiquidityPoolAsset(
                    token=A_WETH.resolve_to_evm_token(),
                    total_amount=FVal('72.576018267058292417'),
                    user_balance=Balance(
                        amount=FVal('1.332490679729371260856256139'),
                        usd_value=ZERO,
                    ),
                    usd_price=ZERO_PRICE,
                ),
            ],
            total_supply=FVal('2885.30760350854829554'),
            user_balance=Balance(
                amount=FVal('52.974048199782328795'),
                usd_value=ZERO,
            ),
        )
    )


# Get balances expected <LiquidityPool> for LIQUIDITY_POSITION_2
def const_exp_liquidity_pool_2():
    return (
        LiquidityPool(
            address=string_to_evm_address('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae'),
            assets=[
                LiquidityPoolAsset(
                    token=A_CAR.resolve_to_evm_token(),
                    total_amount=FVal('8898126.662476782539378895'),
                    user_balance=Balance(
                        amount=FVal('3773477.536528796798537134308'),
                        usd_value=ZERO,
                    ),
                    usd_price=ZERO_PRICE,
                ),
                LiquidityPoolAsset(
                    token=A_USDT.resolve_to_evm_token(),
                    total_amount=FVal('2351046.688852'),
                    user_balance=Balance(
                        amount=FVal('997021.3061952553312356558897'),
                        usd_value=ZERO,
                    ),
                    usd_price=ZERO_PRICE,
                ),
            ],
            total_supply=FVal('4.565121916083260693'),
            user_balance=Balance(
                amount=FVal('1.935956370962755013'),
                usd_value=ZERO,
            ),
        )
    )


# Expected `known_tokens` and `unknown_tokens` for LIQUIDITY_POSITION_1
EXP_KNOWN_TOKENS_1 = {A_WETH}
EXP_UNKNOWN_TOKENS_1 = {A_SHL}

# Expected `known_tokens` and `unknown_tokens` for LIQUIDITY_POSITION_2
EXP_KNOWN_TOKENS_2 = {A_USDT}
EXP_UNKNOWN_TOKENS_2 = {A_CAR}


# Method: `_get_unknown_asset_price_graph`
# 'tokenDayDatas' subgraph response data for SHL
TOKEN_DAY_DATA_SHL = {
    'token': {'id': '0x8542325B72C6D9fC0aD2Ca965A78435413a915A0'},  # A_SHL.evm_address
    'priceUSD': '0.2373897544244518146892192714786454',
}
# 'tokenDayDatas' subgraph response data for CAR
TOKEN_DAY_DATA_CAR = {
    'token': {'id': '0x4D9e23a3842fE7Eb7682B9725cF6c507C424A41B'},
    'priceUSD': '0.2635575008126147388714187358722384',
}

USD_PRICE_WETH = Price(FVal('441.82'))
USD_PRICE_USDT = Price(FVal('0.9998'))
USD_PRICE_SHL = Price(FVal('0.2373897544244518146892192714786454'))
USD_PRICE_CAR = Price(FVal('0.2635575008126147388714187358722384'))


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


def store_call_args(func):
    """
    Helper function for pagination tests that call `self.graph.query()`.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        call_args = {'args': args, 'kwargs': kwargs}
        wrapper.calls.append(call_args)
        return func(*args, **kwargs)

    wrapper.calls = []
    return wrapper
