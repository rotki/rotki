"""Small Bech32/Bech32m helpers for Bitcoin SegWit addresses.

This module builds on the existing `bech32` dependency, which packages Pieter Wuille's
MIT-licensed reference implementation for BIP173 Bech32. Bech32m handling is implemented
from BIP350 by using the BIP350 checksum constant with the same polymod algorithm.

Added to rotki using Codex and ChatGPT 5.5.
"""

from typing import Final

import bech32

CHARSET: Final = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
BECH32_CONST: Final = 1
BECH32M_CONST: Final = 0x2bc830a3


def _checksum_constant(address: str) -> int | None:
    """Return the Bech32 checksum constant for address, if structurally valid."""
    if (
        any(ord(char) < 33 or ord(char) > 126 for char in address) or
        (address.lower() != address and address.upper() != address)
    ):
        return None

    address = address.lower()
    if (pos := address.rfind('1')) < 1 or pos + 7 > len(address):
        return None
    if not all(char in CHARSET for char in address[pos + 1:]):
        return None

    values = [CHARSET.find(char) for char in address[pos + 1:]]
    return bech32.bech32_polymod(bech32.bech32_hrp_expand(address[:pos]) + values)


def encode_segwit_address(hrp: str, witness_version: int, witness_program: bytes) -> str:
    """Encode a SegWit witness program as Bech32 or Bech32m."""
    if (
        len(hrp) == 0 or
        not 0 <= witness_version <= 16 or
        not 2 <= len(witness_program) <= 40 or
        (witness_version == 0 and len(witness_program) not in {20, 32})
    ):
        raise ValueError('Invalid SegWit address data')

    try:
        converted = bech32.convertbits(witness_program, 8, 5)
    except ValueError as e:
        raise ValueError('Invalid SegWit address data') from e
    if converted is None:
        raise ValueError('Invalid SegWit address data')

    data = [witness_version] + converted
    const = BECH32_CONST if witness_version == 0 else BECH32M_CONST
    values = bech32.bech32_hrp_expand(hrp) + data
    polymod = bech32.bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
    checksum = [(polymod >> 5 * (5 - idx)) & 31 for idx in range(6)]
    return hrp + '1' + ''.join(CHARSET[value] for value in data + checksum)


def is_valid_bech32m_segwit_address(hrp: str, address: str) -> bool:
    """Return whether address is a valid Bech32m SegWit address for hrp."""
    if _checksum_constant(address) != BECH32M_CONST:
        return False

    address = address.lower()
    data = [CHARSET.find(char) for char in address[address.rfind('1') + 1:-6]]
    if (
        not address.startswith(hrp + '1') or
        len(data) == 0 or
        data[0] > 16 or
        (decoded := bech32.convertbits(data[1:], 5, 8, False)) is None or
        not 2 <= len(decoded) <= 40
    ):
        return False

    return data[0] != 0
