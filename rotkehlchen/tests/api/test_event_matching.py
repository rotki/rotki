from http import HTTPStatus
from typing import TYPE_CHECKING

import requests

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_eth2 import HOUR_IN_MILLISECONDS
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_match_asset_movements(rotkehlchen_api_server: 'APIServer') -> None:
    """Test manually matching asset movements with corresponding onchain events."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(asset_movement := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
                location_label='Kraken 1',
            )), (matched_event := EvmEvent(
                identifier=2,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1510000000001),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.1'),
                location_label=(user_address := make_evm_address()),
            ))],
        )

    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'asset_movement': 1, 'matched_event': 2},
    ))
    assert matched_event.identifier is not None
    with rotki.data.db.conn.read_ctx() as cursor:
        assert rotki.data.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            identifier=matched_event.identifier,
        ) == asset_movement.identifier
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    # Check that the matched event was properly updated
    matched_event.event_type = HistoryEventType.DEPOSIT
    matched_event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
    matched_event.counterparty = 'kraken'
    matched_event.notes = f'Deposit 0.1 ETH to {user_address} from Kraken 1'
    matched_event.extra_data = {'matched_asset_movement': {
        'group_identifier': asset_movement.group_identifier,
        'exchange': 'kraken',
        'exchange_name': 'Kraken 1',
    }}
    assert events == [asset_movement, matched_event]


def test_match_asset_movements_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test error cases when matching asset movements."""
    assert_error_response(
        response=requests.put(
            url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={'asset_movement': 1, 'matched_event': 2},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='No asset movement event found in the DB for identifier 1',
    )

    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)

    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )],
        )

    assert_error_response(
        response=requests.put(
            url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={'asset_movement': 1, 'matched_event': 2},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='No event found in the DB for identifier 2',
    )


def test_get_unmatched_asset_movements(rotkehlchen_api_server: 'APIServer') -> None:
    """Test getting unmatched asset movements"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(matched_movement := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), (unmatched_movement := AssetMovement(
                identifier=2,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='2',
            ))],
        )
        assert matched_movement.identifier is not None
        rotki.data.db.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            identifier=5,  # matched event identifier can be anything here
            value=matched_movement.identifier,
        )

    result = assert_proper_response_with_result(
        response=requests.get(api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource')),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    assert result == [unmatched_movement.group_identifier]


def test_get_possible_matches(rotkehlchen_api_server: 'APIServer') -> None:
    """Test getting possible matches for an asset movement"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)

    matched_movement = AssetMovement(
        identifier=1,
        location=Location.KRAKEN,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1510000000000),
        asset=A_ETH,
        amount=FVal('0.1'),
    )
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[matched_movement, *[EvmEvent(
                identifier=idx,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(timestamp),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(amount),
            ) for idx, (timestamp, amount) in enumerate([
                (matched_movement.timestamp - 1, '0.1'),  # ID 2 - Before the movement. Not a close match.  # noqa: E501
                (matched_movement.timestamp + 1, '0.1'),  # ID 3 - After the movement, within the time range. Close Match.  # noqa: E501
                (matched_movement.timestamp + 2, '0.1'),  # ID 4 - After the movement, within the time range. Second close Match.  # noqa: E501
                (matched_movement.timestamp + 3, '0.5'),  # ID 5 - Wrong amount, not a match.
                (matched_movement.timestamp + HOUR_IN_MILLISECONDS * 2, '0.1'),  # ID 6 - Outside the time range, not matched or included in the other events list.  # noqa: E501
            ], start=2)]],
        )

    assert assert_proper_response_with_result(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={'asset_movement': matched_movement.group_identifier},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    ) == {  # Returns DB identifiers. These ids are set above with the enumeration index.
        'close_matches': [3, 4],
        'other_events': [2, 5],
    }
