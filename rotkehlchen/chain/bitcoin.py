from hashlib import sha256

import base58check


def is_valid_btc_address(value: str) -> bool:
    """Validates a bitcoin address for the mainnet

    Code is taken from:
    https://github.com/joeblackwaslike/coinaddr/blob/ae35c7ae550a687d9a7c2e0cb090d52edbb29cb5/coinaddr/validation.py#L67-L87

    """
    if 25 > len(value) > 35:
        return False

    abytes = base58check.b58decode(value)
    if not abytes[0] in (0x00, 0x05):
        return False

    checksum = sha256(sha256(abytes[:-4]).digest()).digest()[:4]
    if abytes[-4:] != checksum:
        return False

    return value == base58check.b58encode(abytes).decode()
