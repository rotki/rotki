from typing import List, Optional, Set, Tuple

import bech32
from base58 import b58decode_check, b58encode_check
from eth_typing import ChecksumAddress

from rotkehlchen.types import BTCAddress

_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
_VERSION_MAP = {
    'legacy': [
        ('P2SH', 5, False),
        ('P2PKH', 0, False),
    ],
    'cash': [
        ('P2SH', 8, False),
        ('P2PKH', 0, False),
    ],
}
_PREFIX = 'bitcoincash'


def _polymod(values: list) -> int:
    chk = 1
    generator = [
        (0x01, 0x98f2bc8e61),
        (0x02, 0x79b76d99e2),
        (0x04, 0xf33e5fb3c4),
        (0x08, 0xae2eabe2a8),
        (0x10, 0x1e4f43e470)]
    for value in values:
        top = chk >> 35
        chk = ((chk & 0x07ffffffff) << 5) ^ value
        for i in generator:
            if top & i[0] != 0:
                chk ^= i[1]
    return chk ^ 1


def _prefix_expand(prefix: str) -> list:
    return [ord(x) & 0x1f for x in prefix] + [0]


def is_valid_bitcoin_cash_address(address: str) -> bool:
    """
    Validates a Bitcoin Cash's CashAddr format
    e.g bitcoincash:qpmmlusvvrjj9ha2xdgv8xcrpfwsqn5rngt3k26ve2

    Code is take from:
    https://github.com/oskyk/cashaddress/blob/master/cashaddress/convert.py#L125
    """
    if address.upper() != address and address.lower() != address:
        return False
    address = address.lower()
    colon_count = address.count(':')
    if colon_count == 0:
        address = _PREFIX + ':' + address
    elif colon_count > 1:
        return False
    prefix, base32string = address.split(':')
    decoded = _b32decode(base32string)
    if _polymod(_prefix_expand(prefix) + decoded) != 0:
        return False
    return True


def _b32decode(inputs: str) -> list:
    out = []
    for letter in inputs:
        out.append(_CHARSET.find(letter))
    return out


def b32encode(inputs: list) -> str:
    out = ''
    for char_code in inputs:
        out += _CHARSET[char_code]
    return out


def _address_type(address_type: str, version: int) -> Tuple[str, int, bool]:
    for mapping in _VERSION_MAP[address_type]:
        if version in (mapping[0], mapping[1]):
            return mapping
    return _VERSION_MAP[address_type][0]


def _calculate_checksum(prefix: str, payload: List[int]) -> list:
    poly = _polymod(_prefix_expand(prefix) + payload + [0, 0, 0, 0, 0, 0, 0, 0])
    out = []
    for i in range(8):
        out.append((poly >> 5 * (7 - i)) & 0x1f)
    return out


def _code_list_to_string(code_list: List[int]) -> bytes:
    output = b''
    for code in code_list:
        output += bytes([code])
    return output


def legacy_to_cash_address(address: str) -> Optional[str]:
    """
    Converts a legacy BCH address to CashAddr format.
    Code is taken from:
    https://github.com/oskyk/cashaddress/blob/master/cashaddress/convert.py#L46

    Returns None if an error occured during conversion.
    """
    decoded = bytearray(b58decode_check(address))
    version = _address_type('legacy', decoded[0])
    payload = []
    for letter in decoded[1:]:
        payload.append(letter)
    version_int = _address_type('cash', version[1])[1]
    payload = [version_int] + payload
    converted_bits = bech32.convertbits(payload, 8, 5)
    if converted_bits is None:
        return None
    checksum = _calculate_checksum(_PREFIX, converted_bits)
    return _PREFIX + ':' + b32encode(converted_bits + checksum)


def cash_to_legacy_address(address: str) -> Optional[BTCAddress]:
    """
    Converts a legacy BCH address to CashAddr format.
    Code is taken from:
    https://github.com/oskyk/cashaddress/blob/master/cashaddress/convert.py#L46

    Returns None if an error occured during conversion.
    """
    is_valid = is_valid_bitcoin_cash_address(address)
    if not is_valid:
        return None

    _, base32string = address.split(':')
    decoded_string = _b32decode(base32string)
    converted_bits = bech32.convertbits(decoded_string, 5, 8)
    if converted_bits is None:
        return None
    version_int = _address_type('cash', converted_bits[0])[1]
    payload = converted_bits[1:-6]
    return BTCAddress(b58encode_check(_code_list_to_string([version_int] + payload)).decode())


def force_address_to_legacy_address(address: str) -> BTCAddress:
    """
    Changes the format of a BCH address to Legacy.
    If address already in legacy format, return as is.

    This assumes that the address being passed is valid.
    """
    if ':' in address:
        addr = cash_to_legacy_address(address)
        if addr is not None:
            return addr
    return BTCAddress(address)


def force_addresses_to_legacy_addresses(data: Set[ChecksumAddress]) -> Set[BTCAddress]:
    """Changes the format of a list of addresses to Legacy."""
    return_data = set()
    for entry in data:
        return_data.add(force_address_to_legacy_address(entry))

    return return_data
