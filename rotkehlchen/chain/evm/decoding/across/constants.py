from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.types import ChainID

CPT_ACROSS: Final = 'across'
ACROSS_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ACROSS,
    label='Across',
    image='across.svg',
)

# Event topics — byte literals with canonical 0x… values in comments
FUNDS_DEPOSITED: Final = b"2\xed\x1a@\x9e\xf0L{\x02'\x18\x9c:\x10=\xc5\xac\x10\xe7u\xa1[x]\xccQ\x02\x01\xf7\xc2Z\xd3"  # noqa: E501  # 0x32ed1a409ef04c7b0227189c3a103dc5ac10e775a15b785dcc510201f7c25ad3
V3_FUNDS_DEPOSITED: Final = b'\xa1#\xdc)\xae\xbf}\x0c3"\xc8\xee\xb5\xb9\x99\xe8Y\xf3\x997\x95\x0e\xd3\x10VS\'\x13\xd0\xde9o'  # noqa: E501  # 0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f
FILLED_RELAY: Final = b'\x8a\xb9\xdcl\x19\xfe\x88\xe6\x9b\xc7\x02!\xb39\xc8C2u/\xddIY\x1b|Q\xe6k\xae9G\xb7<'  # noqa: E501  # 0x8ab9dc6c19fe88e69bc70221b339c84332752fdd49591b7c51e66bae3947b73c
OLD_FILLED_RELAY: Final = b'm\xde\x811\xcc\xd2Q\x97b\x8e&K \xb0\xe1\x8a$\xa2\x9b\x81\x15\x8b\xe1\xa3\x9f\xd2Y\xa7B\xc9\xa05'  # noqa: E501  # 0x6dde8131ccd25197628e264b20b0e18a24a29b81158be1a39fd259a742c9a035
V3_FILLED_RELAY: Final = b"Fo$;9\x0fI\xcb\x03\x1dA\x19NM\xff\x86\xf1 \x8b\n\x84\xe0'>\xcd\xb0d\xd9\xd9\x8d\x07\xbb"  # noqa: E501  # 0x466f243b390f49cb031d41194e4dff86f1208b0a84e0273ecdb064d9d98d07bb  # spellchecker:disable-line
FILLED_RELAY_WITH_RELAY_EXECUTION_INFO: Final = b'D\xb5Y\xf1\x01\xf8\xfb\xcc\x8a\x0e\xa4?\xa9\x1a\x05\xa7)\xa5\xean\x14\xa7\xc7Z\xa7P7F\x90\x13r\x08'  # noqa: E501  # 0x44b559f101f8fbcc8a0ea43fa91a05a729a5ea6e14a7c75aa750374690137208
LIQUIDITY_ADDED: Final = b'<ip\x1aa\xc7\x9a\x92\xef\x96\x92\x90:\xaa\x00h\xbc\xe8w\x13a\xec\xb0\x95G9\x1eO\xb4\xdf\x857'  # noqa: E501  # 0x3c69701a61c79a92ef9692903aaa0068bce8771361ecb09547391e4fb4df8537
LIQUIDITY_REMOVED: Final = b'\xcd\xa1\x18_(Y\x9ek\xd1J\xb8\xa6\x8b<0\xa1\x1e\x1d\xceBV\xb5\xe6~\x94\xdd?\xd8F\xa6\xc5\x89'  # noqa: E501  # 0xcda1185f28599e6bd14ab8a68b3c30a11e1dce4256b5e67e94dd3fd846a6c589
LP_TOKEN_STAKED: Final = b'$\x9bi/\xf3\xa1U=\xae\xcb+V\xa8\x07Fl\xab\x98\xa0\xac\xdc\xa4p\xf0\xd1\x8c\x10d\xe8\x9bW2'  # noqa: E501  # 0x249b692ff3a1553daecb2b56a807466cab98a0acdca470f0d18c1064e89b5732
LP_TOKEN_UNSTAKED: Final = b'\xfep\x07\xb2\xe8\x9d\x80\xed\xdav)\x92Q\xdf\x086d\x80\xca\xc2.^&\x0f^f.\x85\x0b\x1fz2'  # noqa: E501  # 0xfe7007b2e89d80edda76299251df08366480cac22e5e260f5e662e850b1f7a32

DEPOSIT_TOPICS: Final = {FUNDS_DEPOSITED, V3_FUNDS_DEPOSITED}
FILL_TOPICS: Final = {
    FILLED_RELAY,
    FILLED_RELAY_WITH_RELAY_EXECUTION_INFO,
    OLD_FILLED_RELAY,
    V3_FILLED_RELAY,
}

# Mapping of Across chain IDs to rotki ChainIDs (only chains rotki supports)
ACROSS_CHAIN_MAPPING: Final = {
    1: ChainID.ETHEREUM,
    10: ChainID.OPTIMISM,
    56: ChainID.BINANCE_SC,
    137: ChainID.POLYGON_POS,
    143: ChainID.MONAD,
    999: ChainID.HYPERLIQUID,
    8453: ChainID.BASE,
    42161: ChainID.ARBITRUM_ONE,
    534352: ChainID.SCROLL,
}
