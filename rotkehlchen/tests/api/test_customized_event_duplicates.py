import random
from typing import TYPE_CHECKING

import requests

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.drivers.gevent import DBCursor


def duplicated_events_setup(
        events_db: DBHistoryEvents,
        write_cursor: 'DBCursor',
        auto_fix_groups: int,
        include_manual_review: bool,
        timestamp: TimestampMS,
) -> tuple[list[EvmSwapEvent], list[int], EvmSwapEvent | None]:
    """Insert duplicate candidates for auto-fix and optional manual review cases."""
    auto_fix_events: list[EvmSwapEvent] = []
    auto_fix_event_ids: list[int] = []
    for _ in range(auto_fix_groups):
        event = EvmSwapEvent(
            tx_ref=(tx_hash := make_evm_tx_hash()),
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=ONE,
        )
        customized_event = EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,  # changes only the sequence index
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=ONE,
        )
        event_id = events_db.add_history_event(write_cursor=write_cursor, event=event)
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=customized_event,
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )
        assert event_id is not None
        auto_fix_events.append(event)
        auto_fix_event_ids.append(event_id)

    manual_review_event: EvmSwapEvent | None = None
    if include_manual_review:
        manual_review_event = EvmSwapEvent(
            tx_ref=(manual_tx_hash := make_evm_tx_hash()),
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=ONE,
        )
        manual_review_customized = EvmSwapEvent(
            tx_ref=manual_tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('2'),  # this is the amount difference that makes it a manual review event
        )
        events_db.add_history_event(write_cursor=write_cursor, event=manual_review_event)
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=manual_review_customized,
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )

    return auto_fix_events, auto_fix_event_ids, manual_review_event


def test_customized_event_duplicates_endpoint(rotkehlchen_api_server: 'APIServer') -> None:
    """Ensure the duplicates endpoint separates auto-fix and manual review groups."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events_db = DBHistoryEvents(rotki.data.db)
    timestamp = TimestampMS(1710000000000)

    with rotki.data.db.conn.write_ctx() as write_cursor:
        auto_fix_events, _, manual_event = duplicated_events_setup(
            events_db=events_db,
            write_cursor=write_cursor,
            auto_fix_groups=1,
            include_manual_review=True,
            timestamp=timestamp,
        )

    async_query = random.choice([True, False])
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
        params={'async_query': async_query},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)

    assert set(result['auto_fix_group_ids']) == {auto_fix_events[0].group_identifier}
    assert manual_event is not None
    assert set(result['manual_review_group_ids']) == {manual_event.group_identifier}


def test_fix_customized_event_duplicates(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Check that auto fixing works properly with and without a group identifier filter"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events_db = DBHistoryEvents(rotki.data.db)
    timestamp = TimestampMS(1710000000000)

    with rotki.data.db.conn.write_ctx() as write_cursor:
        auto_fix_events, auto_fix_event_ids, _ = duplicated_events_setup(
            events_db=events_db,
            write_cursor=write_cursor,
            auto_fix_groups=2,
            include_manual_review=False,
            timestamp=timestamp,
        )
    async_query = random.choice([True, False])
    # First check with a group_identifier filter. Should only fix the provided group.
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
        json={
            'async_query': async_query,
            'group_identifiers': [auto_fix_events[0].group_identifier],
        },
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert set(result['removed_event_identifiers']) == {auto_fix_event_ids[0]}
    assert auto_fix_events[1].group_identifier in result['auto_fix_group_ids']
    assert auto_fix_events[0].group_identifier not in result['auto_fix_group_ids']
    # Then fix without a filter. Should fix the remaining group.
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
        json={'async_query': async_query},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result['removed_event_identifiers'] == [auto_fix_event_ids[1]]
    assert result['auto_fix_group_ids'] == []


def test_gas_events_duplicate_detection(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that gas events are only flagged as duplicates of other gas events.

    Gas fees are always present in EVM transactions and should not be considered
    duplicates of other event types like donate or send.

    1. gas + donate (customized) -> not flagged
    2. gas + gas (one customized) -> flagged as auto-fix
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(  # gas event for tx1
                tx_ref=(tx_hash_1 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1710000000000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001'),
                counterparty=CPT_GAS,
            ), (donate_event := EvmEvent(  # customized donate for tx1
                identifier=2,
                tx_ref=tx_hash_1,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.DONATE,
                asset=A_ETH,
                amount=ONE,
            )), (gas_event := EvmEvent(  # gas event for tx2
                tx_ref=(tx_hash_2 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001'),
                counterparty=CPT_GAS,
            )), EvmEvent(  # customized gas event for tx2
                identifier=4,
                tx_ref=tx_hash_2,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001'),
                counterparty=CPT_GAS,
            )],
        )
        write_cursor.executemany(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) VALUES(?, ?, ?)',
            [
                (2, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.CUSTOMIZED.serialize_for_db()),
                (4, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.CUSTOMIZED.serialize_for_db()),
            ],
        )

    result = assert_proper_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource')),
        rotkehlchen_api_server,
        async_query=False,
    )
    assert donate_event.group_identifier not in result['auto_fix_group_ids']  # gas + donate
    assert donate_event.group_identifier not in result['manual_review_group_ids']
    assert gas_event.group_identifier in result['auto_fix_group_ids']  # gas + gas
