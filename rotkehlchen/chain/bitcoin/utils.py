import hashlib
import logging
import platform
from enum import Enum, auto
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import bech32
import requests

from rotkehlchen.chain.bitcoin.bch.validation import is_valid_bitcoin_cash_address
from rotkehlchen.chain.bitcoin.secp256k1 import PublicKey
from rotkehlchen.chain.bitcoin.segwit import encode_segwit_address
from rotkehlchen.chain.bitcoin.validation import is_valid_btc_address
from rotkehlchen.constants.timing import GLOBAL_REQUESTS_TIMEOUT
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp, ensure_type
from rotkehlchen.types import BTCAddress
from rotkehlchen.utils.base58 import b58encode
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get, request_get_dict, retry_calls

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.fval import FVal
    from rotkehlchen.types import SupportedBlockchain, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BIP32_HARDEN: int = 0x80000000


class WitnessVersion(Enum):
    """This represents the version represents the version of the Segwit address."""
    BECH32 = auto()  # version byte of 0
    BECH32M = auto()  # version byte of 1


class OpCodes(bytes, Enum):
    """Bitcoin script opcodes.
    Only those used in our code are included here.
    See https://learnmeabitcoin.com/technical/script/#opcodes for a complete list.
    """
    # Push data
    OP_0 = b'\x00'
    OP_1 = b'\x51'
    OP_16 = b'\x60'
    OP_PUSHDATA1 = b'\x4c'
    OP_PUSHDATA2 = b'\x4d'
    OP_PUSHDATA4 = b'\x4e'
    # Control flow
    OP_RETURN = b'\x6a'
    # Stack operators
    OP_DUP = b'\x76'
    # Bitwise logic
    OP_EQUAL = b'\x87'
    OP_EQUALVERIFY = b'\x88'
    # Cryptography
    OP_HASH160 = b'\xa9'
    OP_CHECKSIG = b'\xac'


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
    return BTCAddress(b58encode(prefixed_hash + checksum[:4]).decode('ascii'))


def pubkey_to_p2sh_p2wpkh_address(data: bytes) -> BTCAddress:
    """Bitcoin pubkey to PS2H-P2WPKH

    From here:
    https://bitcoin.stackexchange.com/questions/75910/how-to-generate-a-native-segwit-address-and-p2sh-segwit-address-from-a-standard
    """
    witprog = hash160(data)
    script = bytes.fromhex('0014') + witprog

    prefix = b'\x05'  # this is mainnet prefix -- we don't care about testnet
    prefixed_hash, checksum = _calculate_hash160_and_checksum(prefix, script)
    address = b58encode(prefixed_hash + checksum[:4])
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
            result = encode_segwit_address('bc', 0, hash160(PublicKey(data).format()))
        else:
            result = encode_segwit_address('bc', 1, PublicKey(data).taproot_output_key())
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
                "Derivation paths accepted by rotki should have no hardened nodes. Meaning no nodes with a '",  # noqa: E501
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
        data[0:1] != OpCodes.OP_DUP or
        data[1:2] != OpCodes.OP_HASH160 or
        data[-2:-1] != OpCodes.OP_EQUALVERIFY or
        data[-1:] != OpCodes.OP_CHECKSIG
    ):
        raise EncodingError(f'Invalid P2PKH scriptpubkey: {data.hex()}')

    prefixed_hash = bytes.fromhex('00') + data[3:23]  # 20 byte pubkey hash
    checksum = hashlib.sha256(hashlib.sha256(prefixed_hash).digest()).digest()
    address = b58encode(prefixed_hash + checksum[:4])
    return BTCAddress(address.decode('ascii'))


def scriptpubkey_to_p2pk_address(data: bytes) -> BTCAddress:
    """Return the P2PKH address of the public key in a P2PK scriptpubkey. That is how the
    explorers which support P2PK report such TxIOs, and how a user tracks the coins.

    P2PK: <pubkey length> <pubkey> OP_CHECKSIG, with a 33 byte compressed or a 65 byte
    uncompressed public key.

    May raise EncodingError if the scriptpubkey is invalid.
    """
    pubkey_length = data[0] if len(data) != 0 else 0
    if (
        pubkey_length not in (33, 65) or
        len(data) != pubkey_length + 2 or
        data[-1:] != OpCodes.OP_CHECKSIG
    ):
        raise EncodingError(f'Invalid P2PK scriptpubkey: {data.hex()}')

    return pubkey_to_base58_address(data[1:-1])


def scriptpubkey_to_p2sh_address(data: bytes) -> BTCAddress:
    """Return a P2SH address given a scriptpubkey

    P2SH: OP_HASH160 <scriptHash> OP_EQUAL
    """
    if data[0:1] != OpCodes.OP_HASH160 or data[-1:] != OpCodes.OP_EQUAL:
        raise EncodingError(f'Invalid P2SH scriptpubkey: {data.hex()}')

    prefixed_hash = bytes.fromhex('05') + data[2:22]  # 20 byte pubkey hash
    checksum = hashlib.sha256(hashlib.sha256(prefixed_hash).digest()).digest()
    address = b58encode(prefixed_hash + checksum[:4])
    return BTCAddress(address.decode('ascii'))


def scriptpubkey_to_bech32_address(data: bytes) -> BTCAddress:
    """Return a native SegWit (bech32) address given a scriptpubkey"""
    version = data[0]
    if OpCodes.OP_1 <= data[0:1] <= OpCodes.OP_16:
        version -= 0x50
    elif data[0:1] != OpCodes.OP_0:
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

    if first_op_code == OpCodes.OP_DUP:
        return scriptpubkey_to_p2pkh_address(data)

    if first_op_code == OpCodes.OP_HASH160:
        return scriptpubkey_to_p2sh_address(data)

    return scriptpubkey_to_bech32_address(data)


