import random
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_SUSHI, A_USD, A_USDT
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import SUB_SWAPS_DETAILS, EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.tests.utils.accounting import toggle_ignore_an_asset
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import generate_events_response
from rotkehlchen.tests.utils.history_base_entry import (
    KEYS_IN_ENTRY_TYPE,
    add_entries,
    entry_to_input_dict,
    predefined_events_to_insert,
)
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


def assert_editing_works(
        entry: 'HistoryBaseEntry',
        rotkehlchen_api_server: 'APIServer',
        events_db: 'DBHistoryEvents',
        sequence_index: int,
        autoedited: dict[str, Any] | None = None,
        also_redecode: bool = False,
) -> None:
    """A function to assert editing works per entry type. If autoedited is given
    then we check that some fields, given in autoedited, were automatically edited
    and their value derived from other fields"""
    def edit_entry(attr: str, value: Any) -> None:
        if attr in KEYS_IN_ENTRY_TYPE[entry.entry_type]:
            if attr == 'is_mev_reward' and value is True:  # special handling
                entry.sequence_index = 1
                entry.event_type = HistoryEventType.INFORMATIONAL
                entry.event_subtype = HistoryEventSubType.MEV_REWARD
                return

            assert hasattr(entry, attr), f'No {attr} in entry'
            setattr(entry, attr, value)

    def assert_event_got_edited(entry: 'HistoryBaseEntry') -> None:
        with events_db.db.conn.read_ctx() as cursor:
            events = events_db.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(event_identifiers=[entry.event_identifier]),
                has_premium=True,
                group_by_event_ids=False,
            )

        # now that actual edit happened, tweak autoedited fields for the equality check
        if autoedited:
            for key, value in autoedited.items():
                setattr(entry, key, value)

        for event in events:
            if event.identifier == entry.identifier:
                assert event == entry

    entry.timestamp = TimestampMS(entry.timestamp + 2)
    entry.amount = FVal('1500.1')
    edit_entry('event_type', HistoryEventType.DEPOSIT)
    edit_entry('event_subtype', HistoryEventSubType.DEPOSIT_ASSET)
    edit_entry('extra_data', {'some': 2, 'data': 4})
    edit_entry('asset', A_USDT)
    edit_entry('location_label', '0x9531C059098e3d194fF87FebB587aB07B30B1306')
    edit_entry('notes', f'Updated entry for test using type {entry.entry_type}')
    edit_entry('validator_index', 1001)
    edit_entry('is_exit_or_blocknumber', True if isinstance(entry, EthWithdrawalEvent) else 5)
    edit_entry('is_mev_reward', True)
    edit_entry('sequence_index', sequence_index)

    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry_to_input_dict(entry, include_identifier=True),
    )
    assert_simple_ok_response(response)
    assert entry.identifier is not None
    assert_event_got_edited(entry)

    if not also_redecode:
        return

    assert isinstance(entry, EvmEvent)  # should be an evm event for redeocding

    # also redecode without custom deletion and see the custom events
    # are still correctly shown and not deleted
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'evmtransactionsresource'),
        json={
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': entry.tx_hash.hex(),
                }],
            'delete_custom': False,
        },
    )
    assert_simple_ok_response(response)
    assert_event_got_edited(entry)


@pytest.mark.parametrize('have_decoders', [True])  # so we can run redecode after add/edit/delete
@pytest.mark.parametrize('ethereum_accounts', [['0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990']])
def test_add_edit_delete_entries(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = predefined_events_to_insert()
    for entry in entries:
        json_data = entry_to_input_dict(entry, include_identifier=False)
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=json_data,
        )
        result = assert_proper_sync_response_with_result(response)
        assert 'identifier' in result
        entry.identifier = result['identifier']

    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
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
    # test adding event with sequence index same as an existing one fails
    entry.sequence_index = 3
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
    assert_editing_works(entry, rotkehlchen_api_server, db, 4, also_redecode=True)  # evm event
    assert_editing_works(entries[5], rotkehlchen_api_server, db, 5)  # history event
    assert_editing_works(entries[6], rotkehlchen_api_server, db, 6, {'notes': 'Exit validator 1001 with 1500.1 ETH', 'event_identifier': 'EW_1001_19460'})  # eth withdrawal event  # noqa: E501
    assert_editing_works(entries[7], rotkehlchen_api_server, db, 7, {'notes': 'Deposit 1500.1 ETH to validator 1001'})  # eth deposit event  # noqa: E501
    assert_editing_works(entries[8], rotkehlchen_api_server, db, 8, {'notes': 'Validator 1001 produced block 5. Relayer reported 1500.1 ETH as the MEV reward going to 0x9531C059098e3d194fF87FebB587aB07B30B1306', 'event_identifier': 'BP1_5'})  # eth block event  # noqa: E501

    entries.sort(key=lambda x: x.timestamp)  # resort by timestamp
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert len(saved_events) == 9
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
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert len(saved_events) == 9
        for idx, event in enumerate(saved_events):
            assert event == entries[idx]

        # test deleting works
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'identifiers': [2, 4]},
        )
        assert_simple_ok_response(response)
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        # entry is now last since the timestamp was modified
        assert saved_events == [entries[0], entries[2], entries[4], entries[5], entries[6], entries[7], entries[8]]  # noqa: E501

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
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert saved_events == [entries[0], entries[2], entries[4], entries[5], entries[6], entries[7], entries[8]]  # noqa: E501

        # now let's try to edit event_identifier for all possible events.
        for idx, entry in enumerate(entries):
            if entry.identifier in {2, 4}:
                continue  # we deleted those
            entry.event_identifier = f'new_eventid{idx}'
            json_data = entry_to_input_dict(entry, include_identifier=True)
            json_data['event_identifier'] = f'new_eventid{idx}'
            response = requests.patch(
                api_url_for(rotkehlchen_api_server, 'historyeventresource'),
                json=json_data,
            )
            assert_simple_ok_response(response)
        saved_events = db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert saved_events == [entries[0], entries[2], entries[4], entries[5], entries[6], entries[7], entries[8]]  # noqa: E501


