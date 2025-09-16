from typing import Literal

from base58 import b58decode_check, b58encode_check
from bip_utils.bech32.bch_bech32 import BchBech32Decoder, BchBech32Encoder
from eth_typing import ChecksumAddress
from marshmallow import ValidationError

from rotkehlchen.chain.bitcoin.bch.constants import CASHADDR_PREFIX
from rotkehlchen.chain.bitcoin.bch.validation import is_valid_bitcoin_cash_address
from rotkehlchen.chain.bitcoin.validation import is_valid_base58_address
from rotkehlchen.types import BTCAddress


def convert_version(version: int, target_type: Literal['legacy', 'cash']) -> int:
    """Converts a bch address version integer between legacy and cash.
    For the original version map see:
    https://github.com/oskyk/cashaddress/blob/master/cashaddress/convert.py#L11
    """
    if version == 0:  # p2pk - version is 0 for both legacy and cash
        return 0
    elif version in (5, 8):  # p2sh - version is 5 for legacy, 8 for cash
        return 5 if target_type == 'legacy' else 8
    else:
        raise ValueError('Invalid Address')


def cash_to_legacy_address(address: str) -> BTCAddress | None:
    """Converts a CashAddr BCH address to legacy format.
    Returns None if an error occurred during conversion.
    """
    try:
        if not is_valid_bitcoin_cash_address(address):
            return None
        if not address.startswith(CASHADDR_PREFIX):
            address = CASHADDR_PREFIX + ':' + address

        version, data = BchBech32Decoder.Decode(hrp=CASHADDR_PREFIX, addr=address)
        legacy_version = convert_version(
            version=int.from_bytes(version),
            target_type='legacy',
        )
        return BTCAddress(b58encode_check(bytes([legacy_version]) + data).decode())
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


def legacy_to_cash_address(address: str) -> BTCAddress | None:
    """Convert a legacy BCH address to CashAddr format.
    Returns None if an error occurred during conversion.
    """
    if not is_valid_base58_address(address):
        return None

    try:
        decoded = b58decode_check(address)
        cash_version = convert_version(version=decoded[0], target_type='cash')
        return BTCAddress(BchBech32Encoder.Encode(
            hrp=CASHADDR_PREFIX,
            net_ver=bytes([cash_version]),
            data=decoded[1:],
        ))
    except ValueError:
        return None


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
