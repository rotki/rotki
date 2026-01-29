from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import requests

from rotkehlchen.api.v1.types import TaskName
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_WETH
from rotkehlchen.db.cache import ASSET_MOVEMENT_NO_MATCH_CACHE_VALUE, DBCacheDynamic
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType, HistoryEvent
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.events import get_unmatched_asset_movements, match_asset_movements
from rotkehlchen.tests.unit.test_eth2 import HOUR_IN_MILLISECONDS
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
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
    assert asset_movement.identifier is not None
    with rotki.data.db.conn.read_ctx() as cursor:
        assert rotki.data.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            identifier=asset_movement.identifier,
        ) == matched_event.identifier
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


def test_mark_asset_movement_no_match(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that marking an asset movement as not matching works as expected."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(asset_movement := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1500000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            ))],
        )

    movements, _ = get_unmatched_asset_movements(database=rotki.data.db)
    assert len(movements) == 1
    assert asset_movement.identifier is not None
    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'asset_movement': asset_movement.identifier},
    ))

    with rotki.data.db.conn.read_ctx() as cursor:
        assert rotki.data.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            identifier=asset_movement.identifier,
        ) == ASSET_MOVEMENT_NO_MATCH_CACHE_VALUE

    movements, _ = get_unmatched_asset_movements(database=rotki.data.db)
    assert len(movements) == 0


def test_unlink_matched_asset_movements(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that unlinking matched asset movements works as expected."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(movement1 := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1500000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), (movement2 := AssetMovement(
                identifier=2,
                location=Location.BINANCE,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=movement1.timestamp,
                asset=movement1.asset,
                amount=movement1.amount,
                unique_id='2',
            )), (movement3 := AssetMovement(
                identifier=3,
                location=Location.BITSTAMP,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1600000000000),
                asset=A_ETH,
                amount=FVal('0.5'),
                unique_id='3',
            )), (movement3_match := HistoryEvent(
                identifier=4,
                group_identifier='xyz',
                sequence_index=0,
                timestamp=movement3.timestamp,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.EXTERNAL,
                asset=movement3.asset,
                amount=movement3.amount,
            )), (movement4 := AssetMovement(
                identifier=5,
                location=Location.COINBASE,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1700000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='4',
            ))],
        )

    match_asset_movements(database=rotki.data.db)

    for method, movement, expected_cache in [
        ('put', movement4, [  # First mark movement4 as having no match. All movements should have an entry in the cache.  # noqa: E501
            (f'matched_asset_movement_{movement3.identifier}', str(movement3_match.identifier)),
            (f'matched_asset_movement_{movement1.identifier}', str(movement2.identifier)),
            (f'matched_asset_movement_{movement2.identifier}', str(movement1.identifier)),
            (f'matched_asset_movement_{movement4.identifier}', str(ASSET_MOVEMENT_NO_MATCH_CACHE_VALUE)),  # noqa: E501
        ]), ('delete', movement1, [  # unlink movement1
            (f'matched_asset_movement_{movement3.identifier}', str(movement3_match.identifier)),
            (f'matched_asset_movement_{movement4.identifier}', str(ASSET_MOVEMENT_NO_MATCH_CACHE_VALUE)),  # noqa: E501
        ]), ('delete', movement3, [  # unlink movement3
            (f'matched_asset_movement_{movement4.identifier}', str(ASSET_MOVEMENT_NO_MATCH_CACHE_VALUE)),  # noqa: E501
        ]), ('delete', movement4, []),  # unlink movement4 (removes the "no match" value)
    ]:
        assert_simple_ok_response(requests.request(
            method=method,
            url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={'asset_movement': movement.identifier},
        ))
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT * FROM key_value_cache WHERE name LIKE ?',
                (f'{DBCacheDynamic.MATCHED_ASSET_MOVEMENT.name.lower()}%',),
            ).fetchall() == expected_cache


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
            )), (no_match_movement := AssetMovement(
                identifier=3,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='3',
            ))],
        )
        assert matched_movement.identifier is not None
        assert no_match_movement.identifier is not None
        rotki.data.db.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            identifier=matched_movement.identifier,
            value=5,  # matched event identifier can be anything here
        )
        rotki.data.db.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.MATCHED_ASSET_MOVEMENT,
            identifier=no_match_movement.identifier,
            value=ASSET_MOVEMENT_NO_MATCH_CACHE_VALUE,
        )

    result = assert_proper_response_with_result(
        response=requests.get(api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource')),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    assert result == [unmatched_movement.group_identifier]

    result = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            params={'only_ignored': True},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    assert result == [no_match_movement.group_identifier]


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
        location_label='Kraken 1',
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
            ) for idx, (timestamp, asset, amount) in enumerate([
                (matched_movement.timestamp - HOUR_IN_MILLISECONDS * 2, A_ETH, '0.1'),  # ID 2 - More than the tolerance before the movement, but within full range. Not a close match, but included in possible matches.  # noqa: E501
                (matched_movement.timestamp + 1, A_ETH, '0.1'),  # ID 3 - After the movement, within the time range. Close match.  # noqa: E501
                (matched_movement.timestamp + 2, A_ETH, '0.1'),  # ID 4 - After the movement, within the time range. Second close match.  # noqa: E501
                (matched_movement.timestamp + 3, A_ETH, '0.5'),  # ID 5 - Wrong amount, not a match.  # noqa: E501
                (matched_movement.timestamp + 4, A_WETH, '0.1'),  # ID 6 - Asset is different, but in the same collection. Third close match.  # noqa: E501
                (matched_movement.timestamp + HOUR_IN_MILLISECONDS * 3, A_ETH, '0.1'),  # ID 7 - Outside the time range, not matched or included in the other events list.  # noqa: E501
            ], start=2)], SwapEvent(  # Also add an unrelated swap event from the same exchange which should not be included in the possible matches  # noqa: E501
                identifier=8,
                timestamp=matched_movement.timestamp,
                location=matched_movement.location,
                event_subtype=HistoryEventSubType.SPEND,
                asset=matched_movement.asset,
                amount=matched_movement.amount,
                group_identifier='xyz1',
                location_label=matched_movement.location_label,
            ), HistoryEvent(
                identifier=9,
                group_identifier='xyz2',
                sequence_index=0,
                timestamp=TimestampMS(matched_movement.timestamp - 5),
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.EXTERNAL,
                asset=A_BTC,  # asset not in the same collection as the movement.
                amount=matched_movement.amount,
            ), EthWithdrawalEvent(  # ETH staking event that should be ignored.
                identifier=10,
                validator_index=12345,
                timestamp=matched_movement.timestamp,
                amount=FVal('0.1'),
                withdrawal_address=make_evm_address(),
                is_exit=False,
            ), EvmEvent(  # INFO/APPROVE event that should be ignored.
                identifier=11,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=matched_movement.timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.APPROVE,
                asset=matched_movement.asset,
                amount=matched_movement.amount,
            )],
        )

    for only_expected_assets, expected_other_events in [
        (True, [5, 2]),  # skips the BTC event (9)
        (False, [5, 9, 2]),  # BTC event included. ids are ordered by ts distance from the movement
    ]:
        assert assert_proper_response_with_result(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
                json={
                    'asset_movement': matched_movement.group_identifier,
                    'time_range': HOUR_IN_SECONDS * 2,
                    'only_expected_assets': only_expected_assets,
                    'tolerance': '0.002',
                },
            ),
            rotkehlchen_api_server=rotkehlchen_api_server,
        ) == {  # Returns DB identifiers. These ids are set above with the enumeration index.
            'close_matches': [3, 4, 6],
            'other_events': expected_other_events,
        }


