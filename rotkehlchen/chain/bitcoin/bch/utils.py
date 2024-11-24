
import bech32
from base58 import b58encode_check
from eth_typing import ChecksumAddress
from marshmallow import ValidationError

from rotkehlchen.chain.bitcoin.utils import is_valid_base58_address
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
    return _polymod(_prefix_expand(prefix) + decoded) == 0


def _b32decode(inputs: str) -> list:
    return [_CHARSET.find(letter) for letter in inputs]


def _address_type(address_type: str, version: str | int) -> tuple[str, int, bool]:
    for mapping in _VERSION_MAP[address_type]:
        if version in (mapping[0], mapping[1]):
            return mapping
    raise ValueError('Invalid Address')


def _code_list_to_string(code_list: list[int]) -> bytes:
    output = b''
    for code in code_list:
        output += bytes([code])
    return output


def cash_to_legacy_address(address: str) -> BTCAddress | None:
    """
    Converts a legacy BCH address to CashAddr format.
    Code is taken from:
    https://github.com/oskyk/cashaddress/blob/master/cashaddress/convert.py#L46

    Returns None if an error occurred during conversion.
    """
    try:
        is_valid = is_valid_bitcoin_cash_address(address)
        if not is_valid:
            return None
        if address.startswith(_PREFIX) is False:
            address = _PREFIX + ':' + address

        _, base32string = address.split(':')
        decoded_string = _b32decode(base32string)
        converted_bits = bech32.convertbits(decoded_string, 5, 8)
        if converted_bits is None:
            return None
        version = _address_type('cash', converted_bits[0])[0]
        legacy_version = _address_type('legacy', version)[1]
        payload = converted_bits[1:-6]
        return BTCAddress(b58encode_check(
            _code_list_to_string([legacy_version] + payload),
        ).decode())
    except ValueError:
        return None


def force_address_to_legacy_address(address: str) -> BTCAddress:
    """
    Changes the format of a BCH address to Legacy.
    If address already in legacy format, return as is.
    """
    if is_valid_bitcoin_cash_address(address):
        addr = cash_to_legacy_address(address)
        if addr is not None:
            return addr
    return BTCAddress(address)


def force_addresses_to_legacy_addresses(data: set[ChecksumAddress]) -> set[BTCAddress]:
    """Changes the format of a set of addresses to Legacy."""
    return {force_address_to_legacy_address(entry) for entry in data}


def validate_bch_address_input(address: str, given_addresses: set[ChecksumAddress]) -> None:
    """Validates the address provided is valid for Bitcoin Cash.
    May raise ValidationError if all checks are not passed.
    """
    not_valid_address = (
        not address.endswith('.eth') and
        not (is_valid_bitcoin_cash_address(address) or is_valid_base58_address(address))
    )
    if not_valid_address:
        raise ValidationError(
            f'Given value {address} is not a valid bitcoin cash address',
            field_name='address',
        )
    # Check if they're not duplicates of same address but in different formats
    if force_address_to_legacy_address(address) in force_addresses_to_legacy_addresses(given_addresses):  # noqa: E501
        raise ValidationError(
            f'Address {address} appears multiple times in the request data',
            field_name='address',
        )