def test_event_with_details(rotkehlchen_api_server: 'APIServer') -> None:
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
        amount=FVal(100),
    )
    event2 = EvmEvent(
        tx_hash=transaction.tx_hash,
        sequence_index=222,
        timestamp=ts_sec_to_ms(transaction.timestamp),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal(98.2),
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert result == {SUB_SWAPS_DETAILS: event2.extra_data[SUB_SWAPS_DETAILS]}  # type: ignore[index]  # extra_data is not None here


@pytest.mark.parametrize('ethereum_accounts', [['0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990']])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_get_events(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    entries = add_entries(events_db=DBHistoryEvents(rotki.data.db))
    expected_entries = [x.serialize() for x in entries]

    # add one event to the list of ignored events to check that the field ignored_in_accounting
    # gets correctly populated
    with rotki.data.db.conn.write_ctx() as cursor:
        rotki.data.db.add_to_ignored_action_ids(
            write_cursor=cursor,
            action_type=ActionType.HISTORY_EVENT,
            identifiers=[f'{entries[0].event_identifier}'],
        )

    queried_identifiers = [1, 4]
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT event_identifier, sequence_index FROM history_events WHERE '
            'identifier IN (?, ?)',
            queried_identifiers,
        )
        expected_events = set(cursor)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'identifiers': queried_identifiers},
    )
    assert {
        (data['entry']['event_identifier'], data['entry']['sequence_index'])
        for data in response.json()['result']['entries']
    } == expected_events

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
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

    # check if the accounting rule check is respected
    assert 'missing_accounting_rule' not in result['entries'][1]

    # now try with grouping
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': True},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 6
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 6
    assert len(result['entries']) == 6

    # check also that in groups we add the missing_accounting_rule key
    assert 'missing_accounting_rule' not in result['entries'][1]

    # now try with grouping and pagination
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': True, 'offset': 1, 'limit': 1},
    )
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 8
    assert result['entries_found'] == 8
    assert result['entries_limit'] == 100
    assert result['entries_total'] == 9

    # test pagination and exclude_ignored_assets and group by event ids works
    toggle_ignore_an_asset(rotkehlchen_api_server, A_ETH)
    for exclude_ignored_assets, found in ((True, 2), (False, 6)):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'historyeventresource',
            ),
            json={'group_by_event_ids': True, 'offset': 0, 'limit': 5, 'exclude_ignored_assets': exclude_ignored_assets},  # noqa: E501
        )
        result = assert_proper_sync_response_with_result(response)
        assert len(result['entries']) == min(found, 5)
        assert result['entries_found'] == found
        assert result['entries_limit'] == 100
        assert result['entries_total'] == 6

    # test pagination and exclude_ignored_assets without group by event ids works
    for exclude_ignored_assets, events_found, sub_events_found in ((True, 3, 3), (False, 9, 9)):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'historyeventresource',
            ),
            json={'group_by_event_ids': False, 'offset': 0, 'limit': 5, 'exclude_ignored_assets': exclude_ignored_assets},  # noqa: E501
        )
        result = assert_proper_sync_response_with_result(response)
        assert len(result['entries']) == min(sub_events_found, 5)
        assert result['entries_found'] == events_found
        assert result['entries_limit'] == 100
        assert result['entries_total'] == 9

    # test pagination works fine with/without exclude_ignored_assets filter with/without premium
    db_history_events = DBHistoryEvents(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_history_events.db.user_write() as cursor:
        for limit, exclude_ignored, total, found in (
            (None, False, 6, 6),  # premium without ignoring assets, we get all the events
            (None, True, 2, 2),  # premium with ignoring assets (ETH), we get only 2 events
            (3, False, 6, 3),  # free limit (3) without ignoring assets, total events are 6 but we get only 3 (limited)  # noqa: E501
            (2, True, 2, 2),  # free limit (2) with ignoring assets, total events are 2, all shown (limit not exceeded)  # noqa: E501
            (1, False, 6, 1),  # free limit (1) without ignoring assets, total events are 6 but we get only 1 (limited)  # noqa: E501
            (1, True, 2, 1),  # free limit (1) with ignoring assets, total events are 2 but we get only 1 (limited)  # noqa: E501
        ):
            assert db_history_events.get_history_events_count(
                cursor=cursor,
                group_by_event_ids=True,
                query_filter=HistoryEventFilterQuery.make(exclude_ignored_assets=exclude_ignored),
                entries_limit=limit,
            ) == (total, found)

    # test query an event with an unknown asset
    def mock_check_asset_existence(identifier: str, query_packaged_db: bool = True) -> Exception:
        raise UnknownAsset(identifier)

    with patch(
        target='rotkehlchen.assets.asset.AssetResolver.check_existence',
        new=mock_check_asset_existence,
    ):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'historyeventresource',
            ),
        )
    assert_proper_sync_response_with_result(response)
    assert rotkehlchen_api_server.rest_api.rotkehlchen.msg_aggregator.consume_errors() == [
        'Could not deserialize one or more history event(s). '
        'Try redecoding the event(s) or check the logs for more details.',
    ]