def test_get_history_events_with_matched_asset_movements(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that getting history events with matched asset movements works as expected with
    asset movements grouped with their matched events. Checks both the case where a movement
    is matched with an evm event and also where two movements are matched with each other.
    The matched events (including any asset movement fee events) are grouped in a sublist to
    make them easier to identify in the frontend.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(movement1 := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1500000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), AssetMovement(
                identifier=2,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=movement1.timestamp,
                asset=A_ETH,
                amount=FVal('0.001'),
                is_fee=True,
                unique_id='1',
            ), (movement2 := AssetMovement(
                identifier=3,
                location=Location.BINANCE,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1500000000001),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='2',
            )), AssetMovement(
                identifier=4,
                location=Location.BINANCE,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=movement2.timestamp,
                asset=A_ETH,
                amount=FVal('0.001'),
                is_fee=True,
                unique_id='2',
            ), (movement3 := AssetMovement(
                identifier=5,
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1500000000002),
                asset=A_ETH,
                amount=FVal('0.5'),
                unique_id='3',
            )), EvmEvent(  # event in tx but unrelated to the movement. Could be gas fee, etc.
                identifier=6,
                tx_ref=(tx_ref := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=TimestampMS(1500000000002),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.01'),
                location_label=(user_address := make_evm_address()),
            ), (evm_event_1 := EvmEvent(
                identifier=7,
                tx_ref=tx_ref,
                sequence_index=1,
                timestamp=TimestampMS(1500000000002),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.5'),
                location_label=user_address,
            ))],
        )

    match_asset_movements(database=rotki.data.db)

    # Check aggregating by group with several filters that should all get the same groups.
    for filters in (
        {},
        {'entry_types': {'values': [HistoryBaseEntryType.ASSET_MOVEMENT_EVENT.serialize()]}},
        {'group_identifiers': [evm_event_1.group_identifier, movement2.group_identifier]},
    ):
        filters['aggregate_by_group_ids'] = True  # type: ignore[assignment]
        result = assert_proper_response_with_result(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'historyeventresource'),
                json=filters,
            ),
            rotkehlchen_api_server=rotkehlchen_api_server,
        )
        assert result['entries_found'] == result['entries_found_total'] == result['entries_total'] == 2  # noqa: E501
        assert len(result['entries']) == 2
        assert result['entries'][0]['grouped_events_num'] == 3  # includes both evm events and the matched asset movement  # noqa: E501
        assert result['entries'][0]['entry']['group_identifier'] == evm_event_1.group_identifier
        assert result['entries'][1]['grouped_events_num'] == 4  # the two matched movements and their fees  # noqa: E501
        assert result['entries'][1]['entry']['group_identifier'] == movement1.group_identifier

    # Then query the evm event group and the matched asset movement should be included
    result = assert_proper_response_with_result(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={
                'aggregate_by_group_ids': False,
                'group_identifiers': [evm_event_1.group_identifier],
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )['entries']
    # The events returned should all have the group_identifier of the evm event, but should also
    # have the actual_group_identifier set to preserve the real group_identifier of each event.
    # The presence of this field also notifies frontend that this group is a combination of
    # several groups and may need special handling.
    assert len(result) == 2
    # The first event in the tx isn't related to the asset movement
    assert (unrelated_event_entry := result[0])['entry']['event_type'] == 'spend'
    assert unrelated_event_entry['entry']['group_identifier'] == evm_event_1.group_identifier
    assert unrelated_event_entry['entry']['actual_group_identifier'] == evm_event_1.group_identifier  # noqa: E501
    # matched events are in a sublist so frontend can easily group them
    assert len(match1_sublist := result[1]) == 2
    assert match1_sublist[0]['entry']['event_type'] == 'deposit'
    assert match1_sublist[0]['entry']['group_identifier'] == evm_event_1.group_identifier
    assert match1_sublist[0]['entry']['actual_group_identifier'] == evm_event_1.group_identifier
    assert match1_sublist[1]['entry']['event_type'] == 'withdrawal'
    assert match1_sublist[1]['entry']['group_identifier'] == evm_event_1.group_identifier
    assert match1_sublist[1]['entry']['actual_group_identifier'] == movement3.group_identifier

    # Then check the events for the second matched event (movement2)
    result = assert_proper_response_with_result(
        response=requests.post(api_url_for(rotkehlchen_api_server, 'historyeventresource'), json={
            'aggregate_by_group_ids': False,
            'group_identifiers': [movement2.group_identifier],
        }),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )['entries']
    assert len(result) == 1
    assert len(match2_sublist := result[0]) == 4
    assert all(x['entry']['group_identifier'] == movement1.group_identifier for x in match2_sublist)  # noqa: E501
    assert match2_sublist[0]['entry']['event_type'] == 'deposit'
    assert match2_sublist[0]['entry']['actual_group_identifier'] == movement2.group_identifier
    assert match2_sublist[1]['entry']['event_subtype'] == 'fee'
    assert match2_sublist[1]['entry']['actual_group_identifier'] == movement2.group_identifier
    assert match2_sublist[2]['entry']['event_type'] == 'withdrawal'
    assert match2_sublist[2]['entry']['actual_group_identifier'] == movement1.group_identifier
    assert match2_sublist[3]['entry']['event_subtype'] == 'fee'
    assert match2_sublist[3]['entry']['actual_group_identifier'] == movement1.group_identifier

    # Check that querying both groups at once works correctly
    assert assert_proper_response_with_result(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={
                'aggregate_by_group_ids': False,
                'group_identifiers': [movement2.group_identifier, evm_event_1.group_identifier],
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )['entries'] == [unrelated_event_entry, match1_sublist, match2_sublist]


def test_trigger_matching_task(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that triggering the matching task works as expected."""
    for async_query in (True, False):
        with patch(
            target='rotkehlchen.tasks.events.get_unmatched_asset_movements',
            return_value=([], []),
        ) as match_mock:
            response = requests.post(
                api_url_for(rotkehlchen_api_server, 'triggertaskresource'),
                json={
                    'async_query': async_query,
                    'task': TaskName.ASSET_MOVEMENT_MATCHING.serialize(),
                },
            )

        if async_query:
            wait_for_async_task(
                server=rotkehlchen_api_server,
                task_id=assert_ok_async_response(response),
            )
        else:
            assert_simple_ok_response(response)

        assert match_mock.call_count == 1
