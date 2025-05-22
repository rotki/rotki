from typing import Any

from hexbytes import HexBytes as Web3HexBytes

from rotkehlchen.chain.binance_sc.constants import BINANCE_SC_GENESIS
from rotkehlchen.chain.scroll.constants import SCROLL_GENESIS
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID, Timestamp
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import convert_to_int

DEFAULT_API = 'etherscan'


def read_hash(data: dict[str, Any], key: str, api: str = DEFAULT_API) -> bytes:
    if isinstance(data[key], Web3HexBytes):
        return bytes(data[key])

    try:
        result = hexstring_to_bytes(data[key])
    except DeserializationError as e:
        raise DeserializationError(
            f'Failed to read {key} as a hash during {api} transaction query',
        ) from e

    return result


def read_integer(data: dict[str, Any], key: str, api: str = DEFAULT_API) -> int:
    try:
        result = convert_to_int(data[key])
    except ConversionError as e:
        raise DeserializationError(
            f'Failed to read {key} as an integer during {api} transaction query',
        ) from e
    return result


def maybe_read_integer(data: dict[str, Any], key: str, api: str = DEFAULT_API, default_value: int = 0) -> int:  # noqa: E501
    try:
        result = read_integer(data=data, key=key, api=api)
    except KeyError:
        result = default_value

    return result


def get_earliest_ts(chain_id: SUPPORTED_CHAIN_IDS) -> Timestamp:
    """Return the min timestamp per chain that we query in etherscan/blockscout
    when asking for a blocknumber. Those timestamps are close to the genesis
    since etherscan didn't work fine when querying close to the block 0.
    """
    match chain_id:
        case ChainID.ETHEREUM:
            return Timestamp(1438269989)
        case ChainID.OPTIMISM:
            return Timestamp(1636665399)
        case ChainID.ARBITRUM_ONE:
            return Timestamp(1622243344)
        case ChainID.BASE:
            return Timestamp(1686789347)
        case ChainID.GNOSIS:
            return Timestamp(1539024185)
        case ChainID.SCROLL:
            return SCROLL_GENESIS
        case ChainID.BINANCE_SC:
            return BINANCE_SC_GENESIS
        case ChainID.POLYGON_POS:
            return Timestamp(1590856200)

    raise InputError(f'Unexpected chain {chain_id} when querying earliest block ts')