@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
def test_query_new_events(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    """Test that querying new exchange events works correctly both sync and async"""
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
            'exchangeeventsqueryresource',
        ),
        json={
            'async_query': async_query,
            'location': Location.KRAKEN.serialize(),
            'name': 'mockkraken',
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


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_edit_asset_movements(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = [
        {
            'entry_type': 'asset movement event',
            'timestamp': 1569924575000,
            'amount': '0.44',
            'event_type': 'deposit',
            'location': 'bitfinex',
            'unique_id': 'BITFINEX-543',
            'asset': 'ETH',
        }, {
            'entry_type': 'asset movement event',
            'timestamp': 1669924575000,
            'amount': '0.0569',
            'event_type': 'withdrawal',
            'fee': '0.000004',
            'location': 'bitfinex',
            'unique_id': 'BITFINEX-344',
            'asset': 'ETH',
            'fee_asset': 'ETH',
            'notes': ['Main event note', 'Fee event note'],
        },
    ]
    for entry in entries:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        )
        result = assert_proper_sync_response_with_result(response)
        assert 'identifier' in result
        entry['identifier'] = result['identifier']

    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(events := db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )) == 3  # including the fee event.
        assert events[1].event_subtype == HistoryEventSubType.REMOVE_ASSET
        assert events[1].notes == 'Main event note'
        assert events[2].event_subtype == HistoryEventSubType.FEE
        assert events[2].notes == 'Fee event note'
        # Check that references are set by the unique_id
        assert events[0].extra_data == {'reference': 'BITFINEX-543'}
        assert events[1].extra_data == {'reference': 'BITFINEX-344'}

    # Check serialization and that the note is properly appended to the autogenerated description.
    assert generate_events_response(data=[events[1]])[0]['entry'] == {
        'timestamp': 1669924575000,
        'event_type': 'withdrawal',
        'event_subtype': 'remove asset',
        'location': 'bitfinex',
        'location_label': None,
        'asset': 'ETH',
        'amount': '0.0569',
        'notes': 'Withdraw 0.0569 ETH from Bitfinex. Main event note',
        'identifier': 2,
        'entry_type': 'asset movement event',
        'event_identifier': '7e4d3805a88cbbcdc35badc4547044be803724146c7b9f0165cadd62c1616205',
        'sequence_index': 0,
        'extra_data': {'reference': 'BITFINEX-344'},
    }

    # test editing unknown fails
    entry = entries[1].copy()
    entry['identifier'] = 42
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to edit event with id 42 but could not find it in the DB',
        status_code=HTTPStatus.CONFLICT,
    )
    with rotki.data.db.conn.read_ctx() as cursor:
        # now let's try to edit event_identifier for all possible events.
        for idx, entry in enumerate(entries, start=1):
            entry['identifier'] = idx
            entry['event_identifier'] = f'new_eventid{idx}'
            response = requests.patch(
                api_url_for(rotkehlchen_api_server, 'historyeventresource'),
                json=entry,
            )
            assert_simple_ok_response(response)

        saved_events = (db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        ))
        assert len(saved_events) == 3
        fields_to_exclude = {
            'notes', 'extra_data', 'event_subtype', 'sequence_index',
            'location_label', 'unique_id', 'event_identifier',
            'fee', 'fee_asset', 'timestamp',
        }
        for idx, event in enumerate(saved_events):
            serialized_event = event.serialize()
            if idx == 2:  # the fee event
                expected_event = {
                    'asset': 'ETH',
                    'amount': '0.000004',
                    'entry_type': 'asset movement event',
                    'event_type': 'withdrawal',
                    'identifier': 3,
                    'location': 'bitfinex',
                }
            else:
                expected_event = entries[idx].copy()

            for field in fields_to_exclude:
                serialized_event.pop(field, None)
                expected_event.pop(field, None)

            assert serialized_event == expected_event

    with db.db.conn.read_ctx() as cursor:
        # edit the first event to add a fee
        query_for_events = (
            'SELECT COUNT(*) FROM history_events WHERE event_identifier IN (SELECT event_identifier FROM history_events WHERE identifier=?)',  # noqa: E501
            (entries[0]['identifier'],),
        )
        assert cursor.execute(*query_for_events).fetchone()[0] == 1
        entry = entries[0].copy()
        entry['fee'], entry['fee_asset'] = '0.1', 'ETH'
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        )
        assert cursor.execute(*query_for_events).fetchone()[0] == 2

        # edit the same event to remove the fee
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entries[0],
        )
        assert cursor.execute(*query_for_events).fetchone()[0] == 1


