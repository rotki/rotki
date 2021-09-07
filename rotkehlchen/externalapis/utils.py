from typing import Any, Dict

from rotkehlchen.errors import ConversionError, DeserializationError
from rotkehlchen.utils.misc import convert_to_int, hexstring_to_bytes

DEFAULT_API = 'etherscan'


def read_hash(data: Dict[str, Any], key: str, api: str = DEFAULT_API) -> bytes:
    try:
        result = hexstring_to_bytes(data[key])
    except DeserializationError as e:
        raise DeserializationError(
            f'Failed to read {key} as a hash during {api} transaction query',
        ) from e
    return result


def read_integer(data: Dict[str, Any], key: str, api: str = DEFAULT_API) -> int:
    try:
        result = convert_to_int(data[key])
    except ConversionError as e:
        raise DeserializationError(
            f'Failed to read {key} as an integer during {api} transaction query',
        ) from e
    return result
