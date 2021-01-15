from dataclasses import asdict

from eth_typing import HexAddress, HexStr

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.typing import ChecksumEthAddress

SHUF_ETHEREUM_ADDRESS = ChecksumEthAddress(
    HexAddress(HexStr('0x3A9FfF453d50D4Ac52A6890647b823379ba36B9E')),
)
SHUF_SYMBOL = 'SHUF'
SHUF_NAME = 'Shuffle.Monster V3'
SHUF_DECIMALS = 18


# Test initialization
def test_init_default():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    assert ue_token.ethereum_address == SHUF_ETHEREUM_ADDRESS
    assert ue_token.symbol == SHUF_SYMBOL
    assert ue_token.name is None
    assert ue_token.decimals is None


# Test operators
def test_eq():
    ue_token_1 = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    ue_token_2 = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL + 'does not matter',
        name=SHUF_NAME + 'name does no matter',
        decimals=SHUF_DECIMALS - 10,
    )
    assert ue_token_1 == ue_token_2


def test_eq_str():
    ue_token_1 = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    ue_token_2 = SHUF_ETHEREUM_ADDRESS
    assert ue_token_1 == ue_token_2


def test_eq_invalid_type():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    token = EthereumToken('WETH')
    assert ue_token != token


def test_hash():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    assert hash(ue_token) == hash(ue_token.ethereum_address)


def test_ne():
    ue_token_1 = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    ue_token_2 = UnknownEthereumToken(
        ethereum_address=str(SHUF_ETHEREUM_ADDRESS).lower(),
        symbol=SHUF_SYMBOL,
    )
    assert ue_token_1 != ue_token_2


# Test str and representation
def test_str_eq_name_ethereum_address():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
        name=SHUF_NAME,
        decimals=SHUF_DECIMALS,
    )
    assert str(ue_token) == f'{ue_token.name} {ue_token.ethereum_address}'


def test_str_eq_symbol_ethereum_address():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
        decimals=SHUF_DECIMALS,
    )
    assert str(ue_token) == f'{ue_token.symbol} {ue_token.ethereum_address}'


def test_repr():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
        name=SHUF_NAME,
        decimals=SHUF_DECIMALS,
    )
    exp_repr = (
        f'<UnknownEthereumToken '
        f'ethereum_address:{ue_token.ethereum_address} '
        f'symbol:{ue_token.symbol} '
        f'name:{ue_token.name} '
        f'decimals: {ue_token.decimals}>'
    )
    assert repr(ue_token) == exp_repr


# Test serialization
def test_serialize():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    assert ue_token.serialize() == ue_token.ethereum_address


def test_serialize_as_dict_wo_keys():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
    )
    ue_token_as_dict = ue_token.serialize_as_dict()

    assert ue_token_as_dict == asdict(ue_token)


def test_serialize_as_dict_with_keys():
    ue_token = UnknownEthereumToken(
        ethereum_address=SHUF_ETHEREUM_ADDRESS,
        symbol=SHUF_SYMBOL,
        name=SHUF_NAME,
        decimals=SHUF_DECIMALS,
    )
    sz_keys = ('decimals', 'ethereum_address', 'NOT_EXISTING_KEY')
    ue_token_as_dict = ue_token.serialize_as_dict(keys=sz_keys)

    assert len(ue_token_as_dict.keys()) == 2
    assert ue_token_as_dict['ethereum_address'] == ue_token.ethereum_address
    assert ue_token_as_dict['decimals'] == ue_token.decimals
