import hashlib
import platform
from enum import Enum, auto
from typing import Any

import base58check
import bech32
from bip_utils import Bech32ChecksumError, P2TRAddrEncoder, P2WPKHAddrEncoder, SegwitBech32Decoder

from rotkehlchen.errors.serialization import EncodingError
from rotkehlchen.types import BTCAddress

BIP32_HARDEN: int = 0x80000000


class WitnessVersion(Enum):
    """This represents the version represents the version of the Segwit address."""
    BECH32 = auto()  # version byte of 0
    BECH32M = auto()  # version byte of 1


class OpCodes:
    op_0 = b'\x00'
    op_1 = b'\x51'
    op_16 = b'\x60'
    op_dup = b'\x76'
    op_equal = b'\x87'
    op_equalverify = b'\x88'
    op_hash160 = b'\xa9'
    op_checksig = b'\xac'
    op_return = b'\x6a'


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


if platform.system() == 'Linux':
    from .ripemd160 import ripemd160
    def hash160(msg: bytes) -> bytes:
        return ripemd160(hashlib.sha256(msg).digest())

else:
    def hash160(msg: bytes) -> bytes:
        h = hashlib.new('ripemd160')
        h.update(hashlib.sha256(msg).digest())
        return h.digest()


def _calculate_hash160_and_checksum(prefix: bytes, data: bytes) -> tuple[bytes, bytes]:
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
    https://web.archive.org/web/20210608034604/https://hackernoon.com/how-to-generate-bitcoin-addresses-technical-address-generation-explanation-rus3z9e

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
    prefixed_hash, checksum = _calculate_hash160_and_checksum(prefix, script)
    address = base58check.b58encode(prefixed_hash + checksum[:4])
    return BTCAddress(address.decode('ascii'))


def pubkey_to_bech32_address(data: bytes, witver: WitnessVersion) -> BTCAddress:
    """
    Bitcoin pubkey to native Segwit(P2WPKH) & Taproot(P2TR) addresses.
    `witver` represents the version of the Segwit address.
    0 -> BECH32 addresses
    >= 1 -> BECH32M addresses

    Source:
    https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#witness-program
    https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki

    May raise:
    - EncodingError if address could not be derived from public key
    """
    try:
        if witver == WitnessVersion.BECH32:
            result = P2WPKHAddrEncoder.EncodeKey(pub_key=data, hrp='bc')
        else:
            result = P2TRAddrEncoder.EncodeKey(pub_key=data, hrp='bc')
    except ValueError as e:
        raise EncodingError('Could not derive Bech32 address from given public key') from e
    return BTCAddress(result)


def is_valid_derivation_path(path: Any) -> tuple[bool, str]:
    """Check if a derivation path can be understood by rotki

    Returns False, "error message" if not and True, "" if yes
    """
    if not isinstance(path, str):
        return False, 'Derivation path should be a string'

    if not path.startswith('m'):
        return False, 'Derivation paths accepted by rotki should start with m'

    nodes: list[str] = path.split('/')
    if nodes[0] != 'm':
        return False, 'Derivation paths accepted by rotki should start with m'
    nodes = nodes[1:]

    for node in nodes:
        if "'" in node:
            return (
                False,
                'Derivation paths accepted by rotki should have no hardened '
                "nodes. Meaning no nodes with a '",
            )

        try:
            value = int(node)
        except ValueError:
            return False, f'Found non integer node {node} in xpub derivation path'

        if value < 0:
            return False, f'Found negative integer node {value} in xpub derivation path'

    return True, ''


def scriptpubkey_to_p2pkh_address(data: bytes) -> BTCAddress:
    """Return a P2PKH address given a scriptpubkey

    P2PKH: OP_DUP OP_HASH160 <pubKeyHash> OP_EQUALVERIFY OP_CHECKSIG
    """
    if (
        data[0:1] != OpCodes.op_dup or
        data[1:2] != OpCodes.op_hash160 or
        data[-2:-1] != OpCodes.op_equalverify or
        data[-1:] != OpCodes.op_checksig
    ):
        raise EncodingError(f'Invalid P2PKH scriptpubkey: {data.hex()}')

    prefixed_hash = bytes.fromhex('00') + data[3:23]  # 20 byte pubkey hash
    checksum = hashlib.sha256(hashlib.sha256(prefixed_hash).digest()).digest()
    address = base58check.b58encode(prefixed_hash + checksum[:4])
    return BTCAddress(address.decode('ascii'))


def scriptpubkey_to_p2sh_address(data: bytes) -> BTCAddress:
    """Return a P2SH address given a scriptpubkey

    P2SH: OP_HASH160 <scriptHash> OP_EQUAL
    """
    if data[0:1] != OpCodes.op_hash160 or data[-1:] != OpCodes.op_equal:
        raise EncodingError(f'Invalid P2SH scriptpubkey: {data.hex()}')

    prefixed_hash = bytes.fromhex('05') + data[2:22]  # 20 byte pubkey hash
    checksum = hashlib.sha256(hashlib.sha256(prefixed_hash).digest()).digest()
    address = base58check.b58encode(prefixed_hash + checksum[:4])
    return BTCAddress(address.decode('ascii'))


def scriptpubkey_to_bech32_address(data: bytes) -> BTCAddress:
    """Return a native SegWit (bech32) address given a scriptpubkey"""
    version = data[0]
    if OpCodes.op_1 <= data[0:1] <= OpCodes.op_16:
        version -= 0x50
    elif data[0:1] != OpCodes.op_0:
        raise EncodingError(f'Invalid bech32 scriptpubkey: {data.hex()}')

    address = bech32.encode('bc', version, data[2:])
    if not address:  # should not happen
        raise EncodingError('Could not derive bech32 address from given scriptpubkey')

    return BTCAddress(address)


def scriptpubkey_to_btc_address(data: bytes) -> BTCAddress:
    """Return a Bitcoin address given a scriptpubkey.
    Supported formats are: P2PKH, P2SH and native SegWit (bech32).

    May raise EncodingError if the scriptpubkey is invalid.
    """
    first_op_code = data[0:1]

    if first_op_code == OpCodes.op_dup:
        return scriptpubkey_to_p2pkh_address(data)

    if first_op_code == OpCodes.op_hash160:
        return scriptpubkey_to_p2sh_address(data)

    return scriptpubkey_to_bech32_address(data)
