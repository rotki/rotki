from rotkehlchen.assets.asset import EthereumToken, UnderlyingToken
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_MKR
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import Timestamp

underlying_address1 = make_ethereum_address()
underlying_address2 = make_ethereum_address()
underlying_address3 = make_ethereum_address()

custom_address1 = make_ethereum_address()
custom_address2 = make_ethereum_address()
INITIAL_TOKENS = [
    EthereumToken.initialize(
        address=custom_address1,
        decimals=4,
        name='Custom 1',
        symbol='CST1',
        started=Timestamp(0),
        swapped_for=A_MKR,
        coingecko='internet-computer',
        cryptocompare='ICP',
        protocol='uniswap',
        underlying_tokens=[
            UnderlyingToken(address=underlying_address1, weight=FVal('0.5055')),
            UnderlyingToken(address=underlying_address2, weight=FVal('0.1545')),
            UnderlyingToken(address=underlying_address3, weight=FVal('0.34')),
        ],
    ),
    EthereumToken.initialize(
        address=custom_address2,
        decimals=18,
        name='Custom 2',
        symbol='CST2',
    ),
]

INITIAL_EXPECTED_TOKENS = [INITIAL_TOKENS[0]] + [
    EthereumToken.initialize(underlying_address1),
    EthereumToken.initialize(underlying_address2),
    EthereumToken.initialize(underlying_address3),
] + [INITIAL_TOKENS[1]]


underlying_address4 = make_ethereum_address()
custom_address3 = make_ethereum_address()
CUSTOM_TOKEN3 = EthereumToken.initialize(
    address=custom_address3,
    decimals=15,
    name='Custom 3',
    symbol='CST3',
    cryptocompare='ICP',
    protocol='aave',
    underlying_tokens=[
        UnderlyingToken(address=custom_address1, weight=FVal('0.55')),
        UnderlyingToken(address=underlying_address4, weight=FVal('0.45')),
    ],
)
