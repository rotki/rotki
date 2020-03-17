from hashlib import sha256

import base58check
import bech32


def is_valid_btc_address(value: str) -> bool:
    return is_valid_base58_address(value) or is_valid_bech32_address(value)


def is_valid_bech32_address(value: str) -> bool:
    """Validates a bitcoin Bech32 address for the mainnet

    """

    (hrp, _) = bech32.bech32_decode(value)
    return hrp is not None and hrp == 'bc'


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

    checksum = sha256(sha256(abytes[:-4]).digest()).digest()[:4]
    if abytes[-4:] != checksum:
        return False

    return value == base58check.b58encode(abytes).decode()
