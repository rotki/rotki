import functools

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.modules.uniswap.typing import (
    EventType,
    LiquidityPool,
    LiquidityPoolAsset,
    LiquidityPoolEvent,
    LiquidityPoolEventsBalance,
)
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USDT, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_DOLLAR_BASED
from rotkehlchen.typing import AssetAmount, Price, Timestamp

# Logic: Get balances

# Addresses
TEST_ADDRESS_1 = string_to_ethereum_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
TEST_ADDRESS_2 = string_to_ethereum_address('0xcf2B8EeC2A9cE682822b252a1e9B78EedebEFB02')
TEST_ADDRESS_3 = string_to_ethereum_address('0x7777777777777777777777777777777777777777')


# Tokens without oracle data (unknown tokens)
A_SHL = EthereumToken('0x8542325B72C6D9fC0aD2Ca965A78435413a915A0')
A_CAR = EthereumToken('0x4D9e23a3842fE7Eb7682B9725cF6c507C424A41B')
A_BTR = EthereumToken('0xcbf15FB8246F679F9Df0135881CB29a3746f734b')

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
EXP_LIQUIDITY_POOL_1 = (
    LiquidityPool(
        address=string_to_ethereum_address('0x260E069deAd76baAC587B5141bB606Ef8b9Bab6c'),
        assets=[
            LiquidityPoolAsset(
                asset=A_SHL,
                total_amount=FVal('135433.787685858453561892'),
                user_balance=Balance(
                    amount=FVal('2486.554982222884623101272349'),
                    usd_value=ZERO,
                ),
                usd_price=Price(ZERO),
            ),
            LiquidityPoolAsset(
                asset=A_WETH,
                total_amount=FVal('72.576018267058292417'),
                user_balance=Balance(
                    amount=FVal('1.332490679729371260856256139'),
                    usd_value=ZERO,
                ),
                usd_price=Price(ZERO),
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
EXP_LIQUIDITY_POOL_2 = (
    LiquidityPool(
        address=string_to_ethereum_address('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae'),
        assets=[
            LiquidityPoolAsset(
                asset=A_CAR,
                total_amount=FVal('8898126.662476782539378895'),
                user_balance=Balance(
                    amount=FVal('3773477.536528796798537134308'),
                    usd_value=ZERO,
                ),
                usd_price=Price(ZERO),
            ),
            LiquidityPoolAsset(
                asset=A_USDT,
                total_amount=FVal('2351046.688852'),
                user_balance=Balance(
                    amount=FVal('997021.3061952553312356558897'),
                    usd_value=ZERO,
                ),
                usd_price=Price(ZERO),
            ),
        ],
        total_supply=FVal('4.565121916083260693'),
        user_balance=Balance(
            amount=FVal('1.935956370962755013'),
            usd_value=ZERO,
        ),
    )
)

# Expected `known_assets` and `unknown_assets` for LIQUIDITY_POSITION_1
EXP_KNOWN_ASSETS_1 = {A_WETH}
EXP_UNKNOWN_ASSETS_1 = {A_SHL}

# Expected `known_assets` and `unknown_assets` for LIQUIDITY_POSITION_2
EXP_KNOWN_ASSETS_2 = {A_USDT}
EXP_UNKNOWN_ASSETS_2 = {A_CAR}


# Method: `_get_unknown_asset_price_graph`
# 'tokenDayDatas' subgraph response data for SHL
TOKEN_DAY_DATA_SHL = {
    'token': {'id': A_SHL.ethereum_address},
    'priceUSD': '0.2373897544244518146892192714786454',
}
# 'tokenDayDatas' subgraph response data for CAR
TOKEN_DAY_DATA_CAR = {
    'token': {'id': A_CAR.ethereum_address},
    'priceUSD': '0.2635575008126147388714187358722384',
}

USD_PRICE_WETH = Price(FVal('441.82'))
USD_PRICE_USDT = Price(FVal('0.9998'))
USD_PRICE_SHL = Price(FVal('0.2373897544244518146892192714786454'))
USD_PRICE_CAR = Price(FVal('0.2635575008126147388714187358722384'))


# Method: `_update_assets_prices_in_address_balances`
# LIQUIDITY_POOL_1 with all the USD price/value fields updated
UPDATED_LIQUIDITY_POOL_1 = (
    LiquidityPool(
        address=string_to_ethereum_address('0x260E069deAd76baAC587B5141bB606Ef8b9Bab6c'),
        assets=[
            LiquidityPoolAsset(
                asset=A_SHL,
                total_amount=FVal('135433.787685858453561892'),
                user_balance=Balance(
                    amount=FVal('2486.554982222884623101272349'),
                    usd_value=FVal('590.2826765927877283774165039'),  # Updated
                ),
                usd_price=Price(FVal('0.2373897544244518146892192714786454')),  # Updated
            ),
            LiquidityPoolAsset(
                asset=A_WETH,
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
UPDATED_LIQUIDITY_POOL_2 = (
    LiquidityPool(
        address=string_to_ethereum_address('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae'),
        assets=[
            LiquidityPoolAsset(
                asset=A_CAR,
                total_amount=FVal('8898126.662476782539378895'),
                user_balance=Balance(
                    amount=FVal('3773477.536528796798537134308'),
                    usd_value=FVal('994528.3089000718252139634400'),  # Updated
                ),
                usd_price=Price(FVal('0.2635575008126147388714187358722384')),  # Updated
            ),
            LiquidityPoolAsset(
                asset=A_USDT,
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

# LIQUIDITY_POOL_1 with only the USDT USD price/value fields updated
UPDATED_LIQUIDITY_POOL_2_ONLY_USDT = (
    LiquidityPool(
        address=string_to_ethereum_address('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae'),
        assets=[
            LiquidityPoolAsset(
                asset=A_CAR,
                total_amount=FVal('8898126.662476782539378895'),
                user_balance=Balance(
                    amount=FVal('3773477.536528796798537134308'),
                    usd_value=ZERO,
                ),
                usd_price=Price(ZERO),
            ),
            LiquidityPoolAsset(
                asset=A_USDT,
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

# Method: `_calculate_events_balances`

LP_1_EVENTS = [
    LiquidityPoolEvent(
        tx_hash='0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824',
        log_index=263,
        address=TEST_ADDRESS_1,
        timestamp=Timestamp(1604273256),
        event_type=EventType.MINT,
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        amount0=AssetAmount(FVal('605.773209925184996494')),
        amount1=AssetAmount(FVal('1.106631443395672732')),
        usd_price=Price(FVal('872.4689300619698095220125311431804')),
        lp_amount=AssetAmount(FVal('1.220680531244355402')),
    ),
    LiquidityPoolEvent(
        tx_hash='0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa',
        log_index=66,
        address=TEST_ADDRESS_1,
        timestamp=Timestamp(1604283808),
        event_type=EventType.BURN,
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        amount0=AssetAmount(FVal('641.26289347330654345')),
        amount1=AssetAmount(FVal('1.046665027131675546')),
        usd_price=Price(FVal('837.2737746532695970921908229899852')),
        lp_amount=AssetAmount(FVal('1.220680531244355402')),
    ),
]
LP_2_EVENTS = [
    LiquidityPoolEvent(
        tx_hash='0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4',
        log_index=99,
        address=TEST_ADDRESS_1,
        timestamp=Timestamp(1598270334),
        event_type=EventType.MINT,
        pool_address=string_to_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
        token0=A_WETH,
        token1=A_BTR,
        amount0=AssetAmount(FVal('1.580431277572006656')),
        amount1=AssetAmount(FVal('3')),
        usd_price=Price(FVal('1281.249386421513581165086356450817')),
        lp_amount=AssetAmount(FVal('2.074549918528068811')),
    ),
    LiquidityPoolEvent(
        tx_hash='0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa',
        log_index=208,
        address=TEST_ADDRESS_1,
        timestamp=Timestamp(1599000975),
        event_type=EventType.BURN,
        pool_address=string_to_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
        token0=A_WETH,
        token1=A_BTR,
        amount0=AssetAmount(FVal('0.970300671842796406')),
        amount1=AssetAmount(FVal('4.971799615456732408')),
        usd_price=Price(FVal('928.8590296681781753390482605315881')),
        lp_amount=AssetAmount(FVal('2.074549918528068811')),
    ),
]
LP_1_EVENTS_BALANCE = (
    LiquidityPoolEventsBalance(
        address=TEST_ADDRESS_1,
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        events=LP_1_EVENTS,
        profit_loss0=AssetAmount(FVal('35.489683548121546956')),
        profit_loss1=AssetAmount(FVal('-0.059966416263997186')),
        usd_profit_loss=Price(FVal('-35.19515540870021242982170811')),
    )
)
LP_2_EVENTS_BALANCE = (
    LiquidityPoolEventsBalance(
        address=TEST_ADDRESS_1,
        pool_address=string_to_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),
        token0=A_WETH,
        token1=A_BTR,
        events=LP_2_EVENTS,
        profit_loss0=AssetAmount(FVal('-0.610130605729210250')),
        profit_loss1=AssetAmount(FVal('1.971799615456732408')),
        usd_profit_loss=Price(FVal('-352.3903567533354058260380955')),
    )
)
LP_3_EVENTS = [
    LiquidityPoolEvent(
        tx_hash='0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824',
        log_index=263,
        address=TEST_ADDRESS_1,
        timestamp=Timestamp(1604273256),
        event_type=EventType.MINT,
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        amount0=AssetAmount(FVal('605.773209925184996494')),
        amount1=AssetAmount(FVal('1.106631443395672732')),
        usd_price=Price(FVal('872.4689300619698095220125311431804')),
        lp_amount=AssetAmount(FVal('1.220680531244355402')),
    ),
    LiquidityPoolEvent(
        tx_hash='0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa',
        log_index=66,
        address=TEST_ADDRESS_1,
        timestamp=Timestamp(1604283808),
        event_type=EventType.BURN,
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        amount0=AssetAmount(FVal('600')),
        amount1=AssetAmount(FVal('1')),
        usd_price=Price(FVal('800')),
        lp_amount=AssetAmount(FVal('1')),
    ),
]
LP_3_BALANCE = (
    LiquidityPool(
        address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),
        assets=[
            LiquidityPoolAsset(
                asset=A_DOLLAR_BASED,
                total_amount=FVal('13364.706850726724616147'),
                user_balance=Balance(
                    amount=FVal('5'),
                    usd_value=FVal('0.876854'),  # Updated
                ),
                usd_price=Price(FVal('4.38427')),  # Updated
            ),
            LiquidityPoolAsset(
                asset=A_WETH,
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
)
LP_3_EVENTS_BALANCE = (
    LiquidityPoolEventsBalance(
        address=TEST_ADDRESS_1,
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        events=LP_3_EVENTS,
        profit_loss0=AssetAmount(FVal('-0.773209925184996494')),
        profit_loss1=AssetAmount(FVal('-0.056631443395672732')),
        usd_profit_loss=Price(FVal('-36.2389300619698095220125311')),
    )
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
