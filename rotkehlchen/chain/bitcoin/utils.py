import hashlib
import platform
import logging
from collections.abc import Callable
from collections.abc import Sequence
from enum import Enum, auto
from typing import Any

import base58check
import bech32
import requests
from bip_utils import (
    Bech32ChecksumError,
    P2TRAddrEncoder,
    SegwitBech32Decoder,
    Secp256k1PublicKey,
    P2PKHAddrEncoder,
    P2WPKHAddrEncoder,
)

from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
from rotkehlchen.serialization.deserialize import ensure_type
from rotkehlchen.types import BTCAddress, FVal
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get_dict, request_get
from rotkehlchen.logging import RotkehlchenLogsAdapter
from .constants import BLOCKSTREAM_BASE_URL, MEMPOOL_SPACE_BASE_URL
from .types import string_to_btc_address

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

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


def query_apis_via_callbacks(api_callbacks: dict[str, Callable], *args, **kwargs):
    errors: dict[str, str] = {}
    for api_name, callback in api_callbacks.items():
        try:
            return callback(*args, **kwargs)
        except (
            requests.exceptions.RequestException,
            UnableToDecryptRemoteData,
            requests.exceptions.Timeout,
            RemoteError,
            DeserializationError,
        ) as e:
            errors[api_name] = str(e)
            continue
        except KeyError as e:
            errors[api_name] = f"Got unexpected response from {api_name}. Couldn't find key {e!s}"

    serialized_errors = ', '.join(f'{source} error is: "{error}"' for (source, error) in errors.items())  # noqa: E501
    raise RemoteError(f'Bitcoin external API request for balances failed. {serialized_errors}')


def query_blockstream_or_mempool_api(url_suffix: str) -> dict | list:
    return query_apis_via_callbacks(
        api_callbacks={
            'blockstream.info': lambda: request_get(f'{BLOCKSTREAM_BASE_URL}/{url_suffix}'),
            'mempool.space': lambda: request_get(f'{MEMPOOL_SPACE_BASE_URL}/{url_suffix}'),
        },
    )


def have_bc1_accounts(accounts: Sequence[BTCAddress]) -> bool:
    return any(account.lower()[0:3] == 'bc1' for account in accounts)


def _check_blockstream_for_transactions(
        accounts: list[BTCAddress],
) -> dict[BTCAddress, tuple[bool, FVal]]:
    """May raise:
    - RemoteError if couldn't query
    - KeyError if response structure differs from the expected one
    - DeserializationError if response values differ from the expected
    """
    have_transactions = {}
    for account in accounts:
        url = f'https://blockstream.info/api/address/{account}'
        response_data = request_get_dict(url=url, handle_429=True, backoff_in_seconds=4)
        stats = response_data['chain_stats']
        funded_txo_sum = satoshis_to_btc(
            ensure_type(
                symbol=stats['funded_txo_sum'],
                expected_type=int,
                location='blockstream funded_txo_sum',
            ),
        )
        spent_txo_sum = satoshis_to_btc(
            ensure_type(
                symbol=stats['spent_txo_sum'],
                expected_type=int,
                location='blockstream spent_txo_sum',
            ),
        )
        balance = funded_txo_sum - spent_txo_sum
        have_txs = stats['tx_count'] != 0
        have_transactions[account] = (have_txs, balance)

    return have_transactions


def _check_blockchaininfo_for_transactions(
        accounts: list[BTCAddress],
) -> dict[BTCAddress, tuple[bool, FVal]]:
    """May raise RemoteError or KeyError"""
    have_transactions = {}
    params = '|'.join(accounts)
    btc_resp = request_get_dict(
        url=f'https://blockchain.info/multiaddr?active={params}',
        handle_429=True,
        # If we get a 429 then their docs suggest 10 seconds
        # https://blockchain.infoq/
        backoff_in_seconds=15,
    )
    for entry in btc_resp['addresses']:
        balance = satoshis_to_btc(entry['final_balance'])
        have_transactions[entry['address']] = (entry['n_tx'] != 0, balance)

    return have_transactions


def have_bitcoin_transactions(accounts: list[BTCAddress]) -> dict[BTCAddress, tuple[bool, FVal]]:
    """
    Takes a list of addresses and returns a mapping of which addresses have had transactions
    and also their current balance

    May raise:
    - RemoteError if any of the queried websites fail to be queried
    """
    try:
        if have_bc1_accounts(accounts):
            have_transactions = _check_blockstream_for_transactions(accounts)
        else:
            have_transactions = _check_blockchaininfo_for_transactions(accounts)
    except (
            requests.exceptions.RequestException,
            UnableToDecryptRemoteData,
            requests.exceptions.Timeout,
    ) as e:
        raise RemoteError(f'bitcoin external API request for transactions failed due to {e!s}') from e  # noqa: E501
    except KeyError as e:
        raise RemoteError(
            'Malformed response when querying the bitcoin blockchain.'
            f'Did not find key {e!s}',
        ) from e
    except DeserializationError as e:
        raise RemoteError(f"Couldn't read data from the response due to {e!s}") from e

    return have_transactions


def derive_p2pkh_from_p2pk(pubkey_hex) -> BTCAddress:
    """Convert P2PK public key to a p2pkh public key hash (normal bitcoin address)."""
    pub_key = Secp256k1PublicKey.FromBytes(bytes.fromhex(pubkey_hex))
    return string_to_btc_address(P2PKHAddrEncoder.EncodeKey(pub_key))
