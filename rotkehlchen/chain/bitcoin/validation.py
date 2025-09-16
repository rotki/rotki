import hashlib

import base58check
import bech32
from bip_utils import Bech32ChecksumError, SegwitBech32Decoder


def is_valid_btc_address(value: str) -> bool:
    """Validates a bitcoin address.

    The major difference between `is_valid_bech32_address` and `is_valid_bech32_bech32m_address`
    is that they validate two different BIPs specification and they're needed to maintain
    backward compatibility.
    """
    return (
        is_valid_base58_address(value) or
        is_valid_bech32_address(value) or
        is_valid_bech32_bip350_address(value)
    )


def is_valid_bech32_address(value: str) -> bool:
    """Validates a bitcoin Segwit address using BIP-173
    https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki
    """
    decoded = bech32.decode('bc', value)
    return decoded != (None, None)


def is_valid_bech32_bip350_address(value: str) -> bool:
    """Validates a bitcoin Segwit address using BIP-350.

    This validation is based on BIP-350 which improves on a flaw in BIP-173
    https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki
    """
    try:
        SegwitBech32Decoder.Decode('bc', value)
    except (ValueError, Bech32ChecksumError):
        return False
    else:
        return True


def is_valid_base58_address(value: str) -> bool:
    """Validates a bitcoin base58 address for the mainnet

    Code is taken from:
    https://github.com/joeblackwaslike/coinaddr/blob/ae35c7ae550a687d9a7c2e0cb090d52edbb29cb5/coinaddr/validation.py#L67-L87
    """
    if 25 > len(value) > 35:
        return False

    try:
        abytes = base58check.b58decode(value)
    except ValueError:
        return False

    if len(abytes) == 0 or abytes[0] not in {0x00, 0x05}:
        return False

    checksum = hashlib.sha256(hashlib.sha256(abytes[:-4]).digest()).digest()[:4]
    if abytes[-4:] != checksum:
        return False

    return value == base58check.b58encode(abytes).decode()
