
from collections.abc import Sequence
from typing import Any

from rotkehlchen.chain.ethereum.modules.gitcoin.constants import GITCOIN_GRANTS_OLD1
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2, A_USDT
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

KEYS_IN_ENTRY_TYPE: dict[HistoryBaseEntryType, set[str]] = {
    HistoryBaseEntryType.HISTORY_EVENT: {'sequence_index', 'location', 'event_type', 'event_subtype', 'asset', 'notes', 'event_identifier'},  # noqa: E501
    HistoryBaseEntryType.ETH_BLOCK_EVENT: {'validator_index', 'is_exit_or_blocknumber', 'block_number', 'event_subtype', 'fee_recipient', 'location_label', 'is_mev_reward'},  # noqa: E501
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT: {'tx_hash', 'validator_index', 'sequence_index', 'event_identifier'},  # noqa: E501
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT: {'validator_index', 'is_exit_or_blocknumber', 'is_exit'},  # noqa: E501
    HistoryBaseEntryType.EVM_EVENT: {'tx_hash', 'sequence_index', 'location', 'event_type', 'event_subtype', 'asset', 'notes', 'counterparty', 'product', 'address', 'extra_data', 'event_identifier'},  # noqa: E501
}


def pop_multiple_keys(serialized_event: dict[str, Any], entry_type: HistoryBaseEntryType):
    valid_keys = KEYS_IN_ENTRY_TYPE[entry_type].union({'entry_type', 'timestamp', 'amount', 'location_label', 'identifier'})  # noqa: E501
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
        if include_identifier is False:  # when creating an eth deposit event we don't include the event_identifier  # noqa: E501
            serialized.pop('event_identifier')
        serialized['depositor'] = serialized.pop('location_label')
    return serialized


def predefined_events_to_insert() -> list['HistoryBaseEntry']:
    """List of different objects used in tests that will be inserted in the database"""
    return [EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),
        sequence_index=162,
        timestamp=TimestampMS(1569924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        asset=A_DAI,
        amount=FVal('1.542'),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes=f'Set DAI spending approval of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 by {GITCOIN_GRANTS_OLD1} to 1',  # noqa: E501
        event_subtype=HistoryEventSubType.APPROVE,
        address=GITCOIN_GRANTS_OLD1,
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),
        sequence_index=163,
        timestamp=TimestampMS(1569924575000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        asset=A_USDT,
        amount=FVal('1.542'),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes=f'Set USDT spending approval of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 by {GITCOIN_GRANTS_OLD1} to 1',  # noqa: E501
        event_subtype=HistoryEventSubType.APPROVE,
        address=GITCOIN_GRANTS_OLD1,
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
        sequence_index=2,
        timestamp=TimestampMS(1619924576000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        asset=A_ETH,
        amount=FVal('0.0001'),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Burn 0.0001 ETH for gas',
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_GAS,
        extra_data={'testing_data': 42},
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
        sequence_index=3,
        timestamp=TimestampMS(1619924579000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_ETH,
        amount=FVal('0.0001'),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Deposit something somewhere',
        counterparty='somewhere',
    ), EvmEvent(
        tx_hash=deserialize_evm_tx_hash('0x4b5489ed325483db3a8c4831da1d5ac08fb9ab0fd8c570aa3657e0c267a7d023'),
        sequence_index=55,
        timestamp=TimestampMS(1629924574000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        asset=A_ETH,
        amount=ONE,
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
        amount=FVal('0.0000400780'),
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        notes='Staking reward from kraken',
    ), EthWithdrawalEvent(
        validator_index=295601,
        timestamp=TimestampMS(1681392599000),
        amount=FVal('1.631508097'),
        withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
        is_exit=False,
    ), EthDepositEvent(
        tx_hash=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
        validator_index=295601,
        sequence_index=1,
        timestamp=TimestampMS(1691379127000),
        amount=FVal(32),
        depositor=string_to_evm_address('0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a'),
    ), EthBlockEvent(
        validator_index=295601,
        timestamp=TimestampMS(1691693607000),
        amount=FVal('0.126419309459217215'),
        fee_recipient=string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990'),
        fee_recipient_tracked=True,
        block_number=15824493,
        is_mev_reward=False,
    )]


def add_entries(events_db: 'DBHistoryEvents') -> list['HistoryBaseEntry']:
    """Add history events to the database"""
    entries = predefined_events_to_insert()
    for entry in entries:
        with events_db.db.conn.write_ctx() as write_cursor:
            identifier = events_db.add_history_event(
                write_cursor=write_cursor,
                event=entry,
            )
            entry.identifier = identifier
    return entries


def store_and_retrieve_events(
        events: Sequence[HistoryBaseEntry],
        db: DBHandler,
) -> Sequence[HistoryBaseEntry]:
    """Store events in database and retrieve them again fully populated with identifiers"""
    dbevents = DBHistoryEvents(db)
    with db.user_write() as write_cursor:
        for event in events:
            dbevents.add_history_event(
                write_cursor=write_cursor,
                event=event,
            )
        return dbevents.get_history_events(
            cursor=write_cursor,
            filter_query=HistoryEventFilterQuery.make(event_identifiers=[events[0].event_identifier]),
            has_premium=True,
        )  # query them from db to retrieve them with their identifier
