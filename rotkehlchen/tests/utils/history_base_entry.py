
from collections.abc import Sequence
from itertools import groupby
from typing import Any

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.gitcoin.constants import GITCOIN_GRANTS_OLD1
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2, A_USDT
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
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
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

KEYS_IN_ENTRY_TYPE: dict[HistoryBaseEntryType, set[str]] = {
    HistoryBaseEntryType.HISTORY_EVENT: {'sequence_index', 'location', 'event_type', 'event_subtype', 'asset', 'user_notes', 'event_identifier'},  # noqa: E501
    HistoryBaseEntryType.ETH_BLOCK_EVENT: {'validator_index', 'is_exit_or_blocknumber', 'block_number', 'event_subtype', 'fee_recipient', 'location_label', 'is_mev_reward'},  # noqa: E501
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT: {'tx_ref', 'validator_index', 'sequence_index', 'event_identifier'},  # noqa: E501
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT: {'validator_index', 'is_exit_or_blocknumber', 'is_exit'},  # noqa: E501
    HistoryBaseEntryType.EVM_EVENT: {'tx_ref', 'sequence_index', 'location', 'event_type', 'event_subtype', 'asset', 'user_notes', 'counterparty', 'product', 'address', 'extra_data', 'event_identifier'},  # noqa: E501
    HistoryBaseEntryType.ASSET_MOVEMENT_EVENT: {'location', 'event_type', 'asset', 'event_identifier', 'extra_data'},  # noqa: E501
    HistoryBaseEntryType.SWAP_EVENT: {'location', 'asset', 'event_identifier'},
}


def pop_multiple_keys(serialized_event: dict[str, Any], entry_type: HistoryBaseEntryType):
    valid_keys = KEYS_IN_ENTRY_TYPE[entry_type].union({'entry_type', 'timestamp', 'amount', 'location_label', 'identifier'})  # noqa: E501
    event_keys = set(serialized_event.keys())
    for field in event_keys:
        if field not in valid_keys:
            serialized_event.pop(field)


def maybe_group_entries(entries: list[HistoryBaseEntry]) -> list[list[HistoryBaseEntry]]:
    """Group AssetMovements and SwapEvents by their event_identifier so they can be processed
    as a unit when adding/editing via the api.

    Only specific entry types are grouped by event_identifier because while the other types may
    share event_identifiers they are still processed individually when adding/editing via the api.
    """
    grouped_entries, need_group_by_id = [], []
    for entry in entries:
        if entry.entry_type in {
            HistoryBaseEntryType.ASSET_MOVEMENT_EVENT,
            HistoryBaseEntryType.SWAP_EVENT,
        }:
            need_group_by_id.append(entry)
        else:
            grouped_entries.append([entry])

    grouped_entries.extend([list(g) for k, g in groupby(need_group_by_id, lambda entry: entry.event_identifier)])  # noqa: E501
    return grouped_entries


def entries_to_input_dict(
        entries: list[HistoryBaseEntry],
        include_identifier: bool,
) -> dict[str, Any]:
    """Converts a group of HistoryBaseEntry events into a dictionary,
    optionally including the event identifier.
    """
    if len(entries) == 0:
        return {}

    serialized = (entry := entries[0]).serialize()
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
    elif entry.entry_type == HistoryBaseEntryType.ASSET_MOVEMENT_EVENT:
        if (extra_data := serialized.get('extra_data')) is not None:
            serialized['address'] = extra_data.get('address')
            serialized['transaction_id'] = extra_data.get('transaction_id')
            serialized['blockchain'] = extra_data.get('blockchain')
            serialized['unique_id'] = extra_data.get('reference')
            serialized.pop('extra_data')
        if len(entries) == 2:
            serialized['fee'] = (fee_entry := entries[1].serialize())['amount']
            serialized['fee_asset'] = fee_entry['asset']
    elif entry.entry_type == HistoryBaseEntryType.SWAP_EVENT:
        assert len(entries) > 1
        serialized['spend_amount'] = serialized.pop('amount')
        serialized['spend_asset'] = serialized.pop('asset')
        serialized['receive_amount'] = (receive_entry := entries[1].serialize())['amount']
        serialized['receive_asset'] = receive_entry['asset']
        if len(entries) == 3:
            serialized['fee_amount'] = (fee_entry := entries[2].serialize())['amount']
            serialized['fee_asset'] = fee_entry['asset']

    return serialized


def predefined_events_to_insert() -> list['HistoryBaseEntry']:
    """List of different objects used in tests that will be inserted in the database"""
    return [EvmEvent(
        tx_ref=deserialize_evm_tx_hash('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),
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
        tx_ref=deserialize_evm_tx_hash('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),
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
        tx_ref=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
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
        tx_ref=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
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
        tx_ref=deserialize_evm_tx_hash('0x4b5489ed325483db3a8c4831da1d5ac08fb9ab0fd8c570aa3657e0c267a7d023'),
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
        tx_ref=deserialize_evm_tx_hash('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),
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
    ), AssetMovement(
        timestamp=TimestampMS(1701654218000),
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=A_ETH,
        amount=FVal('0.0586453'),
        unique_id='MOVEMENT1',
        location_label='Coinbase 1',
        extra_data={
            'address': '0x6dcD6449dbCa615e40d696328209686eA95327b2',
            'transaction_id': '0x558bfa4d2a4ef598ddb92233459c00eda9e6c14cda75e6773b90208cb6938169',
            'reference': 'MOVEMENT1',
        },
    ), AssetMovement(
        timestamp=TimestampMS(1701654218000),
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=A_ETH,
        amount=FVal('0.000423'),
        unique_id='MOVEMENT1',
        location_label='Coinbase 1',
        is_fee=True,
    ), SwapEvent(
        timestamp=TimestampMS(1722153221000),
        location=Location.OKX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('5792.2972152799999995'),
        event_identifier='TRADE1',
        location_label='Okx 1',
    ), SwapEvent(
        timestamp=TimestampMS(1722153221000),
        location=Location.OKX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal('4.5'),
        event_identifier='TRADE1',
        location_label='Okx 1',
    ), SwapEvent(
        timestamp=TimestampMS(1722153221000),
        location=Location.OKX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00315'),
        event_identifier='TRADE1',
        location_label='Okx 1',
    )]


def add_entries(events_db: 'DBHistoryEvents') -> list['HistoryBaseEntry']:
    """Add history events to the database"""
    entries = predefined_events_to_insert()
    with events_db.db.conn.write_ctx() as write_cursor:
        for entry in entries:
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
        return dbevents.get_history_events_internal(
            cursor=write_cursor,
            filter_query=HistoryEventFilterQuery.make(event_identifiers=[events[0].event_identifier]),
        )  # query them from db to retrieve them with their identifier
