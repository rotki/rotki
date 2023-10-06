
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.accounting.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2, A_USDT
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.db.history_events import DBHistoryEvents


KEYS_IN_ENTRY_TYPE: dict[HistoryBaseEntryType, set[str]] = {
    HistoryBaseEntryType.HISTORY_EVENT: {'sequence_index', 'location', 'event_type', 'event_subtype', 'asset', 'notes', 'event_identifier'},  # noqa: E501
    HistoryBaseEntryType.ETH_BLOCK_EVENT: {'validator_index', 'block_number', 'event_subtype'},
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT: {'tx_hash', 'validator_index', 'sequence_index', 'event_identifier', 'extra_data'},  # noqa: E501
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT: {'validator_index', 'is_exit'},
    HistoryBaseEntryType.EVM_EVENT: {'tx_hash', 'sequence_index', 'location', 'event_type', 'event_subtype', 'asset', 'notes', 'counterparty', 'product', 'address', 'extra_data', 'event_identifier'},  # noqa: E501
}


def pop_multiple_keys(serialized_event: dict[str, Any], entry_type: HistoryBaseEntryType):
    valid_keys = KEYS_IN_ENTRY_TYPE[entry_type].union({'entry_type', 'timestamp', 'balance', 'location_label', 'identifier'})  # noqa: E501
    event_keys = set(serialized_event.keys())
    for field in event_keys:
        if field not in valid_keys:
            serialized_event.pop(field)


def entry_to_input_dict(
        entry: 'HistoryBaseEntry',
        include_identifier: bool,
) -> dict[str, Any]:
    """
    Converts a HistoryBaseEntry into a dictionary, optionally including the event identifier.
    """
    serialized = entry.serialize()
    if include_identifier:
        assert entry.identifier is not None
        serialized['identifier'] = entry.identifier
    else:
        serialized.pop('identifier')  # there is `identifier`: `None` which we have to remove
    pop_multiple_keys(serialized, entry.entry_type)
    if entry.entry_type == HistoryBaseEntryType.EVM_EVENT:
        serialized.pop('event_identifier')
    elif entry.entry_type == HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT:
        serialized['withdrawal_address'] = serialized.pop('location_label')
    elif entry.entry_type == HistoryBaseEntryType.ETH_BLOCK_EVENT:
        serialized['fee_recipient'] = serialized.pop('location_label')
        serialized['is_mev_reward'] = serialized.pop('event_subtype') == HistoryEventSubType.MEV_REWARD.serialize()  # noqa: E501
    elif entry.entry_type == HistoryBaseEntryType.ETH_DEPOSIT_EVENT:
        serialized['depositor'] = serialized.pop('location_label')
    return serialized


def add_entries(events_db: 'DBHistoryEvents') -> list['HistoryBaseEntry']:
    """Adds a pre-set list of history entries to the database"""
    entries: list[HistoryBaseEntry] = [EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),
        sequence_index=162,
        timestamp=TimestampMS(1569924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        asset=A_DAI,
        balance=Balance(amount=FVal('1.542'), usd_value=FVal('1.675')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Set DAI spending approval of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE to 1',  # noqa: E501
        event_subtype=HistoryEventSubType.APPROVE,
        address=string_to_evm_address('0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE'),
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),
        sequence_index=163,
        timestamp=TimestampMS(1569924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        asset=A_USDT,
        balance=Balance(amount=FVal('1.542'), usd_value=FVal('1.675')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Set USDT spending approval of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE to 1',  # noqa: E501
        event_subtype=HistoryEventSubType.APPROVE,
        address=string_to_evm_address('0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE'),
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
        sequence_index=2,
        timestamp=TimestampMS(1619924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.0001'), usd_value=FVal('5.31')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Burned 0.0001 ETH for gas',
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_GAS,
        extra_data={'testing_data': 42},
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
        sequence_index=3,
        timestamp=TimestampMS(1619924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.0001'), usd_value=FVal('5.31')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Deposit something somewhere',
        event_subtype=HistoryEventSubType.NONE,
        counterparty='somewhere',
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0x4b5489ed325483db3a8c4831da1d5ac08fb9ab0fd8c570aa3657e0c267a7d023'),
        sequence_index=55,
        timestamp=TimestampMS(1629924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=ONE, usd_value=FVal('1525.11')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Receive 1 ETH from 0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a',
        event_subtype=HistoryEventSubType.NONE,
        address=string_to_evm_address('0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a'),
    ), HistoryEvent(
        event_identifier='STARK-STARK-STARK',
        sequence_index=0,
        timestamp=TimestampMS(1673146287380),
        location=Location.KRAKEN,
        location_label='Kraken',
        asset=A_ETH2,
        balance=Balance(
            amount=FVal('0.0000400780'),
            usd_value=FVal('0.051645312360'),
        ),
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        notes='Staking reward from kraken',
    ), EthWithdrawalEvent(
        identifier=5,
        validator_index=295601,
        timestamp=TimestampMS(1681392599000),
        balance=Balance(amount=FVal('1.631508097')),
        withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
        is_exit=False,
    ), EthBlockEvent(
        identifier=12,
        validator_index=295601,
        timestamp=TimestampMS(1691693607000),
        balance=Balance(FVal('0.126419309459217215')),
        fee_recipient=string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990'),
        block_number=15824493,
        is_mev_reward=False,
    ), EthDepositEvent(
        identifier=1,
        tx_hash=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
        validator_index=295601,
        sequence_index=1,
        timestamp=TimestampMS(1691379127000),
        balance=Balance(FVal(32)),
        depositor=string_to_evm_address('0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a'),
    )]

    for entry in entries:
        with events_db.db.conn.write_ctx() as write_cursor:
            identifier = events_db.add_history_event(
                write_cursor=write_cursor,
                event=entry,
            )
            entry.identifier = identifier
    return entries
