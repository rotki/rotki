"""Tests for history events notes search functionality"""
from typing import TYPE_CHECKING

import requests

from rotkehlchen.constants.assets import A_ETH, A_USD
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response_with_result,
)
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_history_events_search_by_notes(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test searching history events by notes substring"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Create test events with different notes
    events = [
        HistoryEvent(
            event_identifier='event1',
            sequence_index=0,
            timestamp=TimestampMS(1000),
            location=Location.BINANCE,
            asset=A_ETH,
            amount=FVal('1.5'),
            notes='Bought ETH on Binance exchange',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
        ), HistoryEvent(
            event_identifier='event2',
            sequence_index=0,
            timestamp=TimestampMS(2000),
            location=Location.KRAKEN,
            asset=A_USD,
            amount=FVal('100'),
            notes='Deposited USD to Kraken',
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        ), HistoryEvent(
            event_identifier='event3',
            sequence_index=0,
            timestamp=TimestampMS(3000),
            location=Location.COINBASE,
            asset=A_ETH,
            amount=FVal('0.5'),
            notes='Transferred ETH from Coinbase to cold wallet',
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
        ), HistoryEvent(
            event_identifier='event4',
            sequence_index=0,
            timestamp=TimestampMS(4000),
            location=Location.EXTERNAL,
            asset=A_ETH,
            amount=FVal('2.0'),
            notes='Custom event for ETH staking rewards',
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
    ]

    # Add events to database
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, events)

    # Test 1: Search for "ETH" in notes
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'notes_substring': 'ETH'},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server)

    # Should find events 1, 3, and 4
    assert result['entries_found'] == 3
    found_identifiers = {entry['entry']['event_identifier'] for entry in result['entries']}
    assert found_identifiers == {'event1', 'event3', 'event4'}

    # Test 2: Search for "exchange" in notes (case insensitive)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'notes_substring': 'exchange'},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server)

    # Should find event 1 only
    assert result['entries_found'] == 1
    assert result['entries'][0]['entry']['event_identifier'] == 'event1'

    # Test 3: Search for "Custom" in notes
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'notes_substring': 'Custom'},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server)

    # Should find event 4 only
    assert result['entries_found'] == 1
    assert result['entries'][0]['entry']['event_identifier'] == 'event4'

    # Test 4: Search for non-existent substring
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'notes_substring': 'nonexistent'},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server)

    # Should find no events
    assert result['entries_found'] == 0
    assert result['entries'] == []


def test_history_events_search_by_event_identifier(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test searching history events by event identifier"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Create test events
    events = [
        HistoryEvent(
            event_identifier='unique_event_123',
            sequence_index=0,
            timestamp=TimestampMS(1000),
            location=Location.EXTERNAL,
            asset=A_ETH,
            amount=FVal('1.0'),
            notes='Event with unique identifier',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
        ), HistoryEvent(
            event_identifier='another_event_456',
            sequence_index=0,
            timestamp=TimestampMS(2000),
            location=Location.EXTERNAL,
            asset=A_USD,
            amount=FVal('50'),
            notes='Another event',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
        ),
    ]

    # Add events to database
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, events)

    # Test: Search by specific event identifier
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'event_identifiers': ['unique_event_123']},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server)

    # Should find exactly one event
    assert result['entries_found'] == 1
    assert result['entries'][0]['entry']['event_identifier'] == 'unique_event_123'


def test_history_events_combined_filters(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test combining notes search with other filters"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Create test events
    events = [
        HistoryEvent(
            event_identifier='eth_event_1',
            sequence_index=0,
            timestamp=TimestampMS(1000),
            location=Location.BINANCE,
            asset=A_ETH,
            amount=FVal('1.0'),
            notes='Bought ETH on Binance',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
        ), HistoryEvent(
            event_identifier='eth_event_2',
            sequence_index=0,
            timestamp=TimestampMS(2000),
            location=Location.KRAKEN,
            asset=A_ETH,
            amount=FVal('2.0'),
            notes='Bought ETH on Kraken',
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
        ), HistoryEvent(
            event_identifier='usd_event',
            sequence_index=0,
            timestamp=TimestampMS(3000),
            location=Location.BINANCE,
            asset=A_USD,
            amount=FVal('100'),
            notes='Deposited USD on Binance',
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        ),
    ]

    # Add events to database
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, events)

    # Test: Search for "ETH" in notes AND filter by Binance location
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={
            'notes_substring': 'ETH',
            'location': 'binance',
        },
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server)

    # Should find only the ETH event from Binance
    assert result['entries_found'] == 1
    assert result['entries'][0]['entry']['event_identifier'] == 'eth_event_1'
    assert result['entries'][0]['entry']['location'] == 'binance'
