from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import ChainID, EvmTokenKind, Timestamp

underlying_address1 = make_ethereum_address()
underlying_address2 = make_ethereum_address()
underlying_address3 = make_ethereum_address()

user_token_address1 = make_ethereum_address()
user_token_address2 = make_ethereum_address()

MAKER_ASSET = EvmToken.initialize(
    address=string_to_evm_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
    chain=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    decimals=18,
    name='Maker',
    symbol='MKR',
    started=Timestamp(4),
    swapped_for=None,
    coingecko='maker',
    cryptocompare=None,
    protocol=None,
)

INITIAL_TOKENS = [
    EvmToken.initialize(
        address=user_token_address1,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=4,
        name='Custom 1',
        symbol='CST1',
        started=Timestamp(0),
        swapped_for=MAKER_ASSET,
        coingecko='internet-computer',
        cryptocompare='ICP',
        protocol='uniswap',
        underlying_tokens=[
            UnderlyingToken(address=underlying_address1, token_kind=EvmTokenKind.ERC20, weight=FVal('0.5055')),  # noqa: E501
            UnderlyingToken(address=underlying_address2, token_kind=EvmTokenKind.ERC20, weight=FVal('0.1545')),  # noqa: E501
            UnderlyingToken(address=underlying_address3, token_kind=EvmTokenKind.ERC20, weight=FVal('0.34')),  # noqa: E501
        ],
    ),
    EvmToken.initialize(
        address=user_token_address2,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Custom 2',
        symbol='CST2',
    ),
]

INITIAL_EXPECTED_TOKENS = [INITIAL_TOKENS[0]] + [
    EvmToken.initialize(underlying_address1, chain=ChainID.ETHEREUM, token_kind=EvmTokenKind.ERC20),  # noqa: E501
    EvmToken.initialize(underlying_address2, chain=ChainID.ETHEREUM, token_kind=EvmTokenKind.ERC20),  # noqa: E501
    EvmToken.initialize(underlying_address3, chain=ChainID.ETHEREUM, token_kind=EvmTokenKind.ERC20),  # noqa: E501
] + [INITIAL_TOKENS[1]]


underlying_address4 = make_ethereum_address()
user_token_address3 = make_ethereum_address()
USER_TOKEN3 = EvmToken.initialize(
    address=user_token_address3,
    chain=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    decimals=15,
    name='Custom 3',
    symbol='CST3',
    cryptocompare='ICP',
    protocol='aave',
    underlying_tokens=[
        UnderlyingToken(address=user_token_address1, token_kind=EvmTokenKind.ERC20, weight=FVal('0.55')),  # noqa: E501
        UnderlyingToken(address=underlying_address4, token_kind=EvmTokenKind.ERC20, weight=FVal('0.45')),  # noqa: E501
    ],
)
