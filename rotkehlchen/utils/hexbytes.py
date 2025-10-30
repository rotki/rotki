"""This is inspired from https://github.com/ethereum/hexbytes and adjusted to the
way rotki works instead of subclassing it to handle errors our way in order to keep
it as lightweight as possible"""

from typing import Union, cast, overload

from hexbytes import HexBytes as Web3HexBytes

from rotkehlchen.errors.serialization import DeserializationError


def hexstring_to_bytes(hexstr: str) -> bytes:
    """May raise DeserializationError if it can't convert"""
    try:
        return bytes.fromhex(hexstr.removeprefix('0x'))
    except ValueError as e:
        raise DeserializationError(f'Failed to turn {hexstr} to bytes') from e


def to_bytes(val: Web3HexBytes | (bytearray | (bytes | str))) -> bytes:
    """
    Equivalent to: `eth_utils.hexstr_if_str(eth_utils.to_bytes, val)` .

    Convert a hex string, integer, or bool, to a bytes representation.
    Alternatively, pass through bytes or bytearray as a bytes value.
    """
    if isinstance(val, Web3HexBytes | bytearray):
        return bytes(val)
    if isinstance(val, bytes):
        return val
    if isinstance(val, str):
        return hexstring_to_bytes(val)

    raise DeserializationError(f'Cannot convert {val!r} of type {type(val)} to bytes')


class HexBytes(bytes):
    """
    HexBytes is a *very* thin wrapper around the python built-in :class:`bytes` class.

    It has these three changes:
        1. Accepts more hex strings as initializing values
        2. Returns hex with prefix '0x' from :meth:`HexBytes.hex`
        3. The representation at console is in hex
    """
    def __new__(
            cls: type[bytes],
            val: Web3HexBytes | (bytearray | (bytes | str)),
    ) -> 'HexBytes':
        bytesval = to_bytes(val)
        return cast('HexBytes', super().__new__(cls, bytesval))  # type: ignore  # https://github.com/python/typeshed/issues/2630

    def hex(self) -> str:  # type: ignore
        """
        Output hex-encoded bytes, with an "0x" prefix.

        Everything following the "0x" is output exactly like :meth:`bytes.hex`.

        type ignore is since we don't provide the same signature as bytes.hex()
        https://docs.python.org/3/library/stdtypes.html#bytes.hex
        """
        return '0x' + super().hex()

    @overload  # type: ignore
    def __getitem__(self, key: int) -> int:
        ...

    @overload
    def __getitem__(self, key: slice) -> 'HexBytes':
        ...

    def __getitem__(self, key: int | slice) -> Union[int, bytes, 'HexBytes']:
        result = super().__getitem__(key)
        if hasattr(result, 'hex'):
            return type(self)(result)  # type: ignore  # cant be an int

        return result

    def __repr__(self) -> str:
        return f'HexBytes({self.hex()!r})'

    @classmethod
    def from_bytes(cls: type['HexBytes'], value: bytes) -> 'HexBytes':
        """Creates a new HexBytes instance directly from bytes, skipping deserialization"""
        return super().__new__(cls, value)

    def __str__(self) -> str:
        return self.hex()
