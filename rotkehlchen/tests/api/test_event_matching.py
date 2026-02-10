from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import requests

from rotkehlchen.api.v1.types import IncludeExcludeFilterData, TaskName
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_WETH
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HistoryEventLinkType,
    HistoryMappingState,
)
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
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


def _check_all_unlinked(
        dbevents: 'DBHistoryEvents',
        original_events: list['HistoryBaseEntry'],
) -> None:
    """Check that all asset movements are unlinked with the matched events restored
    to their original state.
    """
    with dbevents.db.conn.read_ctx() as cursor:
        # Check that all modified events have been restored to their original state and the
        # adjustment event has been removed.
        assert dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                order_by_rules=[('history_events_identifier', True)],
            ),
        ) == original_events
        # Check that no events remain in the backup table
        assert cursor.execute('SELECT COUNT(*) FROM history_events_backup').fetchone()[0] == 0
        # Check that the auto-matched mapping states have been removed.
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HistoryMappingState.AUTO_MATCHED.serialize_for_db()),
        ).fetchone()[0] == 0


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
                event_subtype=HistoryEventSubType.SPEND,
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
        json={'asset_movement': 1, 'matched_events': [2]},
    ))
    assert asset_movement.identifier is not None
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT right_event_id FROM history_event_links '
            'WHERE left_event_id=? AND link_type=?',
            (asset_movement.identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
        ).fetchone()[0] == matched_event.identifier
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    # Check that the matched event was properly updated
    matched_event.event_type = HistoryEventType.EXCHANGE_TRANSFER
    matched_event.event_subtype = HistoryEventSubType.RECEIVE
    matched_event.counterparty = 'kraken'
    matched_event.notes = f'Receive 0.1 ETH in {user_address} from Kraken 1'
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
            json={'asset_movement': 1, 'matched_events': [2]},
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
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )],
        )

    assert_error_response(
        response=requests.put(
            url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={'asset_movement': 1, 'matched_events': [2]},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Some of the specified matched event identifiers [2] are missing from the DB.',  # noqa: E501
    )


def test_multi_match_asset_movements(rotkehlchen_api_server: 'APIServer') -> None:
    """Test manually matching an asset movement with multiple onchain events."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=(original_events := [(before_event := HistoryEvent(
                identifier=1,
                group_identifier='xyz1',
                sequence_index=0,
                location=Location.EXTERNAL,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                timestamp=TimestampMS(1500000000000),
                asset=A_BTC,
                amount=FVal('0.01'),
            )), (asset_movement := AssetMovement(
                identifier=2,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.3'),
                unique_id='1',
                location_label='Kraken 1',
            )), EvmEvent(
                identifier=3,
                tx_ref=(tx_hash1 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=TimestampMS(1510000000001),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.0001'),
                counterparty=CPT_GAS,
                location_label=(user_address := make_evm_address()),
            ), (matched_event1 := EvmEvent(
                identifier=4,
                tx_ref=tx_hash1,
                sequence_index=1,
                timestamp=TimestampMS(1510000000001),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.1'),
                location_label=user_address,
            )), EvmEvent(
                identifier=5,
                tx_ref=(tx_hash2 := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=TimestampMS(1510000000002),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.0001'),
                counterparty=CPT_GAS,
                location_label=(user_address := make_evm_address()),
            ), (matched_event2 := EvmEvent(
                identifier=6,
                tx_ref=tx_hash2,
                sequence_index=1,
                timestamp=TimestampMS(1510000000002),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.2'),
                location_label=user_address,
            )), (after_event := HistoryEvent(
                identifier=7,
                group_identifier='xyz2',
                sequence_index=0,
                location=Location.EXTERNAL,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                timestamp=TimestampMS(1510000000003),
                asset=A_BTC,
                amount=FVal('0.01'),
            ))]),
        )

    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={
            'asset_movement': asset_movement.identifier,
            'matched_events': [matched_event1.identifier, matched_event2.identifier],
        },
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        # Check that the matched events were properly linked
        assert cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall() == [
            (asset_movement.identifier, matched_event1.identifier),
            (asset_movement.identifier, matched_event2.identifier),
        ]
        # Check that the matched events were properly updated
        assert len(events := dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                entry_types=IncludeExcludeFilterData([HistoryBaseEntryType.EVM_EVENT]),
                event_types=[HistoryEventType.EXCHANGE_TRANSFER],
                event_subtypes=[HistoryEventSubType.RECEIVE],
            ),
        )) == 2  # the two matched events
        assert all(
            x.extra_data is not None and 'matched_asset_movement' in x.extra_data
            for x in events
        )
        assert events[0].group_identifier == matched_event1.group_identifier
        assert events[1].group_identifier == matched_event2.group_identifier

    # Check aggregating by group
    result = assert_proper_response_with_result(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'aggregate_by_group_ids': True},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )['entries']
    assert len(result) == 3  # before event + multi match group + after event
    assert result[0]['entry']['group_identifier'] == after_event.group_identifier
    assert result[1]['entry']['group_identifier'] == asset_movement.group_identifier
    assert result[2]['entry']['group_identifier'] == before_event.group_identifier

    # Check filtering by group_identifiers without aggregating gets the proper results for any
    # group id in the joined group.
    for group_identifier in [
        asset_movement.group_identifier,
        matched_event1.group_identifier,
        matched_event2.group_identifier,
    ]:
        result = assert_proper_response_with_result(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'historyeventresource'),
                json={'aggregate_by_group_ids': False, 'group_identifiers': [group_identifier]},
            ),
            rotkehlchen_api_server=rotkehlchen_api_server,
        )['entries']
        assert len(result) == 3  # two gas events and the matched pair sublist
        assert all(x['entry']['group_identifier'] == asset_movement.group_identifier for x in result[:2])  # noqa: E501
        assert result[0]['entry']['actual_group_identifier'] == matched_event1.group_identifier
        assert result[0]['entry']['counterparty'] == CPT_GAS
        assert result[1]['entry']['actual_group_identifier'] == matched_event2.group_identifier
        assert result[1]['entry']['counterparty'] == CPT_GAS
        assert len(sublist := result[2]) == 3  # movement and two matched events
        assert all(x['entry']['group_identifier'] == asset_movement.group_identifier for x in sublist)  # noqa: E501
        assert sublist[0]['entry']['event_type'] == HistoryEventType.EXCHANGE_TRANSFER.serialize()
        assert sublist[0]['entry']['event_subtype'] == HistoryEventSubType.SPEND.serialize()
        assert sublist[0]['entry']['actual_group_identifier'] == asset_movement.group_identifier
        assert sublist[1]['entry']['event_type'] == HistoryEventType.EXCHANGE_TRANSFER.serialize()
        assert sublist[1]['entry']['event_subtype'] == HistoryEventSubType.RECEIVE.serialize()
        assert sublist[1]['entry']['actual_group_identifier'] == matched_event1.group_identifier
        assert sublist[2]['entry']['event_type'] == HistoryEventType.EXCHANGE_TRANSFER.serialize()
        assert sublist[2]['entry']['event_subtype'] == HistoryEventSubType.RECEIVE.serialize()
        assert sublist[2]['entry']['actual_group_identifier'] == matched_event2.group_identifier

    # Check that non-aggregating with no filter works properly including the surrounding events.
    result = assert_proper_response_with_result(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'aggregate_by_group_ids': False},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )['entries']
    assert len(result) == 5  # before event + two gas events + matched pair sublist + after event
    assert result[0]['entry']['group_identifier'] == after_event.group_identifier
    assert result[1]['entry']['actual_group_identifier'] == matched_event2.group_identifier
    assert result[2]['entry']['actual_group_identifier'] == matched_event1.group_identifier
    assert len(result[3]) == 3  # movement and two matched events
    assert result[4]['entry']['group_identifier'] == before_event.group_identifier

    # Check that unlinking a multi-match works properly
    assert_simple_ok_response(requests.delete(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'identifier': asset_movement.identifier},
    ))
    _check_all_unlinked(dbevents=dbevents, original_events=original_events)


def test_mark_asset_movement_no_match(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that marking an asset movement as not matching works as expected, and also that
    this ignored movement can also be converted to a matched pair properly.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[(asset_movement := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1500000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), HistoryEvent(
                identifier=(matched_event_id := 2),
                group_identifier='xyz',
                sequence_index=0,
                location=Location.EXTERNAL,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                timestamp=TimestampMS(1510000000001),
                asset=A_ETH,
                amount=FVal('0.01'),
            )],
        )

    movements, _ = get_unmatched_asset_movements(database=rotki.data.db)
    assert len(movements) == 1
    assert asset_movement.identifier is not None
    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'asset_movement': asset_movement.identifier},
    ))

    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_event_link_ignores '
            'WHERE event_id=? AND link_type=?',
            (asset_movement.identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
        ).fetchone()[0] == 1

    movements, _ = get_unmatched_asset_movements(database=rotki.data.db)
    assert len(movements) == 0

    # Also check that converting from an ignored movement to matched pair works properly
    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'asset_movement': asset_movement.identifier, 'matched_events': [matched_event_id]},
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_event_link_ignores '
            'WHERE event_id=? AND link_type=?',
            (asset_movement.identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall() == [(asset_movement.identifier, matched_event_id)]


def test_unlink_matched_asset_movements(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that unlinking matched asset movements works as expected."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=(original_events := [(movement1 := AssetMovement(
                identifier=1,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1500000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), (movement2 := AssetMovement(
                identifier=2,
                location=Location.BINANCE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=movement1.timestamp,
                asset=movement1.asset,
                amount=movement1.amount + FVal('0.0001'),  # different amount - will make an adjustment event.  # noqa: E501
                unique_id='2',
            )), (movement3 := AssetMovement(
                identifier=3,
                location=Location.BITSTAMP,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1600000000000),
                asset=A_ETH,
                amount=FVal('0.5'),
                unique_id='3',
            )), (movement3_match := EvmEvent(
                identifier=4,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=movement3.timestamp,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.ETHEREUM,
                asset=movement3.asset,
                amount=movement3.amount,
            )), (movement4 := AssetMovement(
                identifier=5,
                location=Location.COINBASE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='4',
            ))]),
        )

    match_asset_movements(database=rotki.data.db)

    with rotki.data.db.conn.read_ctx() as cursor:
        # Check that we have backups of the three matched events (movement3_match,
        # and both movement1 and movement2 since they are the matches for eachother).
        assert cursor.execute('SELECT group_identifier FROM history_events_backup').fetchall() == [
            (movement2.group_identifier,),
            (movement3_match.group_identifier,),
            (movement1.group_identifier,),
        ]
        # Check that we have an exchange adjustment event.
        assert len(dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                event_types=[HistoryEventType.EXCHANGE_ADJUSTMENT],
            ),
        )) == 1
        # Check that the auto-matched mapping states have been set.
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HistoryMappingState.AUTO_MATCHED.serialize_for_db()),
        ).fetchone()[0] == 4  # 3 matched events + 1 adjustment event

    for method, key, value, expected_links, expected_ignored in [
        (  # First mark movement4 as having no match.
            'put',
            'asset_movement',
            movement4.identifier,
            [
                (movement3.identifier, movement3_match.identifier),
                (movement1.identifier, movement2.identifier),
                (movement2.identifier, movement1.identifier),
            ],
            [movement4.identifier],
        ),
        ('delete', 'identifier', movement1.identifier, [  # unlink movement1
            (movement3.identifier, movement3_match.identifier),
        ], [movement4.identifier]),
        # unlink movement3 via its match's identifier
        ('delete', 'identifier', movement3_match.identifier, [], [movement4.identifier]),
        ('delete', 'identifier', movement4.identifier, [], []),  # unlink movement4 ignore
    ]:
        assert_simple_ok_response(requests.request(
            method=method,
            url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={key: value},
        ))
        with rotki.data.db.conn.read_ctx() as cursor:
            assert set(cursor.execute(
                'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
                (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
            ).fetchall()) == set(expected_links)
            assert set(cursor.execute(
                'SELECT event_id FROM history_event_link_ignores WHERE link_type=?',
                (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
            ).fetchall()) == {(identifier,) for identifier in expected_ignored}

    _check_all_unlinked(dbevents=dbevents, original_events=original_events)

    # Re-link after unlinking should not fail due to duplicated key_value_cache entries.
    assert_simple_ok_response(requests.put(
        url=api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={
            'asset_movement': movement3.identifier,
            'matched_events': [movement3_match.identifier],
        },
    ))


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
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), (unmatched_movement := AssetMovement(
                identifier=2,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='2',
            )), (no_match_movement := AssetMovement(
                identifier=3,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='3',
            )), HistoryEvent(
                identifier=(match_identifier := 4),
                group_identifier='dummy',
                sequence_index=0,
                timestamp=TimestampMS(1510000000000),
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.EXTERNAL,
                asset=A_ETH,
                amount=FVal('0.1'),
            )],
        )
        assert matched_movement.identifier is not None
        assert no_match_movement.identifier is not None
        write_cursor.execute(
            'INSERT INTO history_event_links(left_event_id, right_event_id, link_type) '
            'VALUES(?, ?, ?)',
            (
                matched_movement.identifier,
                match_identifier,
                HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
            ),
        )
        write_cursor.execute(
            'INSERT INTO history_event_link_ignores(event_id, link_type) VALUES(?, ?)',
            (no_match_movement.identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
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
        event_subtype=HistoryEventSubType.SPEND,
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

    with rotki.data.db.conn.write_ctx() as write_cursor:
        for idx, value in enumerate(already_matched_ids := [5, 3]):
            link_left_id = dbevents.add_history_event(
                write_cursor=write_cursor,
                event=AssetMovement(
                    group_identifier=f'dummy-{idx}',
                    timestamp=matched_movement.timestamp,
                    event_subtype=HistoryEventSubType.RECEIVE,
                    location=Location.EXTERNAL,
                    asset=A_ETH,
                    amount=FVal('0.1'),
                ),
            )
            assert link_left_id is not None
            write_cursor.execute(
                'INSERT INTO history_event_links(left_event_id, right_event_id, link_type) '
                'VALUES(?, ?, ?)',
                (
                    link_left_id,  # simulate matching with some other movement's id
                    value,
                    HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                ),
            )

    result = assert_proper_response_with_result(
        response=requests.post(
            api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
            json={
                'asset_movement': matched_movement.group_identifier,
                'time_range': HOUR_IN_SECONDS * 2,
                'tolerance': '0.002',
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    for already_matched_id in already_matched_ids:
        assert already_matched_id not in result['close_matches']
        assert already_matched_id not in result['other_events']


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
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1500000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='1',
            )), AssetMovement(
                identifier=2,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.FEE,
                timestamp=movement1.timestamp,
                asset=A_ETH,
                amount=FVal('0.001'),
                unique_id='1',
            ), (movement2 := AssetMovement(
                identifier=3,
                location=Location.BINANCE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1500000000001),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='2',
            )), AssetMovement(
                identifier=4,
                location=Location.BINANCE,
                event_subtype=HistoryEventSubType.FEE,
                timestamp=movement2.timestamp,
                asset=A_ETH,
                amount=FVal('0.001'),
                unique_id='2',
            ), (movement3 := AssetMovement(
                identifier=5,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
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
        assert result['entries'][0]['entry']['group_identifier'] == movement3.group_identifier
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
    assert unrelated_event_entry['entry']['group_identifier'] == movement3.group_identifier
    assert unrelated_event_entry['entry']['actual_group_identifier'] == evm_event_1.group_identifier  # noqa: E501
    # matched events are in a sublist so frontend can easily group them
    assert len(match1_sublist := result[1]) == 2
    assert match1_sublist[0]['entry']['event_type'] == 'exchange transfer'
    assert match1_sublist[0]['entry']['event_subtype'] == 'receive'
    assert match1_sublist[0]['entry']['group_identifier'] == movement3.group_identifier
    assert match1_sublist[0]['entry']['actual_group_identifier'] == evm_event_1.group_identifier
    assert match1_sublist[1]['entry']['event_type'] == 'exchange transfer'
    assert match1_sublist[1]['entry']['event_subtype'] == 'spend'
    assert match1_sublist[1]['entry']['group_identifier'] == movement3.group_identifier
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
    assert match2_sublist[0]['entry']['event_type'] == 'exchange transfer'
    assert match2_sublist[0]['entry']['event_subtype'] == 'spend'
    assert match2_sublist[0]['entry']['actual_group_identifier'] == movement1.group_identifier
    assert match2_sublist[1]['entry']['event_subtype'] == 'fee'
    assert match2_sublist[1]['entry']['actual_group_identifier'] == movement1.group_identifier
    assert match2_sublist[2]['entry']['event_type'] == 'exchange transfer'
    assert match2_sublist[2]['entry']['event_subtype'] == 'receive'
    assert match2_sublist[2]['entry']['actual_group_identifier'] == movement2.group_identifier
    assert match2_sublist[3]['entry']['event_subtype'] == 'fee'
    assert match2_sublist[3]['entry']['actual_group_identifier'] == movement2.group_identifier

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


def test_scheduler_endpoint(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the scheduler endpoint can enable and disable the task scheduler."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.task_manager is not None

    for enabled in (True, False):
        assert assert_proper_response_with_result(
            response=requests.put(
                api_url_for(rotkehlchen_api_server, 'schedulerresource'),
                json={'enabled': enabled},
            ),
            rotkehlchen_api_server=rotkehlchen_api_server,
        ) == {'enabled': enabled}
        assert rotki.task_manager.should_schedule is enabled
