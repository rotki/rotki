import json
import random
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import SUB_SWAPS_DETAILS, EvmEvent
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_SUSHI, A_USDT
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.history_base_entry import add_entries, entry_to_input_dict
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    HistoryEventQueryType,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_edit_delete_entries(rotkehlchen_api_server: 'APIServer'):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = add_entries(server=rotkehlchen_api_server, events_db=db)
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
    for idx, event in enumerate(saved_events):
        assert event == entries[idx]

    entry = entries[2]
    assert isinstance(entry, EvmEvent)
    # test editing unknown fails
    unknown_id = 42
    json_data = entry_to_input_dict(entry, include_identifier=True)
    json_data['identifier'] = unknown_id
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to edit event with id {unknown_id} but could not find it in the DB',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )
    # test editing by making sequence index same as an existing one fails
    entry.sequence_index = 3
    entry.timestamp = TimestampMS(1649924575000)
    json_data = entry_to_input_dict(entry, include_identifier=True)
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to edit event to have event_identifier 10xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc and sequence_index 3 but it already exists',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )
    # test adding event with  sequence index same as an existing one fails
    entry.sequence_index = 3
    entry.timestamp = TimestampMS(1649924575000)
    json_data = entry_to_input_dict(entry, include_identifier=False)
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to add event to the DB. It already exists',
        status_code=HTTPStatus.CONFLICT,
    )
    # test editing works
    entry.sequence_index = 4
    entry.timestamp = TimestampMS(1639924575000)
    entry.event_type = HistoryEventType.DEPOSIT
    entry.asset = A_USDT
    entry.balance = Balance(amount=FVal('1500.1'), usd_value=FVal('1499.45'))
    entry.location_label = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    entry.notes = 'Deposit stuff for staking somewhere'
    entry.event_subtype = HistoryEventSubType.NONE
    entry.address = string_to_evm_address('0xAB8d71d59827dcc90fEDc5DDb97f87eFfB1B1A5B')
    json_data = entry_to_input_dict(entry, include_identifier=True)
    assert entry.extra_data == {'testing_data': 42}

    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=json_data,
    )
    assert_simple_ok_response(response)
    assert entry.identifier is not None

    # check that the extra data information hasn't been overwritten
    with db.db.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT extra_data FROM evm_events_info WHERE identifier=?',
            (entry.identifier,),
        )
        db_extra_data = json.loads(cursor.fetchone()[0])
    assert entry.extra_data == db_extra_data

    entries.sort(key=lambda x: x.timestamp)  # resort by timestamp
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert len(saved_events) == 5
        for idx, event in enumerate(saved_events):
            assert event == entries[idx]

        # test deleting unknown fails
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'identifiers': [19, 1, 3]},
        )
        assert_error_response(
            response=response,
            contained_in_msg='Tried to remove history event with id 19 which does not exist',
            status_code=HTTPStatus.CONFLICT,
        )
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert len(saved_events) == 5
        for idx, event in enumerate(saved_events):
            assert event == entries[idx]

        # test deleting works
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'identifiers': [2, 4]},
        )
        result = assert_proper_response_with_result(response)
        assert result is True
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        # entry is now last since the timestamp was modified
        assert saved_events == [entries[0], entries[3], entry]

        # test that deleting last event of a transaction hash fails
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'identifiers': [1]},
        )
        assert_error_response(
            response=response,
            contained_in_msg='Tried to remove history event with id 1 which was the last event of a transaction',  # noqa: E501
            status_code=HTTPStatus.CONFLICT,
        )
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert saved_events == [entries[0], entries[3], entry]


