import base64
import random
import string
from typing import Any, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    AddressbookEntry,
    ApiKey,
    ApiSecret,
    AssetAmount,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
    Fee,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    TradeType,
    deserialize_evm_tx_hash,
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


def make_evm_address() -> ChecksumEvmAddress:
    return to_checksum_address('0x' + make_random_bytes(20).hex())


def make_evm_tx_hash() -> EVMTxHash:
    return deserialize_evm_tx_hash(make_random_bytes(32))


def make_ethereum_transaction(
        tx_hash: Optional[bytes] = None,
        timestamp: Optional[Timestamp] = None,
) -> EvmTransaction:
    if tx_hash is None:
        tx_hash = make_random_bytes(42)
    timestamp = timestamp if timestamp is not None else Timestamp(0)
    return EvmTransaction(
        tx_hash=deserialize_evm_tx_hash(tx_hash),
        chain_id=ChainID.ETHEREUM,
        timestamp=timestamp,
        block_number=0,
        from_address=make_evm_address(),
        to_address=make_evm_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    )


CUSTOM_USDT = EvmToken.initialize(
    address=string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
    chain_id=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    name='Tether',
    symbol='USDT',
    started=Timestamp(1402358400),
    forked=None,
    swapped_for=None,
    coingecko='tether',
    cryptocompare=None,
    decimals=6,
    protocol=None,
)


def make_ethereum_event(
        index: int,
        tx_hash: Optional[bytes] = None,
        location_label: Optional[str] = None,
        asset: CryptoAsset = CUSTOM_USDT,
        counterparty: Optional[str] = None,
        event_type: HistoryEventType = HistoryEventType.UNKNOWN,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        timestamp: TimestampMS = 0,  # type: ignore
) -> EvmEvent:
    if tx_hash is None:
        tx_hash = make_random_bytes(32)
    return EvmEvent(
        tx_hash=deserialize_evm_tx_hash(tx_hash),
        sequence_index=index,
        location_label=location_label,
        identifier=index,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        balance=Balance(amount=ONE, usd_value=ONE),
        counterparty=counterparty,
    )


def generate_events_response(
        data: list['EvmEvent'],
) -> list:
    result = []
    for event in data:
        result.append({
            'entry': event.serialize(),
        })
    return result


def make_addressbook_entries() -> list[AddressbookEntry]:
    return [
        AddressbookEntry(
            address=to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
            name='My dear friend Fred',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67'),
            name='Neighbour Thomas',
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        AddressbookEntry(
            address=to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67'),
            name='Neighbour Thomas but in Ethereum',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=to_checksum_address('0x3D61AEBB1238062a21BE5CC79df308f030BF0c1B'),
            name='Secret agent Rose',
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
    ]


def make_user_notes_entries() -> list[dict[str, Any]]:
    return [
        {
            'title': 'TODO List',
            'content': '*Sleep*  *Wake Up!*',
            'location': 'manual balances',
            'is_pinned': False,
        },
        {
            'title': 'Coins Watchlist #1',
            'content': '$NEAR $SCRT $ETH $BTC $AVAX',
            'location': 'ledger actions',
            'is_pinned': False,
        },
        {
            'title': 'Programming Languages',
            'content': '-Python -GoLang -Haskell -OCaml -Dart -Rust',
            'location': 'manual balances',
            'is_pinned': False,
        },
    ]


def make_random_user_notes(num_notes: int) -> list[dict[str, Any]]:
    """Make random user notes to be used in tests"""
    notes = []
    for note_number in range(num_notes):
        notes.append(
            {
                'title': f'Note #{note_number + 1}',
                'content': 'I am a random note',
                'location': 'manual balances',
                'is_pinned': random.choice([True, False]),
            },
        )
    return notes


def make_random_trades(num_trades: int) -> list[Trade]:
    """Make random trades to be used in tests."""
    trades = []
    for idx in range(num_trades):
        trade_type = random.choice([TradeType.BUY, TradeType.SELL])
        trades.append(
            Trade(
                timestamp=Timestamp(random.randint(100000, 10000000)),
                trade_type=trade_type,
                location=Location.EXTERNAL,
                base_asset=A_ETH,
                quote_asset=A_USDC,
                amount=AssetAmount(FVal(idx)),
                rate=Price(FVal(idx)),
                fee=Fee(ZERO),
                fee_currency=A_USDC,
                link='',
                notes='',
            ),
        )
    return trades


UNIT_BTC_ADDRESS1 = '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'
UNIT_BTC_ADDRESS2 = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'
UNIT_BTC_ADDRESS3 = '18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2'

ZERO_ETH_ADDRESS = string_to_evm_address('0x' + '0' * 40)
