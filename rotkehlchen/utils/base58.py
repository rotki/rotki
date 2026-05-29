"""
A python implementation of the Base58Check encoding scheme.

The Base58Check encoding scheme is a modified Base 58 binary-to-text encoding.
More generically, Base58Check encoding is used for encoding byte arrays in
Bitcoin into human-typable strings.

ref: `<https://en.bitcoin.it/wiki/Base58Check_encoding>`_

:copyright: (c) 2018 by Joseph Black. license: MIT,

The code has been modified and optimized for the use case of rotki.
"""

from typing import Final

DEFAULT_CHARSET: Final[bytes] = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BASE58_LENGTH: Final[int] = 58
_CHARSET_INDEX: Final[dict[int, int]] = {char: idx for idx, char in enumerate(DEFAULT_CHARSET)}


def _b58encode_int(value: int) -> bytes:
    """Convert an integer to its Base58 bytes representation."""
    output = bytearray()
    while value:
        value, idx = divmod(value, BASE58_LENGTH)
        output.append(DEFAULT_CHARSET[idx])

    output.reverse()
    return bytes(output)


def _b58decode_int(val: bytes) -> int:
    """Convert Base58 bytes to the integer they represent."""
    output = 0
    for char in val:
        try:
            digit = _CHARSET_INDEX[char]
        except KeyError as e:
            raise ValueError(f'invalid base58 character: {chr(char)!r}') from e

        output = output * BASE58_LENGTH + digit

    return output


def b58encode(val: bytes) -> bytes:
    """Encode input to base58check encoding"""
    pad_len = 0
    for byte in val:
        if byte != 0:
            break

        pad_len += 1

    result = _b58encode_int(int.from_bytes(val[pad_len:], byteorder='big'))
    prefix = bytes([DEFAULT_CHARSET[0]]) * pad_len
    return prefix + result


def b58decode(val: bytes | str) -> bytes:
    """Decode base58check encoded input to original raw bytes"""
    if isinstance(val, str):
        val = val.encode('ascii')

    # obtain the number of leading 0 bytes
    zero_char, pad_len = DEFAULT_CHARSET[0], 0
    for char in val:
        if char != zero_char:
            break

        pad_len += 1

    acc = _b58decode_int(val[pad_len:])
    # convert acc to the smallest big endian byte string that can hold it.
    result = acc.to_bytes((acc.bit_length() + 7) // 8, byteorder='big')
    prefix = b'\0' * pad_len
    return prefix + result
