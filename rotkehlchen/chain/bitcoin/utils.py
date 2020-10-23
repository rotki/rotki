import hashlib
from typing import Tuple

import base58check
import bech32

from rotkehlchen.errors import EncodingError
from rotkehlchen.typing import BTCAddress

BIP32_HARDEN: int = 0x80000000


def is_valid_btc_address(value: str) -> bool:
    return is_valid_base58_address(value) or is_valid_bech32_address(value)


def is_valid_bech32_address(value: str) -> bool:
    """Validates a bitcoin SegWit address for the mainnet
    """

    decoded = bech32.decode('bc', value)
    return decoded != (None, None)


def is_valid_base58_address(value: str) -> bool:
    """Validates a bitcoin base58 address for the mainnet

    Code is taken from:
    https://github.com/joeblackwaslike/coinaddr/blob/ae35c7ae550a687d9a7c2e0cb090d52edbb29cb5/coinaddr/validation.py#L67-L87

    """
    if 25 > len(value) > 35:
        return False

    try:
        abytes = base58check.b58decode(value)
    except (ValueError):
        return False

    if not abytes[0] in (0x00, 0x05):
        return False

    checksum = hashlib.sha256(hashlib.sha256(abytes[:-4]).digest()).digest()[:4]
    if abytes[-4:] != checksum:
        return False

    return value == base58check.b58encode(abytes).decode()


def hash160(msg: bytes) -> bytes:
    h = hashlib.new('ripemd160')
    h.update(hashlib.sha256(msg).digest())
    return h.digest()


def _calculate_hash160_and_checksum(prefix: bytes, data: bytes) -> Tuple[bytes, bytes]:
    """Calculates the prefixed hash160 and checksum"""
    s1 = prefix + hash160(data)
    s2 = hashlib.sha256(s1).digest()
    checksum = hashlib.sha256(s2).digest()

    return s1, checksum


def pubkey_to_base58_address(data: bytes) -> BTCAddress:
    """
    Bitcoin pubkey to base58 address

    Source:
    https://en.bitcoin.it/wiki/Technical_background_of_version_1_Bitcoin_addresses#How_to_create_Bitcoin_Address
    https://hackernoon.com/how-to-generate-bitcoin-addresses-technical-address-generation-explanation-rus3z9e

    May raise:
    - ValueError, TypeError due to b58encode
    """
    prefixed_hash, checksum = _calculate_hash160_and_checksum(b'\x00', data)
    return BTCAddress(base58check.b58encode(prefixed_hash + checksum[:4]).decode('ascii'))


def pubkey_to_p2sh_p2wpkh_address(data: bytes) -> BTCAddress:
    """Bitcoin pubkey to PS2H-P2WPKH

    From here:
    https://bitcoin.stackexchange.com/questions/75910/how-to-generate-a-native-segwit-address-and-p2sh-segwit-address-from-a-standard
    """
    witprog = hash160(data)
    script = bytes.fromhex('0014') + witprog

    prefix = b'\x05'  # this is mainnet prefix -- we don't care about testnet
    # prefixed_hash, checksum = _calculate_hash160_and_checksum(prefix, prefix + script)
    prefixed_hash, checksum = _calculate_hash160_and_checksum(prefix, script)
    # address = base58check.b58encode(prefix + prefixed_hash + checksum[:4])
    address = base58check.b58encode(prefixed_hash + checksum[:4])
    return BTCAddress(address.decode('ascii'))


def pubkey_to_bech32_address(data: bytes, witver: int) -> BTCAddress:
    """
    Bitcoin pubkey to bech32 address

    Source:
    https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#witness-program
    https://github.com/mcdallas/cryptotools/blob/master/btctools/address.py

    May raise:
    - EncodingError if address could not be derived from public key
    """
    witprog = hash160(data)
    result = bech32.encode('bc', witver, witprog)
    if not result:
        raise EncodingError('Could not derive bech32 address from given public key')

    return BTCAddress(result)
