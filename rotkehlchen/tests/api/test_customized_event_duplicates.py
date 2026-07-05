import random
from typing import TYPE_CHECKING

import requests

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.merkl.constants import CPT_MERKL
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.drivers.sqlite import DBCursor


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
            amount=FVal('1.05'),  # amount within 10% makes it a manual review event
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


def test_fee_events_duplicate_detection(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that fee events are ignored in duplicate detection.

    1. fee + donate (customized) -> not flagged
    2. gas + gas (one customized) -> not flagged
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(  # fee event for tx1
                tx_ref=(tx_hash_1 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1710000000000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001'),
            ), (donate_event := EvmEvent(  # customized donate for tx1
                identifier=2,
                tx_ref=tx_hash_1,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.DONATE,
                asset=A_ETH,
                amount=FVal('0.001'),
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
    assert gas_event.group_identifier not in result['auto_fix_group_ids']


def test_subtype_notes_and_counterparty_change_auto_fix(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that we still auto fix a duplicate even if its event subtype, notes, and counterparty
    are edited in the customized event.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(  # fee event for tx1
                tx_ref=(tx_hash_1 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1710000000000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.001'),
            ), (customized_event := EvmEvent(  # customized donate for tx1
                identifier=2,
                tx_ref=tx_hash_1,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=A_ETH,
                amount=FVal('0.001'),
                notes='Claim reward',
                counterparty=CPT_MERKL,
            ))],
        )
        write_cursor.executemany(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) VALUES(?, ?, ?)',
            [(
                customized_event.identifier,
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
            )],
        )

    result = assert_proper_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource')),
        rotkehlchen_api_server,
        async_query=False,
    )
    assert customized_event.group_identifier in result['auto_fix_group_ids']
    assert len(result['manual_review_group_ids']) == 0


def test_balance_tracking_direction_duplicate_detection(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that events with different balance-tracking directions are not flagged as duplicates.

    Events that have NEUTRAL direction normally but different directions with
    for_balance_tracking=True should not be considered duplicates.

    1. protocol withdrawal (customized) + informational -> not flagged (IN vs NEUTRAL)
    2. account withdrawal (customized) + cex deposit + informational -> not flagged (OUT vs IN)
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[(protocol_withdrawal := EvmEvent(  # customized protocol withdrawal for tx1
                identifier=1,
                tx_ref=(tx_hash_1 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1710000000000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                asset=A_ETH,
                amount=ONE,
            )), EvmEvent(  # informational event for tx1
                tx_ref=tx_hash_1,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
            ), EvmEvent(  # customized account withdrawal for tx2
                identifier=3,
                tx_ref=(tx_hash_2 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=A_ETH,
                amount=ONE,
            ), (cex_deposit := EvmEvent(  # cex deposit for tx2
                tx_ref=tx_hash_2,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=ONE,
            )), EvmEvent(  # informational event for tx2
                tx_ref=tx_hash_2,
                sequence_index=2,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
            )],
        )
        write_cursor.executemany(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) VALUES(?, ?, ?)',
            [
                (1, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.CUSTOMIZED.serialize_for_db()),
                (3, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.CUSTOMIZED.serialize_for_db()),
            ],
        )

    result = assert_proper_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource')),
        rotkehlchen_api_server,
        async_query=False,
    )
    # tx1: protocol withdrawal + informational -> not flagged (IN vs NEUTRAL)
    assert protocol_withdrawal.group_identifier not in result['auto_fix_group_ids']
    assert protocol_withdrawal.group_identifier not in result['manual_review_group_ids']
    # tx2: account withdrawal + cex deposit + informational -> not flagged (OUT vs IN)
    assert cex_deposit.group_identifier not in result['auto_fix_group_ids']
    assert cex_deposit.group_identifier not in result['manual_review_group_ids']


def test_amount_threshold_duplicate_detection(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that we only flag as duplicates when the amounts are within a 10% threshold.

    1. customized (1 ETH) + non-customized (1.05 ETH) -> flagged (5% difference)
    2. customized (1 ETH) + non-customized (1.5 ETH) -> not flagged (50% difference)
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events_db = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(under_threshold_event := EvmEvent(
                identifier=1,
                tx_ref=(tx_hash1 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1710000000000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            )), (under_threshold_event_customized := EvmEvent(
                identifier=2,
                tx_ref=tx_hash1,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1.05'),  # 5% difference, under 10% threshold -> should be flagged
            )), (over_threshold_event := EvmEvent(
                identifier=3,
                tx_ref=(tx_hash2 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            )), (over_threshold_event_customized := EvmEvent(
                identifier=4,
                tx_ref=tx_hash2,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1.5'),  # 50% difference, over 10% threshold -> should not be flagged
            ))],
        )
        for event in [under_threshold_event_customized, over_threshold_event_customized]:
            events_db.set_event_mapping_state(
                write_cursor=write_cursor,
                event=event,
                mapping_state=HistoryMappingState.CUSTOMIZED,
            )

    result = assert_proper_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource')),
        rotkehlchen_api_server,
        async_query=False,
    )
    # tx1: 5% amount difference -> flagged for manual review
    assert under_threshold_event.group_identifier in result['manual_review_group_ids']
    # tx2: 50% amount difference -> not flagged
    assert over_threshold_event.group_identifier not in result['auto_fix_group_ids']
    assert over_threshold_event.group_identifier not in result['manual_review_group_ids']


def test_ignore_customized_event_duplicates(rotkehlchen_api_server: 'APIServer') -> None:
    """Test ignoring, unignoring, and ignoring a nonexistent group."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with rotki.data.db.conn.write_ctx() as write_cursor:
        auto_fix_events, _, manual_event = duplicated_events_setup(
            events_db=DBHistoryEvents(rotki.data.db),
            write_cursor=write_cursor,
            auto_fix_groups=1,
            include_manual_review=True,
            timestamp=TimestampMS(1710000000000),
        )

    auto_fix_group = auto_fix_events[0].group_identifier
    assert manual_event is not None
    manual_group = manual_event.group_identifier

    # verify both groups appear before ignoring
    result = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert auto_fix_group in result['auto_fix_group_ids']
    assert manual_group in result['manual_review_group_ids']
    assert result['ignored_group_ids'] == []

    # ignore both groups
    async_query = random.choice([True, False])
    result = assert_proper_response_with_result(
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
            json={
                'async_query': async_query,
                'group_identifiers': [auto_fix_group, manual_group],
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )
    assert set(result) == {auto_fix_group, manual_group}

    # ignoring already-ignored groups returns an error
    assert_error_response(
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
            json={
                'async_query': False,
                'group_identifiers': [auto_fix_group],
            },
        ),
        contained_in_msg='already ignored',
    )

    # unignoring a group that is not ignored returns an error
    assert_error_response(
        response=requests.delete(
            api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
            json={
                'async_query': False,
                'group_identifiers': ['nonexistent_group_id'],
            },
        ),
        contained_in_msg='not ignored',
    )

    # unignore the auto-fix group
    async_query = random.choice([True, False])
    result = assert_proper_response_with_result(
        response=requests.delete(
            api_url_for(rotkehlchen_api_server, 'customizedeventduplicatesresource'),
            json={
                'async_query': async_query,
                'group_identifiers': [auto_fix_group],
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )
    assert result == [manual_group]
