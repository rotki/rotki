"""Frozen facts about the location enum that the location tree replaced, for tests that
check migrations against an independent source."""
from typing import Final

# serialization of every enum member a v53 user DB can hold, in enum value order. The DB
# stored member number n as chr(n + 64).
V53_ENUM_SERIALIZATIONS: Final = (
    'external',
    'kraken',
    'poloniex',
    'bittrex',
    'binance',
    'bitmex',
    'coinbase',
    'total',
    'banks',
    'blockchain',
    'coinbasepro',
    'gemini',
    'equities',
    'realestate',
    'commodities',
    'cryptocom',
    'uniswap',
    'bitstamp',
    'binanceus',
    'bitfinex',
    'bitcoinde',
    'iconomi',
    'kucoin',
    'balancer',
    'loopring',
    'ftx',
    'nexo',
    'blockfi',
    'independentreserve',
    'gitcoin',
    'sushiswap',
    'shapeshift',
    'uphold',
    'bitpanda',
    'bisq',
    'ftxus',
    'okx',
    'ethereum',
    'optimism',
    'polygon pos',
    'arbitrum one',
    'base',
    'gnosis',
    'woo',
    'bybit',
    'scroll',
    'zksync lite',
    'htx',
    'bitcoin',
    'bitcoin cash',
    'polkadot',
    'kusama',
    'coinbaseprime',
    'binance sc',
    'solana',
    'avalanche',
    'hyperliquid',
    'monad',
    'gate',
    'bit2me',
    'coinex',
)
V53_ENUM_CHAR_TO_SERIALIZATION: Final = {
    chr(index + 65): name for index, name in enumerate(V53_ENUM_SERIALIZATIONS)
}


def v53_seq(location: str) -> int:
    """The `seq` (enum value) a location had in the pre-v54 location table"""
    return V53_ENUM_SERIALIZATIONS.index(location) + 1
