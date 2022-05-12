import base64
import random
import string
from typing import List, Optional, Tuple

from eth_utils.address import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ChecksumEthAddress,
    EthereumTransaction,
    Location,
    Timestamp,
    TimestampMS,
    make_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now

DEFAULT_START_TS = Timestamp(1451606400)


def make_random_bytes(size: int) -> bytes:
    return bytes(bytearray(random.getrandbits(8) for _ in range(size)))


def make_random_b64bytes(size: int) -> bytes:
    return base64.b64encode(make_random_bytes(size))


def make_random_uppercasenumeric_string(size: int) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=size))


def make_random_positive_fval(max_num: int = 1000000) -> FVal:
    return FVal(random.uniform(0, max_num))


def make_random_timestamp(
        start: Optional[Timestamp] = DEFAULT_START_TS,
        end: Optional[Timestamp] = None,
) -> Timestamp:
    if end is None:
        end = ts_now()
    if start is None:
        start = DEFAULT_START_TS
    return Timestamp(random.randint(start, end))


def make_api_key() -> ApiKey:
    return ApiKey(make_random_b64bytes(128).decode())


def make_api_secret() -> ApiSecret:
    return ApiSecret(base64.b64encode(make_random_b64bytes(128)))


def make_ethereum_address() -> ChecksumEthAddress:
    return to_checksum_address('0x' + make_random_bytes(20).hex())


def make_ethereum_transaction(tx_hash: Optional[bytes] = None) -> EthereumTransaction:
    if tx_hash is None:
        tx_hash = make_random_bytes(42)
    return EthereumTransaction(
        tx_hash=make_evm_tx_hash(tx_hash),
        timestamp=Timestamp(0),
        block_number=0,
        from_address=make_ethereum_address(),
        to_address=make_ethereum_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    )


def make_ethereum_event(
    index: int,
    tx_hash: Optional[bytes] = None,
    asset: Asset = A_USD,
    counterparty: Optional[str] = None,
) -> HistoryBaseEntry:
    if tx_hash is None:
        tx_hash = make_random_bytes(42)
    return HistoryBaseEntry(
        event_identifier=make_evm_tx_hash(tx_hash).hex(),  # pylint: disable=no-member
        sequence_index=index,
        identifier=index,
        timestamp=TimestampMS(0),
        location=Location.KRAKEN,
        event_type=HistoryEventType.UNKNOWN,
        event_subtype=HistoryEventSubType.NONE,
        asset=asset,
        balance=Balance(amount=ONE, usd_value=ONE),
        counterparty=counterparty,
    )


def generate_tx_entries_response(
    data: List[Tuple[EthereumTransaction, List[HistoryBaseEntry]]],
) -> List:
    result = []
    for tx, events in data:
        decoded_events = []
        for event in events:
            decoded_events.append({
                'entry': event.serialize(),
                'customized': False,
            })
        result.append({
            'entry': tx.serialize(),
            'decoded_events': decoded_events,
            'ignored_in_accounting': False,
        })
    return result


UNIT_BTC_ADDRESS1 = '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'
UNIT_BTC_ADDRESS2 = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'
UNIT_BTC_ADDRESS3 = '18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2'

ZERO_ETH_ADDRESS = string_to_ethereum_address('0x' + '0' * 40)
