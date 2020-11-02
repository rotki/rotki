import functools

from eth_utils.typing import HexAddress, HexStr

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import (
    ChecksumEthAddress,
    Price,
)
from rotkehlchen.chain.ethereum.uniswap.typing import (
    LiquidityPool,
    LiquidityPoolAsset,
)


# Logic: Get balances

# Addresses
TEST_ADDRESS_1 = ChecksumEthAddress(
    HexAddress(HexStr('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')),
)
TEST_ADDRESS_2 = ChecksumEthAddress(
    HexAddress(HexStr('0xcf2B8EeC2A9cE682822b252a1e9B78EedebEFB02')),
)
TEST_ADDRESS_3 = ChecksumEthAddress(
    HexAddress(HexStr('0x7777777777777777777777777777777777777777')),
)

# Known tokens
ASSET_USDT = EthereumToken('USDT')
ASSET_WETH = EthereumToken('WETH')

# Unknown tokens
ASSET_SHUF = UnknownEthereumToken(
    ethereum_address=ChecksumEthAddress(
        HexAddress(HexStr('0x3A9FfF453d50D4Ac52A6890647b823379ba36B9E')),
    ),
    symbol='SHUF',
    name='Shuffle.Monster V3',
    decimals=18,
)
ASSET_TGX = UnknownEthereumToken(
    ethereum_address=ChecksumEthAddress(
        HexAddress(HexStr('0x364A7381A5b378CeD7AB33d1CDf6ff1bf162Bfd6')),
    ),
    symbol='TGX',
    name='DeFi-X Token',
    decimals=18,
)

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
            'id': '0x3a9fff453d50d4ac52a6890647b823379ba36b9e',
            'name': 'Shuffle.Monster V3',
            'symbol': 'SHUF',
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
            'id': '0x364a7381a5b378ced7ab33d1cdf6ff1bf162bfd6',
            'name': 'DeFi-X Token',
            'symbol': 'TGX',
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
        address=ChecksumEthAddress(
            HexAddress(HexStr('0x260E069deAd76baAC587B5141bB606Ef8b9Bab6c')),
        ),
        assets=[
            LiquidityPoolAsset(
                asset=ASSET_SHUF,
                total_amount=FVal('135433.787685858453561892'),
                user_balance=Balance(
                    amount=FVal('2486.554982222884623101272349'),
                    usd_value=FVal(ZERO),
                ),
                usd_price=Price(ZERO),
            ),
            LiquidityPoolAsset(
                asset=ASSET_WETH,
                total_amount=FVal('72.576018267058292417'),
                user_balance=Balance(
                    amount=FVal('1.332490679729371260856256139'),
                    usd_value=FVal(ZERO),
                ),
                usd_price=Price(ZERO),
            ),
        ],
        total_supply=FVal('2885.30760350854829554'),
        user_balance=Balance(
            amount=FVal('52.974048199782328795'),
            usd_value=FVal(ZERO),
        ),
    )
)

# Get balances expected <LiquidityPool> for LIQUIDITY_POSITION_2
EXP_LIQUIDITY_POOL_2 = (
    LiquidityPool(
        address=ChecksumEthAddress(
            HexAddress(HexStr('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae')),
        ),
        assets=[
            LiquidityPoolAsset(
                asset=ASSET_TGX,
                total_amount=FVal('8898126.662476782539378895'),
                user_balance=Balance(
                    amount=FVal('3773477.536528796798537134308'),
                    usd_value=FVal(ZERO),
                ),
                usd_price=Price(ZERO),
            ),
            LiquidityPoolAsset(
                asset=ASSET_USDT,
                total_amount=FVal('2351046.688852'),
                user_balance=Balance(
                    amount=FVal('997021.3061952553312356558897'),
                    usd_value=FVal(ZERO),
                ),
                usd_price=Price(ZERO),
            ),
        ],
        total_supply=FVal('4.565121916083260693'),
        user_balance=Balance(
            amount=FVal('1.935956370962755013'),
            usd_value=FVal(ZERO),
        ),
    )
)

# Expected `known_assets` and `unknown_assets` for LIQUIDITY_POSITION_1
EXP_KNOWN_ASSETS_1 = {ASSET_WETH}
EXP_UNKNOWN_ASSETS_1 = {ASSET_SHUF}

# Expected `known_assets` and `unknown_assets` for LIQUIDITY_POSITION_2
EXP_KNOWN_ASSETS_2 = {ASSET_USDT}
EXP_UNKNOWN_ASSETS_2 = {ASSET_TGX}


# Method: `_get_unknown_asset_price_graph`
# 'tokenDayDatas' subgraph response data for SHUF
TOKEN_DAY_DATA_SHUF = {
    'token': {'id': ASSET_SHUF.ethereum_address},
    'priceUSD': '0.2373897544244518146892192714786454',
}
# 'tokenDayDatas' subgraph response data for TGX
TOKEN_DAY_DATA_TGX = {
    'token': {'id': ASSET_TGX.ethereum_address},
    'priceUSD': '0.2635575008126147388714187358722384',
}

USD_PRICE_WETH = Price(FVal('441.82'))
USD_PRICE_USDT = Price(FVal('0.9998'))
USD_PRICE_SHUF = Price(FVal('0.2373897544244518146892192714786454'))
USD_PRICE_TGX = Price(FVal('0.2635575008126147388714187358722384'))


# Method: `_update_assets_prices_in_address_balances`
# LIQUIDITY_POOL_1 with all the USD price/value fields updated
UPDATED_LIQUIDITY_POOL_1 = (
    LiquidityPool(
        address=ChecksumEthAddress(
            HexAddress(HexStr('0x260E069deAd76baAC587B5141bB606Ef8b9Bab6c')),
        ),
        assets=[
            LiquidityPoolAsset(
                asset=ASSET_SHUF,
                total_amount=FVal('135433.787685858453561892'),
                user_balance=Balance(
                    amount=FVal('2486.554982222884623101272349'),
                    usd_value=FVal('590.2826765927877283774165039'),  # Updated
                ),
                usd_price=Price(FVal('0.2373897544244518146892192714786454')),  # Updated
            ),
            LiquidityPoolAsset(
                asset=ASSET_WETH,
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
        address=ChecksumEthAddress(
            HexAddress(HexStr('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae')),
        ),
        assets=[
            LiquidityPoolAsset(
                asset=ASSET_TGX,
                total_amount=FVal('8898126.662476782539378895'),
                user_balance=Balance(
                    amount=FVal('3773477.536528796798537134308'),
                    usd_value=FVal('994528.3089000718252139634400'),  # Updated
                ),
                usd_price=Price(FVal('0.2635575008126147388714187358722384')),  # Updated
            ),
            LiquidityPoolAsset(
                asset=ASSET_USDT,
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
        address=ChecksumEthAddress(
            HexAddress(HexStr('0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae')),
        ),
        assets=[
            LiquidityPoolAsset(
                asset=ASSET_TGX,
                total_amount=FVal('8898126.662476782539378895'),
                user_balance=Balance(
                    amount=FVal('3773477.536528796798537134308'),
                    usd_value=FVal(ZERO),
                ),
                usd_price=Price(ZERO),
            ),
            LiquidityPoolAsset(
                asset=ASSET_USDT,
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
