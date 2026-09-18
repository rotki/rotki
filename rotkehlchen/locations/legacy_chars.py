"""Frozen view of the one-character location encoding used before the location tree.

User DBs before v54 and global DBs before v19 store every location as one character. Their
upgrades must keep reading and writing that encoding no matter how locations are represented in
the current code, so they go through this module instead of the current serializers.
"""
from typing import Final

from rotkehlchen.types import Location

# Reviewed mapping of every location character a v53 database can hold to the identifier of
# its node in the location tree. Never derive this from enum order at runtime. The characters
# of the protocol-labelled legacy locations are in V53_LEGACY_LOCATION_CHARS instead.
V53_LOCATION_CHAR_TO_IDENTIFIER: Final = {
    'A': 'external',
    'B': 'kraken',
    'C': 'poloniex',
    'D': 'bittrex',
    'E': 'binance',
    'F': 'bitmex',
    'G': 'coinbase',
    'H': 'total',
    'I': 'banks',
    'J': 'blockchain',
    'K': 'coinbasepro',
    'L': 'gemini',
    'M': 'equities',
    'N': 'realestate',
    'O': 'commodities',
    'P': 'cryptocom',
    'R': 'bitstamp',
    'S': 'binanceus',
    'T': 'bitfinex',
    'U': 'bitcoinde',
    'V': 'iconomi',
    'W': 'kucoin',
    'Y': 'loopring',
    'Z': 'ftx',
    '[': 'nexo',
    '\\': 'blockfi',
    ']': 'independentreserve',
    '`': 'shapeshift',
    'a': 'uphold',
    'b': 'bitpanda',
    'c': 'bisq',
    'd': 'ftxus',
    'e': 'okx',
    'f': 'ethereum',
    'g': 'optimism',
    'h': 'polygon pos',
    'i': 'arbitrum one',
    'j': 'base',
    'k': 'gnosis',
    'l': 'woo',
    'm': 'bybit',
    'n': 'scroll',
    'o': 'zksync lite',
    'p': 'htx',
    'q': 'bitcoin',
    'r': 'bitcoin cash',
    's': 'polkadot',
    't': 'kusama',
    'u': 'coinbaseprime',
    'v': 'binance sc',
    'w': 'solana',
    'x': 'avalanche',
    'y': 'hyperliquid',
    'z': 'monad',
    '{': 'gate',
    '|': 'bit2me',
    '}': 'coinex',
}
# Protocol-labelled locations: (tree identifier, display name, packaged image). Their nodes are
# created below LEGACY_LOCATIONS_PARENT only when user data still references them.
V53_LEGACY_LOCATION_CHARS: Final = {
    'Q': ('legacy:uniswap', 'Uniswap', 'uniswap.svg'),
    'X': ('legacy:balancer', 'Balancer', 'balancer.svg'),
    '^': ('legacy:gitcoin', 'Gitcoin', 'gitcoin.svg'),
    '_': ('legacy:sushiswap', 'Sushiswap', 'sushiswap.svg'),
}
# (identifier, name, parent identifier, icon) of the inactive parent of the legacy locations
LEGACY_LOCATIONS_PARENT: Final = ('legacy locations', 'Legacy locations', 'other', 'lu-archive')

# The enum serialization of every v53 character, protocol-labelled ones included
V53_CHAR_TO_NAME: Final = V53_LOCATION_CHAR_TO_IDENTIFIER | {
    char: identifier.removeprefix('legacy:')
    for char, (identifier, _, _) in V53_LEGACY_LOCATION_CHARS.items()
}
_V53_NAME_TO_CHAR: Final = {name: char for char, name in V53_CHAR_TO_NAME.items()}


def location_from_v53_char(char: str) -> Location:
    """Read a location stored in the pre-v54 one-character encoding.

    May raise KeyError for a character that no v53 database can hold.
    """
    return Location.deserialize(V53_CHAR_TO_NAME[char])


def location_to_v53_char(location: Location) -> str:
    """Encode a location in the pre-v54 one-character encoding.

    May raise KeyError for a location that did not exist in v53.
    """
    return _V53_NAME_TO_CHAR[str(location)]


def v53_char(name: str) -> str:
    """The pre-v54 character of the location with the given name, e.g. 'kraken' -> 'B'.

    May raise KeyError for a location that did not exist in v53.
    """
    return _V53_NAME_TO_CHAR[name]
