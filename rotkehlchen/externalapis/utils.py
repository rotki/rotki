from typing import Any

from hexbytes import HexBytes as Web3HexBytes

from rotkehlchen.errors.serialization import ConversionError, DeserializationError
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
