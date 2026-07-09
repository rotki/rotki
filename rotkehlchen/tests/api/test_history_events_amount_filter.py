"""Tests for filtering history events by amount range"""
from http import HTTPStatus
from typing import TYPE_CHECKING

import requests

from rotkehlchen.constants.assets import A_ETH, A_USD
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_history_events_filter_by_amount(rotkehlchen_api_server: 'APIServer') -> None:
    """Test filtering history events by min_amount/max_amount with and without an asset"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events = [
        HistoryEvent(
            group_identifier='event1',
            sequence_index=0,
            timestamp=TimestampMS(1000),
            location=Location.BINANCE,
            asset=A_ETH,
            amount=FVal('1.5'),
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
        ), HistoryEvent(
            group_identifier='event2',
            sequence_index=0,
            timestamp=TimestampMS(2000),
            location=Location.KRAKEN,
            asset=A_USD,
            amount=FVal('100'),
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        ), HistoryEvent(
            group_identifier='event3',
            sequence_index=0,
            timestamp=TimestampMS(3000),
            location=Location.COINBASE,
            asset=A_ETH,
            amount=FVal('0.5'),
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
        ), HistoryEvent(
            group_identifier='event4',
            sequence_index=0,
            timestamp=TimestampMS(4000),
            location=Location.EXTERNAL,
            asset=A_ETH,
            amount=FVal('2'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
    ]
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, events)

    for json_filter, expected_groups in (
            ({'min_amount': '1'}, {'event1', 'event2', 'event4'}),
            ({'max_amount': '2'}, {'event1', 'event3', 'event4'}),  # boundary is inclusive
            ({'min_amount': '0.5', 'max_amount': '1.5'}, {'event1', 'event3'}),
            ({'min_amount': '1', 'max_amount': '2', 'asset': A_ETH.identifier}, {'event1', 'event4'}),  # noqa: E501
            ({'min_amount': '25', 'max_amount': '30'}, set()),
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=json_filter,
        )
        result = assert_proper_response_with_result(response, rotkehlchen_api_server)
        assert result['entries_found'] == len(expected_groups)
        assert {entry['entry']['group_identifier'] for entry in result['entries']} == expected_groups  # noqa: E501


def test_history_events_invalid_amount_range(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that a min_amount greater than max_amount is rejected"""
    assert_error_response(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'min_amount': '3', 'max_amount': '2'},
        ),
        contained_in_msg='min_amount must be smaller than or equal to max_amount',
        status_code=HTTPStatus.BAD_REQUEST,
    )