def query_blockstream_like_blockheight(base_url: str) -> int:
    """
    Query blockheight from APIs similar to blockstream.info
    Returns the blockheight
    May raise:
    - RemoteError if got problems with querying the API
    """
    if (response := retry_calls(
        times=CachedSettings().get_query_retry_limit(),
        location='bitcoin',
        handle_429=True,
        backoff_in_seconds=4,
        method_name='query_blockstream_like_height',
        function=requests.get,
        # function's arguments
        url=(url := f'{base_url}/blocks/tip/height'),
        timeout=GLOBAL_REQUESTS_TIMEOUT,
    )).status_code != HTTPStatus.OK:
        raise RemoteError(
            f'{url} returned status: {response.status_code} with message: {response.text}')

    log.debug(f'Got response: {response.text} from {base_url}/blocks/tip/height')
    return int(response.text)


def query_blockstream_like_account_info(
        base_url: str,
        account: BTCAddress,
) -> tuple[FVal, int]:
    """Query account info from APIs similar to blockstream.info
    Returns the account balance and tx count in a tuple.
    May raise:
    - RemoteError if got problems with querying the API
    - UnableToDecryptRemoteData if unable to load json in request_get
    - KeyError if got unexpected json structure
    - DeserializationError if got unexpected json values
    """
    response_data = request_get_dict(
        url=f'{base_url}/address/{account}',
        handle_429=True,
        backoff_in_seconds=4,
    )
    stats = response_data['chain_stats']
    funded_txo_sum = satoshis_to_btc(ensure_type(
        symbol=stats['funded_txo_sum'],
        expected_type=int,
        location='blockstream-like API funded_txo_sum',
    ))
    spent_txo_sum = satoshis_to_btc(ensure_type(
        symbol=stats['spent_txo_sum'],
        expected_type=int,
        location='blockstream-like API spent_txo_sum',
    ))
    return funded_txo_sum - spent_txo_sum, stats['tx_count']


def query_blockstream_like_balances(
        base_url: str,
        accounts: Sequence[BTCAddress],
) -> dict[BTCAddress, FVal]:
    """Query balances from APIs similar to blockstream.info"""
    balances = {}
    for account in accounts:
        balance, _ = query_blockstream_like_account_info(base_url, account)
        balances[account] = balance
    return balances


def query_blockstream_like_has_transactions(
        base_url: str,
        accounts: Sequence[BTCAddress],
) -> dict[BTCAddress, tuple[bool, FVal]]:
    """Query if accounts have transactions from APIs similar to blockstream.info"""
    have_transactions = {}
    for account in accounts:
        balance, tx_count = query_blockstream_like_account_info(base_url, account)
        have_transactions[account] = ((tx_count != 0), balance)
    return have_transactions


def query_mempool_address_transactions(
        base_url: str,
        address: BTCAddress,
        last_queried_block: int,
        progress_callback: Callable[[Timestamp], None] | None = None,
) -> list[dict[str, Any]]:
    """Query the transactions of an address from a mempool api (mempool.space or an instance
    of the user), newest to oldest, following the pagination until a page ends at or below
    `last_queried_block`. Mempool entries come first and are returned too; the caller
    skips them like it drops the transactions of the last page that are already known.

    Pages are followed via `after_txid`, which both backends of mempool support. Esplora's
    `/txs/chain/{txid}` is not served by an instance on an electrum backend. The page size
    can't be relied on either: mempool.space serves 25 transactions per page but an
    electrum backend serves 10, so only an empty page ends the history. An electrum
    backend serves the first page again when the cursor is the newest transaction of the
    address, so a page repeating a transaction ends the history too.

    Note that mempool indexes transactions by scriptpubkey, so a transaction touching the
    address only through a P2PK script is not part of its history.

    May raise:
    - RemoteError if got problems with querying the API
    - UnableToDecryptRemoteData if unable to load json in request_get
    - KeyError if got unexpected json structure
    - DeserializationError if got unexpected json values
    """
    txs: list[dict[str, Any]] = []
    seen_tx_ids: set[str] = set()
    url = f'{base_url}/address/{address}/txs'
    while True:
        if not isinstance(page := request_get(
            url=url,
            timeout=CachedSettings().get_timeout_tuple(),
            handle_429=True,
            backoff_in_seconds=4,
        ), list):
            raise RemoteError(f'{url} returned unexpected data. Response is not a list: {page}')

        if len(page) == 0 or page[0]['txid'] in seen_tx_ids:
            return txs

        txs.extend(page)
        seen_tx_ids.update(tx['txid'] for tx in page)
        if (status := (last_tx := page[-1])['status']).get('confirmed') is True:
            _report_mempool_query_progress(progress_callback, last_tx)
            if ensure_type(
                symbol=status['block_height'],
                expected_type=int,
                location='mempool API block_height',
            ) <= last_queried_block:
                return txs

        url = f'{base_url}/address/{address}/txs?after_txid={last_tx["txid"]}'


def _report_mempool_query_progress(
        progress_callback: Callable[[Timestamp], None] | None,
        tx: dict[str, Any],
) -> None:
    """Report the oldest transaction of a fetched mempool page, when available."""
    if progress_callback is None:
        return

    try:
        progress_callback(deserialize_timestamp(tx['status']['block_time']))
    except (DeserializationError, KeyError, ValueError) as e:
        log.debug('Unable to report mempool query progress due to %s', e)


def is_valid_bitcoin_address(chain: SupportedBlockchain, value: str) -> bool:
    """
    Returns False only if `chain` is a Bitcoin chain and `value` is an
    invalid address; otherwise returns True.
    """
    return (
        not chain.is_bitcoin() or
        (is_valid_btc_address(value) or is_valid_bitcoin_cash_address(value))
    )