def test_add_edit_swap_events(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = [
        {
            'entry_type': 'swap event',
            'timestamp': 1569924575000,
            'location': 'bitfinex',
            'spend_amount': '50',
            'spend_asset': 'USD',
            'receive_amount': '0.026',
            'receive_asset': 'ETH',
            'unique_id': 'TRADE1',
        }, {
            'entry_type': 'swap event',
            'timestamp': 1569924576000,
            'location': 'bitfinex',
            'spend_amount': '0.01',
            'spend_asset': 'ETH',
            'receive_amount': '20',
            'receive_asset': 'USD',
            'fee_amount': '0.000004',
            'fee_asset': 'ETH',
            'unique_id': 'TRADE2',
            'notes': ['Example note', '', ''],
        },
    ]
    for entry in entries:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        )
        result = assert_proper_sync_response_with_result(response)
        assert 'identifier' in result
        entry['identifier'] = result['identifier']

    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )) == 5  # spend/receive (2) from first swap, and spend/receive/fee (3) from the second

    # Edit the event identifier of the first entry and add a fee
    entry = entries[0].copy()
    entry['fee_amount'], entry['fee_asset'], entry['event_identifier'], entry['notes'] = '0.1', 'USD', 'test_id', ['Note1', 'Note2', 'Note3']  # noqa: E501
    requests.patch(api_url_for(rotkehlchen_api_server, 'historyeventresource'), json=entry)
    with rotki.data.db.conn.read_ctx() as cursor:
        assert (events := db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )) == [SwapEvent(
            identifier=1,
            timestamp=TimestampMS(1569924575000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USD,
            amount=FVal('50'),
            notes='Note1',
            event_identifier='test_id',
        ), SwapEvent(
            identifier=2,
            timestamp=TimestampMS(1569924575000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.026'),
            notes='Note2',
            event_identifier='test_id',
        ), SwapEvent(
            identifier=6,  # highest id since it was added during edit
            timestamp=TimestampMS(1569924575000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal('0.1'),
            notes='Note3',
            event_identifier='test_id',
        ), SwapEvent(
            identifier=3,
            timestamp=TimestampMS(1569924576000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.01'),
            unique_id='TRADE2',
            notes='Example note',
        ), SwapEvent(
            identifier=4,
            timestamp=TimestampMS(1569924576000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USD,
            amount=FVal('20'),
            unique_id='TRADE2',
        ), SwapEvent(
            identifier=5,
            timestamp=TimestampMS(1569924576000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000004'),
            unique_id='TRADE2',
        )]

    # Check serialization and that the note is properly appended to the autogenerated description.
    assert generate_events_response(data=[events[3]])[0]['entry'] == {
        'timestamp': 1569924576000,
        'event_type': 'trade',
        'event_subtype': 'spend',
        'location': 'bitfinex',
        'location_label': None,
        'asset': 'ETH',
        'amount': '0.01',
        'notes': 'Swap 0.01 ETH in Bitfinex. Example note',
        'identifier': 3,
        'entry_type': 'swap event',
        'event_identifier': '4074f41ac078988b05b7058775f111a3119888fc968f94ee9ed6a132918a3b83',
        'sequence_index': 0,
        'extra_data': None,
    }