def test_event_with_details(rotkehlchen_api_server: 'APIServer'):
    """Checks that if some events have details this is handled correctly."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db

    transaction = EvmTransaction(
        tx_hash=deserialize_evm_tx_hash('0x66e3d2686193e01a4fbf0f598872236402edfe2f4efad84c4f6cdc753b8c78e3'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1672580821),
        block_number=16383832,
        from_address=string_to_evm_address('0x0D268FE4F4BB33d092F098147646275241668A08'),
        to_address=string_to_evm_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'),
        value=0,
        gas=21000,
        gas_price=1000000000,
        gas_used=21000,
        input_data=b'',
        nonce=26,
    )
    event1 = EvmEvent(
        tx_hash=transaction.tx_hash,
        sequence_index=221,
        timestamp=ts_sec_to_ms(transaction.timestamp),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SUSHI,
        balance=Balance(amount=FVal(100)),
    )
    event2 = EvmEvent(
        tx_hash=transaction.tx_hash,
        sequence_index=222,
        timestamp=ts_sec_to_ms(transaction.timestamp),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        balance=Balance(amount=FVal(98.2)),
        extra_data={
            SUB_SWAPS_DETAILS: [
                {'amount_in': '100.0', 'amount_out': '0.084', 'from_asset': A_SUSHI.identifier, 'to_asset': A_ETH.identifier},  # noqa: E501
                {'amount_in': '0.084', 'amount_out': '98.2', 'from_asset': A_ETH.identifier, 'to_asset': A_USDT.identifier},  # noqa: E501
            ],
            'some-internal-data': 'some data',  # this data shouldn't be returned to the frontend
        },
    )

    dbevmtx = DBEvmTx(db)
    with db.user_write() as write_cursor:
        dbevmtx.add_evm_transactions(
            write_cursor=write_cursor,
            evm_transactions=[transaction],
            relevant_address=None,
        )
    dbevents = DBHistoryEvents(db)
    with db.user_write() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[event1, event2],
        )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    events = result['entries']
    assert events[1]['has_details'] is True

    # Check that if an event is not in the db, an error is returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eventdetailsresource',
        ), json={'identifier': 100},  # doesn't exist
    )
    assert_error_response(
        response=response,
        contained_in_msg='No event found',
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Check that if an event is in the db, but has no details, an error is returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eventdetailsresource',
        ), json={'identifier': events[0]['entry']['identifier']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='No details found',
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Check that if an event is in the db and has details, the details are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eventdetailsresource',
        ), json={'identifier': events[1]['entry']['identifier']},
    )
    result = assert_proper_response_with_result(response)
    assert result == {SUB_SWAPS_DETAILS: event2.extra_data[SUB_SWAPS_DETAILS]}  # type: ignore[index]  # extra_data is not None here


def test_get_events(rotkehlchen_api_server: 'APIServer'):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = add_entries(server=rotkehlchen_api_server, events_db=db, add_directly=True)
    expected_entries = [x.serialize() for x in entries]

    # add one event to the list of ignored events to check that the field ignored_in_accounting
    # gets correctly populated
    with rotki.data.db.conn.write_ctx() as cursor:
        rotki.data.db.add_to_ignored_action_ids(
            write_cursor=cursor,
            action_type=ActionType.HISTORY_EVENT,
            identifiers=[f'{entries[0].event_identifier}'],
        )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 9
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 9
    for event in result['entries']:
        assert event['entry'] in expected_entries

        # check that the only ignored event is the one that we have set
        if event['entry']['event_identifier'] == entries[0].event_identifier:
            assert event['ignored_in_accounting'] is True
        else:
            assert 'ignored_in_accounting' not in event

    # now try with grouping
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': True},
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 6
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 6
    assert len(result['entries']) == 6

    # now try with grouping and pagination
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': True, 'offset': 1, 'limit': 1},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries_found'] == 6
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 6

    # now with grouping, pagination and a filter
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': True, 'offset': 0, 'limit': 1, 'asset': 'ETH'},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries_found'] == 4
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 6

    # filter by location using kraken and ethereum
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'location': Location.KRAKEN.serialize()},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries_found'] == 1
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 9

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'location': Location.ETHEREUM.serialize()},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 8
    assert result['entries_found'] == 8
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 9


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
def test_query_new_events(rotkehlchen_api_server_with_exchanges: 'APIServer'):
    """Test that the endpoint for querying new events works correctly both sync and async"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    query_filter = HistoryEventFilterQuery.make(location=Location.KRAKEN)
    async_query = random.choice([True, False])

    with rotki.data.db.conn.read_ctx() as cursor:
        kraken_events_count, _ = db.get_history_events_count(
            cursor=cursor,
            query_filter=query_filter,
        )
        assert kraken_events_count == 0

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'eventsonlinequeryresource',
        ),
        json={
            'async_query': async_query,
            'query_type': HistoryEventQueryType.EXCHANGES.serialize(),
        },
    )

    if async_query is True:
        assert_ok_async_response(response)
    else:
        assert_proper_response(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        kraken_events_count, _ = db.get_history_events_count(
            cursor=cursor,
            query_filter=query_filter,
        )
        assert kraken_events_count != 0
