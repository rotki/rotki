"""Minimal Bitcoin Cash CashAddr encoder/decoder.

Implemented from the Bitcoin Cash CashAddr specification:
https://github.com/bitcoincashorg/bitcoincash.org/blob/master/spec/cashaddr.md

It reuses the bit-conversion helper from the existing `bech32` dependency, which packages
Pieter Wuille's MIT-licensed BIP173 reference implementation.

Added to rotki using Codex and ChatGPT 5.5.
"""

from typing import Final

import bech32

CHARSET: Final = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
GENERATOR: Final = (0x98f2bc8e61, 0x79b76d99e2, 0xf33e5fb3c4, 0xae2eabe2a8, 0x1e4f43e470)


def _prefix_expand(prefix: str) -> list[int]:
    """Expand a CashAddr prefix into checksum input values."""
    return [ord(char) & 0x1f for char in prefix] + [0]


def _polymod(values: list[int]) -> int:
    """Return the CashAddr polymod checksum value."""
    checksum = 1
    for value in values:
        top = checksum >> 35
        checksum = ((checksum & 0x07ffffffff) << 5) ^ value
        for idx, generator in enumerate(GENERATOR):
            if top >> idx & 1:
                checksum ^= generator

    return checksum ^ 1


def _create_checksum(prefix: str, payload: list[int]) -> list[int]:
    """Create the 8-word CashAddr checksum for prefix and payload."""
    polymod = _polymod(_prefix_expand(prefix) + payload + [0] * 8)
    return [(polymod >> 5 * (7 - idx)) & 31 for idx in range(8)]


def cashaddr_encode(prefix: str, version: bytes, data: bytes) -> str:
    """Encode a BCH P2PKH/P2SH 20-byte hash as CashAddr."""
    if len(prefix) == 0 or len(version) != 1 or version[0] not in {0, 8} or len(data) != 20:
        raise ValueError('Invalid CashAddr data')
    try:
        payload = bech32.convertbits(version + data, 8, 5)
    except ValueError as e:
        raise ValueError('Invalid CashAddr data') from e
    if payload is None:
        raise ValueError('Invalid CashAddr data')

    try:
        checksum = _create_checksum(prefix, payload)
    except ValueError as e:
        raise ValueError('Invalid CashAddr data') from e
    return prefix + ':' + ''.join(CHARSET[value] for value in payload + checksum)


def cashaddr_decode(prefix: str, address: str) -> tuple[bytes, bytes]:
    """Decode a BCH CashAddr into version byte and 20-byte hash."""
    if len(prefix) == 0 or (address.upper() != address and address.lower() != address):
        raise ValueError('Invalid CashAddr data')

    address = address.lower()
    if ':' not in address:
        address = prefix + ':' + address

    hrp, encoded = address.split(':', maxsplit=1)
    if hrp != prefix or len(encoded) < 8 or not all(char in CHARSET for char in encoded):
        raise ValueError('Invalid CashAddr data')

    payload_with_checksum = [CHARSET.find(char) for char in encoded]
    try:
        is_valid_checksum = _polymod(_prefix_expand(hrp) + payload_with_checksum) == 0
    except ValueError as e:
        raise ValueError('Invalid CashAddr data') from e
    if not is_valid_checksum:
        raise ValueError('Invalid CashAddr data')

    payload_5bit = payload_with_checksum[:-8]
    try:
        payload = bech32.convertbits(payload_5bit, 5, 8, False)
    except ValueError as e:
        raise ValueError('Invalid CashAddr data') from e
    if len(payload_5bit) == 0 or payload is None or len(payload) != 21 or payload[0] not in {0, 8}:
        raise ValueError('Invalid CashAddr data')

    return bytes([payload[0]]), bytes(payload[1:])
