import random
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.bitcoin.bch.constants import BCH_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.btc.constants import BTC_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_BCH,
    A_BTC,
    A_DAI,
    A_ETH,
    A_SOL,
    A_SUSHI,
    A_USD,
    A_USDC,
    A_USDT,
    A_WBNB,
    A_WBTC,
    A_WETH,
)
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import SUB_SWAPS_DETAILS, EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.tests.utils.accounting import toggle_ignore_an_asset
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import (
    generate_events_response,
    make_btc_tx_id,
    make_evm_address,
    make_evm_tx_hash,
    make_solana_address,
    make_solana_signature,
)
from rotkehlchen.tests.utils.history_base_entry import (
    KEYS_IN_ENTRY_TYPE,
    add_entries,
    entries_to_input_dict,
    maybe_group_entries,
    predefined_events_to_insert,
)
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    SolanaAddress,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash


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
            events = events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(event_identifiers=[entry.event_identifier]),
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
        json=entries_to_input_dict(entries=[entry], include_identifier=True),
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
        api_url_for(rotkehlchen_api_server, 'transactionsdecodingresource'),
        json={'chain': 'eth', 'tx_refs': [str(entry.tx_ref)], 'delete_custom': False},
    )
    assert_simple_ok_response(response)
    assert_event_got_edited(entry)


def add_test_evm_tx(database: 'DBHandler', tx_hash: 'EVMTxHash') -> None:
    """Add a blank tx so evm events can be added/edited without the tx_hash validation failing."""
    with database.conn.write_ctx() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp(0),
                block_number=0,
                from_address=ZERO_ADDRESS,
                to_address=ZERO_ADDRESS,
                value=0,
                gas=0,
                gas_price=0,
                gas_used=0,
                input_data=b'',
                nonce=0,
            )],
            relevant_address=None,
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])  # so we can run redecode after add/edit/delete
@pytest.mark.parametrize('ethereum_accounts', [['0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990']])
def test_add_edit_delete_entries(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = predefined_events_to_insert()
    grouped_entries = maybe_group_entries(entries=entries.copy())
    # Check that adding evm events fails when the tx_hash is not present.
    assert_error_response(
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entries_to_input_dict(grouped_entries[0], include_identifier=False),
        ),
        contained_in_msg='The provided transaction hash does not exist for ethereum.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Ignore one of the assets used in the events to be added. Used below to ensure
    # the `ignored` column gets set correctly on added events.
    assert A_DAI in [entry.asset for entry in entries]
    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.add_to_ignored_assets(write_cursor, A_DAI)

    for group in grouped_entries:
        json_data = entries_to_input_dict(group, include_identifier=False)
        if isinstance(event := group[0], EvmEvent):
            add_test_evm_tx(database=rotki.data.db, tx_hash=event.tx_ref)
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=json_data,
        )
        result = assert_proper_sync_response_with_result(response)
        assert 'identifier' in result
        for idx, entry in enumerate(group):
            entry.identifier = result['identifier'] + idx

    with rotki.data.db.conn.read_ctx() as cursor:
        for asset, ignored in cursor.execute('SELECT asset, ignored FROM history_events'):
            assert ignored == (1 if asset == A_DAI.identifier else 0)

        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
    for idx, event in enumerate(saved_events):
        assert event == entries[idx]

    entry = entries[2]
    assert isinstance(entry, EvmEvent)
    # test editing unknown fails
    unknown_id = 42
    json_data = entries_to_input_dict(entries=[entry], include_identifier=True)
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
    json_data = entries_to_input_dict(entries=[entry], include_identifier=True)
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
    json_data = entries_to_input_dict(entries=[entry], include_identifier=False)
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to add event to the DB. It already exists',
        status_code=HTTPStatus.CONFLICT,
    )
    # test that setting tx_hash to a hash not in the db and not present onchain fails.
    original_tx_hash = entry.tx_ref
    entry.tx_ref = deserialize_evm_tx_hash('0x51a331dc069f6f7ed6e02e259ff31131799e1fad632c72d15b9d138ec43e2a87')  # noqa: E501
    assert_error_response(
        response=requests.patch(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entries_to_input_dict(entries=[entry], include_identifier=True),
        ),
        contained_in_msg='The provided transaction hash does not exist for ethereum.',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # test that setting a real tx_hash that's only missing from the DB pulls the tx from onchain.
    entry.tx_ref = deserialize_evm_tx_hash('0x0deecc90c9d172b77ea52ebc13b929f219bf47f22a8a875bb6e2fedf3e3b74e1')  # noqa: E501
    original_location_label = entry.location_label
    entry.location_label = ethereum_accounts[0]  # associated address must be tracked when pulling new tx  # noqa: E501
    assert_simple_ok_response(requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entries_to_input_dict(entries=[entry], include_identifier=True),
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_transactions WHERE tx_hash=?',
            (entry.tx_ref,),
        ).fetchone()[0] == 1
    entry.tx_ref = original_tx_hash
    entry.location_label = original_location_label
    # test setting asset to something other than BTC fails for bitcoin history events
    assert isinstance((history_event_entry := entries[5]), HistoryEvent)
    json_data = entries_to_input_dict(entries=[history_event_entry], include_identifier=True)
    json_data['asset'] = A_ETH.identifier
    for location, error_msg in (
        (Location.BITCOIN, 'bitcoin events must use BTC as the asset'),
        (Location.BITCOIN_CASH, 'bitcoin_cash events must use BCH as the asset'),
    ):
        json_data['location'] = location.serialize()
        assert_error_response(
            response=requests.patch(
                api_url_for(rotkehlchen_api_server, 'historyeventresource'),
                json=json_data,
            ),
            contained_in_msg=error_msg,
            status_code=HTTPStatus.BAD_REQUEST,
        )
    # Test that editing works for the various event types
    assert_editing_works(entry, rotkehlchen_api_server, db, 4, also_redecode=True)  # evm event
    assert_editing_works(entries[5], rotkehlchen_api_server, db, 5)  # history event
    assert_editing_works(entries[6], rotkehlchen_api_server, db, 6, {'notes': 'Exit validator 1001 with 1500.1 ETH', 'event_identifier': 'EW_1001_19460'})  # eth withdrawal event  # noqa: E501
    assert_editing_works(entries[7], rotkehlchen_api_server, db, 7, {'notes': 'Deposit 1500.1 ETH to validator 1001'})  # eth deposit event  # noqa: E501
    assert_editing_works(entries[8], rotkehlchen_api_server, db, 8, {'notes': 'Validator 1001 produced block 5. Relayer reported 1500.1 ETH as the MEV reward going to 0x9531C059098e3d194fF87FebB587aB07B30B1306', 'event_identifier': 'BP1_5'})  # eth block event  # noqa: E501
    # Editing of AssetMovements and Swaps is tested in test_add_edit_asset_movements and test_add_edit_swap_events  # noqa: E501

    entries.sort(key=lambda x: x.timestamp)  # resort by timestamp
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
        assert len(saved_events) == 14
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
        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
        assert len(saved_events) == 14
        for idx, event in enumerate(saved_events):
            assert event == entries[idx]

        # test deleting works
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json={'identifiers': [2, 4]},
        )
        assert_simple_ok_response(response)
        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
        # entry is now last since the timestamp was modified
        assert saved_events == [entries[0], entries[2]] + entries[4:]

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
        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
        assert saved_events == [entries[0], entries[2]] + entries[4:]

        # now let's try to edit event_identifier for all possible events.
        for idx, group in enumerate(grouped_entries):
            if group[0].identifier in {2, 4}:
                continue  # we deleted those
            for entry in group:
                entry.event_identifier = f'new_eventid{idx}'
            json_data = entries_to_input_dict(group, include_identifier=True)
            json_data['event_identifier'] = f'new_eventid{idx}'
            response = requests.patch(
                api_url_for(rotkehlchen_api_server, 'historyeventresource'),
                json=json_data,
            )
            assert_simple_ok_response(response)
        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
        assert saved_events == [entries[0], entries[2]] + entries[4:]


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
        tx_ref=transaction.tx_hash,
        sequence_index=221,
        timestamp=ts_sec_to_ms(transaction.timestamp),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SUSHI,
        amount=FVal(100),
    )
    event2 = EvmEvent(
        tx_ref=transaction.tx_hash,
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
        dbevmtx.add_transactions(
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
    assert result['entries_found'] == 14
    assert result['entries_limit'] == 1000
    assert result['entries_total'] == 14
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
    assert result['entries_found'] == 8
    assert result['entries_limit'] == 1000
    assert result['entries_total'] == 8
    assert len(result['entries']) == 8

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
    assert result['entries_found'] == 8
    assert result['entries_limit'] == 1000
    assert result['entries_total'] == 8

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
    assert result['entries_found'] == 6
    assert result['entries_limit'] == 1000
    assert result['entries_total'] == 8

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
    assert result['entries_limit'] == 1000
    assert result['entries_total'] == 14

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
    assert result['entries_limit'] == 1000
    assert result['entries_total'] == 14

    # test pagination and exclude_ignored_assets and group by event ids works
    toggle_ignore_an_asset(rotkehlchen_api_server, A_ETH)
    for exclude_ignored_assets, found in ((True, 3), (False, 8)):
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
        assert result['entries_limit'] == 1000
        assert result['entries_total'] == 8

    # test pagination and exclude_ignored_assets without group by event ids works
    for exclude_ignored_assets, events_found, sub_events_found in ((True, 4, 4), (False, 14, 14)):
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
        assert result['entries_limit'] == 1000
        assert result['entries_total'] == 14

    # test pagination works fine with/without exclude_ignored_assets filter with/without premium
    db_history_events = DBHistoryEvents(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_history_events.db.user_write() as cursor:
        for limit, exclude_ignored, total, found in (
            (None, False, 8, 8),  # premium without ignoring assets, we get all the events  # noqa: E501
            (None, True, 3, 3),  # premium with ignoring assets (ETH), we get only 3 events  # noqa: E501
            (3, False, 8, 3),  # free limit (3) without ignoring assets, total events are 8 but we get only 3 (limited)  # noqa: E501
            (3, True, 3, 3),  # free limit (3) with ignoring assets, total events are 3, all shown (limit not exceeded)  # noqa: E501
            (1, False, 8, 1),  # free limit (1) without ignoring assets, total events are 8 but we get only 1 (limited)  # noqa: E501
            (1, True, 3, 1),  # free limit (1) with ignoring assets, total events are 2 but we get only 1 (limited)  # noqa: E501
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

    # check that address filter shows incoming transactions to the filtered address.
    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=deserialize_evm_tx_hash('0x9a76e51e6feb83690b4f0ecb257adbceb73b6f8b38d7d5c5d3f5e22fd10e3c71'),
                sequence_index=1,
                timestamp=TimestampMS(1639924590000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('2.5'),
                location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
                address=(address := string_to_evm_address('0xA7C8F1e13eDC5FBfB768f55ECF2Fee5d4C5BF964')),  # noqa: E501,
                notes=f'Send 2.5 ETH to {address}',  # type: ignore
            ), EvmEvent(
                tx_ref=deserialize_evm_tx_hash('0x9a76e51e6feb83690b4f0ecb257adbceb73b6f8b38d7d5c5d3f5e22fd10e3c72'),
                sequence_index=100,
                timestamp=TimestampMS(1639924590000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('2.5'),
                location_label=address,
                notes='Receive 2.5 ETH from 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
                address=string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
            )],
        )
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'location_labels': [address], 'group_by_event_ids': True, 'offset': 0, 'limit': 5, 'exclude_ignored_assets': False},  # noqa: E501
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries'][0]['entry']['user_notes'] == f'Send 2.5 ETH to {address}'
    assert result['entries'][1]['entry']['user_notes'] == 'Receive 2.5 ETH from 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'  # noqa: E501


def test_get_events_with_location_labels_filter(rotkehlchen_api_server: 'APIServer') -> None:
    """Regression test for a problem where filtering by location_labels used an evm filter query
    even if they were not evm addresses.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    with rotki.data.db.conn.write_ctx() as cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=cursor,
            history=[HistoryEvent(
                event_identifier=(event_identifier := 'btc_xxxxxx'),
                sequence_index=0,
                timestamp=TimestampMS(1722153222000),
                location=Location.BITCOIN,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_BTC,
                amount=FVal('0.001'),
                location_label='bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
            )],
        )

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'location_labels': ['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 1
    assert result['entries'][0]['entry']['event_identifier'] == event_identifier


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
            'user_notes': ['Main event note', 'Fee event note'],
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
        assert len(events := db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )) == 3  # including the fee event.
        assert events[1].event_subtype == HistoryEventSubType.REMOVE_ASSET
        assert events[1].notes == 'Main event note'
        assert events[2].event_subtype == HistoryEventSubType.FEE
        assert events[2].notes == 'Fee event note'
        # Check that references are set by the unique_id
        assert events[0].extra_data == {'reference': 'BITFINEX-543'}
        assert events[1].extra_data == {'reference': 'BITFINEX-344'}

    # Check event serialization.
    assert generate_events_response(data=[events[1]])[0]['entry'] == {
        'timestamp': 1669924575000,
        'event_type': 'withdrawal',
        'event_subtype': 'remove asset',
        'location': 'bitfinex',
        'location_label': None,
        'asset': 'ETH',
        'amount': '0.0569',
        'user_notes': 'Main event note',
        'identifier': 2,
        'entry_type': 'asset movement event',
        'event_identifier': '7e4d3805a88cbbcdc35badc4547044be803724146c7b9f0165cadd62c1616205',
        'sequence_index': 0,
        'extra_data': {'reference': 'BITFINEX-344'},
        'auto_notes': 'Withdraw 0.0569 ETH from Bitfinex',
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

        saved_events = (db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        ))
        assert len(saved_events) == 3
        fields_to_exclude = {
            'user_notes', 'extra_data', 'event_subtype', 'sequence_index',
            'location_label', 'unique_id', 'event_identifier',
            'fee', 'fee_asset', 'timestamp', 'auto_notes',
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

        # Check that the event_identifier is set correctly when editing an event with a fee
        assert cursor.execute(
            'SELECT event_identifier FROM history_events WHERE identifier=?',
            (entries[0]['identifier'],),
        ).fetchone()[0] == 'new_eventid1'

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
            'fees': [{'asset': 'ETH', 'amount': '0.000004'}],
            'unique_id': 'TRADE2',
            'user_notes': ['Example note', '', ''],
        }, {
            'entry_type': 'swap event',
            'timestamp': 1569954576000,
            'location': 'coinbase',
            'spend_amount': '0.02',
            'spend_asset': 'ETH',
            'receive_amount': '200',
            'receive_asset': 'USD',
            'fees': [
                {'asset': 'ETH', 'amount': '0.000044'},
                {'asset': 'USD', 'amount': '0.5'},
            ],
            'unique_id': 'TRADE3',
            'user_notes': ['Example note', 'Second note', 'Third note', 'Fourth note'],
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
        assert len(db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )) == 9  # spend/receive (2) from first swap, spend/receive/fee (3) from the second and spend/receive/fee/fee (4) from the third  # noqa: E501

    # Edit the event identifier of the first entry and add a fee
    entry = entries[0].copy()
    entry['fees'], entry['event_identifier'], entry['user_notes'] = [{'amount': '0.1', 'asset': 'USD'}], 'test_id', ['Note1', 'Note2', 'Note3']  # noqa: E501
    requests.patch(api_url_for(rotkehlchen_api_server, 'historyeventresource'), json=entry)
    with rotki.data.db.conn.read_ctx() as cursor:
        assert (events := db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
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
            extra_data={'reference': 'TRADE1'},
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
            identifier=10,  # highest id since it was added during edit
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
            notes='Example note',
            extra_data={'reference': 'TRADE2'},
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='TRADE2',
            ),
        ), SwapEvent(
            identifier=4,
            timestamp=TimestampMS(1569924576000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USD,
            amount=FVal('20'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='TRADE2',
            ),
        ), SwapEvent(
            identifier=5,
            timestamp=TimestampMS(1569924576000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000004'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='TRADE2',
            ),
        ), SwapEvent(
            identifier=6,
            timestamp=(trade3_timestamp := TimestampMS(1569954576000)),
            location=Location.COINBASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.02'),
            notes='Example note',
            extra_data={'reference': 'TRADE3'},
            event_identifier=(trade3_identifier := create_event_identifier_from_unique_id(
                location=Location.COINBASE,
                unique_id='TRADE3',
            )),
        ), SwapEvent(
            identifier=7,
            timestamp=trade3_timestamp,
            location=Location.COINBASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USD,
            amount=FVal('200'),
            notes='Second note',
            event_identifier=trade3_identifier,
        ), SwapEvent(
            identifier=8,
            timestamp=trade3_timestamp,
            location=Location.COINBASE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000044'),
            notes='Third note',
            event_identifier=trade3_identifier,
        ), SwapEvent(
            identifier=9,
            timestamp=trade3_timestamp,
            location=Location.COINBASE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal('0.5'),
            notes='Fourth note',
            sequence_index=3,
            event_identifier=trade3_identifier,
        )]

    # Check event serialization.
    assert generate_events_response(data=[events[3]])[0]['entry'] == {
        'timestamp': 1569924576000,
        'event_type': 'trade',
        'event_subtype': 'spend',
        'location': 'bitfinex',
        'location_label': None,
        'asset': 'ETH',
        'amount': '0.01',
        'user_notes': 'Example note',
        'identifier': 3,
        'entry_type': 'swap event',
        'event_identifier': '4074f41ac078988b05b7058775f111a3119888fc968f94ee9ed6a132918a3b83',
        'sequence_index': 0,
        'extra_data': {'reference': 'TRADE2'},
        'auto_notes': 'Swap 0.01 ETH in Bitfinex',
    }


def test_add_edit_evm_swap_events(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    entries = [{
        'entry_type': 'evm swap event',
        'timestamp': 1569924575000,
        'location': 'ethereum',
        'spend': [
            {'amount': '0.16', 'asset': A_ETH.identifier, 'user_notes': 'Example note', 'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545'},  # noqa: E501
            {'amount': '0.54', 'asset': A_WBNB.identifier, 'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545'},  # noqa: E501
        ],
        'receive': [
            {'amount': '0.003', 'asset': A_WBTC.identifier, 'location_label': '0x706A70067BE19BdadBea3600Db0626859Ff25D74'},  # noqa: E501
        ],
        'fee': [
            {'amount': '0.0002', 'asset': A_ETH.identifier},
            {'amount': '0.0012', 'asset': A_WETH.identifier},
        ],
        'sequence_index': 0,
        'tx_ref': (tx_hash_str := '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f'),  # noqa: E501
        'counterparty': 'some counterparty',
        'address': '0xA090e606E30bD747d4E6245a1517EbE430F0057e',
    }, {
        'entry_type': 'evm swap event',
        'timestamp': 1569924576000,
        'location': 'ethereum',
        'spend': [{'amount': '50', 'asset': A_USDT.identifier, 'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545'}],  # noqa: E501
        'receive': [{'amount': '0.026', 'asset': A_ETH.identifier, 'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545'}],  # noqa: E501
        'sequence_index': 123,
        'tx_ref': tx_hash_str,
        'counterparty': 'some counterparty',
        'address': '0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511',
    }]
    add_test_evm_tx(
        database=rotki.data.db,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(tx_hash_str)),
    )
    for entry in entries:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        )
        result = assert_proper_sync_response_with_result(response)
        assert 'identifier' in result

    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(events := db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )) == 7
        assert events[0].event_type == HistoryEventType.MULTI_TRADE
        assert events[0].event_subtype == HistoryEventSubType.SPEND
        assert events[1].event_subtype == HistoryEventSubType.SPEND
        assert events[2].event_subtype == HistoryEventSubType.RECEIVE
        assert events[3].event_subtype == HistoryEventSubType.FEE
        assert events[4].event_subtype == HistoryEventSubType.FEE
        assert events[5].event_type == HistoryEventType.TRADE
        assert events[5].event_subtype == HistoryEventSubType.SPEND
        assert events[6].event_subtype == HistoryEventSubType.RECEIVE

    # Setup entry's identifiers for editing
    entry = entries[0]
    entry['identifiers'], ids_per_subtype = [], defaultdict(list)
    for event in events:
        if event.timestamp == Timestamp(1569924575000):
            entry['identifiers'].append(event.identifier)  # type: ignore  # mypy doesn't understand what type the items in `entry` have
            ids_per_subtype[event.event_subtype.serialize()].append(event.identifier)

    for subtype in ('spend', 'receive', 'fee'):
        assert len(data_list := entry[subtype]) == len(id_list := ids_per_subtype[subtype])  # type: ignore
        for idx, identifier in enumerate(id_list):
            data_list[idx]['identifier'] = identifier  # type: ignore

    # Try adding a new fee event during edit with a colliding sequence index
    entry['sequence_index'] = 118
    entry['fee'].append({'amount': '1', 'asset': A_ETH.identifier})  # type: ignore
    assert_error_response(
        response=requests.patch(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        ),
        contained_in_msg=f'Tried to insert an event with event_identifier {events[0].event_identifier} and sequence_index 123, but an event already exists at that sequence_index.',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )
    entry['sequence_index'] = 0  # reset this so it doesn't affect later edits

    # Try setting tx_hash to a hash not in the db.
    entry['tx_ref'] = '0x51a331dc069f6f7ed6e02e259ff31131799e1fad632c72d15b9d138ec43e2a87'
    assert_error_response(
        response=requests.patch(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        ),
        contained_in_msg='The provided transaction hash does not exist for ethereum.',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    entry['tx_ref'] = tx_hash_str

    # Edit the event identifier of the first entry, add a receive event, and remove a fee event.
    entry['event_identifier'] = 'test_id'
    entry['receive'].append({'amount': '0.034', 'asset': A_WETH.identifier})  # type: ignore
    entry['fee'] = [entry['fee'][1]]  # type: ignore
    assert_proper_sync_response_with_result(requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        assert (events := db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )) == [EvmSwapEvent(
            identifier=1,
            event_identifier='test_id',
            sequence_index=0,
            timestamp=TimestampMS(1569924575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.16'),
            location_label=(location_label := '0x6e15887E2CEC81434C16D587709f64603b39b545'),
            notes='Example note',
            tx_ref=tx_hash,
            counterparty=(counterparty := 'some counterparty'),
            address=(addr1 := string_to_evm_address('0xA090e606E30bD747d4E6245a1517EbE430F0057e')),
        ), EvmSwapEvent(
            identifier=2,
            event_identifier='test_id',
            sequence_index=1,
            timestamp=TimestampMS(1569924575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WBNB,
            amount=FVal('0.54'),
            location_label=location_label,
            tx_ref=tx_hash,
            counterparty=counterparty,
            address=addr1,
        ), EvmSwapEvent(
            identifier=3,
            event_identifier='test_id',
            sequence_index=2,
            timestamp=TimestampMS(1569924575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WBTC,
            amount=FVal('0.003'),
            location_label='0x706A70067BE19BdadBea3600Db0626859Ff25D74',
            tx_ref=tx_hash,
            counterparty=counterparty,
            address=addr1,
        ), EvmSwapEvent(
            identifier=8,
            event_identifier='test_id',
            sequence_index=3,
            timestamp=TimestampMS(1569924575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WETH,
            amount=FVal('0.034'),
            tx_ref=tx_hash,
            counterparty=counterparty,
            address=addr1,
        ), EvmSwapEvent(
            identifier=5,
            event_identifier='test_id',
            sequence_index=4,
            timestamp=TimestampMS(1569924575000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_WETH,
            amount=FVal('0.0012'),
            tx_ref=tx_hash,
            counterparty=counterparty,
            address=addr1,
        ), EvmSwapEvent(
            identifier=6,
            sequence_index=123,
            timestamp=TimestampMS(1569924576000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('50'),
            location_label=location_label,
            tx_ref=tx_hash,
            counterparty=counterparty,
            address=(addr2 := string_to_evm_address('0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511')),
        ), EvmSwapEvent(
            identifier=7,
            sequence_index=124,
            timestamp=TimestampMS(1569924576000),
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.026'),
            location_label=location_label,
            tx_ref=tx_hash,
            counterparty=counterparty,
            address=addr2,
        )]

    # Check event serialization.
    assert generate_events_response(data=[events[5]])[0]['entry'] == {
        'timestamp': 1569924576000,
        'event_type': 'trade',
        'event_subtype': 'spend',
        'location': 'ethereum',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'asset': A_USDT.identifier,
        'amount': '50',
        'identifier': 6,
        'entry_type': 'evm swap event',
        'event_identifier': '10x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
        'sequence_index': 123,
        'extra_data': None,
        'tx_ref': '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
        'counterparty': 'some counterparty',
        'address': '0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511',
    }


def test_event_grouping(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that events are properly grouped into sub-lists
    when they are serialized for the api.

    The test events are as follows:
    - spend/fee gas event
    - group of EvmSwapEvents: spend, receive, fee
    - informational event
    - group of MULTI_TRADE events: spend, spend, receive, receive, fee
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # First check that querying history events grouped by id with no events works correctly.
    # Regression test for a problem that was introduced in the changes for event grouping.
    assert assert_proper_sync_response_with_result(response=requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'group_by_event_ids': True},
    ))['entries_found'] == 0

    db = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        db.add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=(tx_hash := deserialize_evm_tx_hash('0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f')),  # noqa: E501
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1569924575000)),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_WBTC,
                amount=FVal('0.003'),
                counterparty=CPT_GAS,
            ), EvmSwapEvent(
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal('0.16'),
                tx_ref=tx_hash,
            ), EvmSwapEvent(
                sequence_index=2,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_WBTC,
                amount=FVal('0.003'),
                tx_ref=tx_hash,
            ), EvmSwapEvent(
                sequence_index=3,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.0002'),
                tx_ref=tx_hash,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=4,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
            ), EvmSwapEvent(
                tx_ref=tx_hash,
                sequence_index=5,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.MULTI_TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal(0.123),
            ), EvmSwapEvent(
                tx_ref=tx_hash,
                sequence_index=6,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.MULTI_TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_WBTC,
                amount=FVal(0.0032),
            ), EvmSwapEvent(
                tx_ref=tx_hash,
                sequence_index=7,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.MULTI_TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_USDC,
                amount=FVal(120),
            ), EvmSwapEvent(
                tx_ref=tx_hash,
                sequence_index=8,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.MULTI_TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_USDT,
                amount=FVal(140),
            ), EvmSwapEvent(
                tx_ref=tx_hash,
                sequence_index=9,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.MULTI_TRADE,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal(0.0002),
            )],
        )
        result = assert_proper_sync_response_with_result(
            response=requests.post(api_url_for(rotkehlchen_api_server, 'historyeventresource')),
        )
        assert result['entries_found'] == 10
        assert len(entries := result['entries']) == 4  # gas event, evm swap group, informational event, multi trade group  # noqa: E501
        assert entries[0]['entry']['counterparty'] == 'gas'
        assert len(entries[1]) == 3  # spend, receive, fee
        assert entries[1][0]['entry']['event_type'] == 'trade'
        assert entries[1][0]['entry']['event_subtype'] == 'spend'
        assert entries[1][1]['entry']['event_subtype'] == 'receive'
        assert entries[1][2]['entry']['event_subtype'] == 'fee'
        assert entries[2]['entry']['event_type'] == 'informational'
        assert len(entries[3]) == 5  # spend, spend, receive, receive, fee
        assert entries[3][0]['entry']['event_type'] == 'multi trade'
        assert entries[3][0]['entry']['event_subtype'] == 'spend'
        assert entries[3][1]['entry']['event_subtype'] == 'spend'
        assert entries[3][2]['entry']['event_subtype'] == 'receive'
        assert entries[3][3]['entry']['event_subtype'] == 'receive'
        assert entries[3][4]['entry']['event_subtype'] == 'fee'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_edit_delete_solana_events(rotkehlchen_api_server: 'APIServer') -> None:
    """test that adding, editing, filtering, and deleting solana events works correctly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)

    # create test solana events with different attributes
    entries = [{
        'entry_type': 'solana event',
        'timestamp': 1569924575000,
        'amount': '1.5',
        'event_type': 'trade',
        'event_subtype': 'receive',
        'sequence_index': 1,
        'asset': 'SOL',
        'tx_ref': str(make_solana_signature()),
        'location_label': '7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W',
        'user_notes': 'solana event 1',
    }, {
        'entry_type': 'solana event',
        'timestamp': 1569924576000,
        'amount': '2.5',
        'event_type': 'trade',
        'event_subtype': 'spend',
        'sequence_index': 2,
        'asset': 'SOL',
        'tx_ref': str(make_solana_signature()),
        'location_label': '8Qp42peZrPfgfORFITw2VEiZsfiyjQOUyDxFTxDVk8Y',
        'user_notes': 'solana event 2',
    }, {
        'entry_type': 'solana event',
        'timestamp': 1569924577000,
        'amount': '3.5',
        'event_type': 'trade',
        'sequence_index': 3,
        'event_subtype': 'receive',
        'asset': 'SOL',
        'tx_ref': str(make_solana_signature()),
        'location_label': '9Rq53qfAsQghgPSGJUx3WFjAtgjzkPVZEyGUyEWm9Z',
        'user_notes': 'solana event 3',
    }]
    for entry in entries:  # add the events
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        )
        result = assert_proper_sync_response_with_result(response)
        assert 'identifier' in result
        entry['identifier'] = result['identifier']

    # verify events were added correctly
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
    assert len(saved_events) == 3
    for idx, event in enumerate(saved_events):
        assert str(event.amount) == entries[idx]['amount']
        assert event.notes == entries[idx]['user_notes']

    # test editing an event
    entry = entries[0].copy()
    entry['amount'] = '4.2'
    entry['user_notes'] = 'edited solana event'
    entry['counterparty'] = 'jupiter'
    entry['timestamp'] = 1569924580000

    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    )
    assert_simple_ok_response(response)

    # verify the edit worked
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'counterparties': 'jupiter'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 1
    edited_event = result['entries'][0]['entry']
    assert edited_event['identifier'] == entry['identifier']
    assert edited_event['amount'] == '4.2'
    assert edited_event['counterparty'] == 'jupiter'
    assert edited_event['user_notes'] == 'edited solana event'

    # test deleting an event
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'identifiers': [entries[1]['identifier']]},
    )
    assert_simple_ok_response(response)

    # verify the deletion worked
    with rotki.data.db.conn.read_ctx() as cursor:
        remaining_events = db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )
    assert len(remaining_events) == 2
    assert [event.identifier for event in remaining_events] == [
        entries[2]['identifier'],
        entries[0]['identifier'],
    ]

    # test filtering by event subtype
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'location': 'solana', 'event_subtypes': ['receive']},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 2


def test_tx_ref_and_address_filtering(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that filtering by tx_ref and address works correctly."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    btc_tx_id, bch_tx_id = make_btc_tx_id(), make_btc_tx_id()
    all_events: list[HistoryBaseEntry] = []
    all_events.extend(evm_events := [EvmEvent(
        tx_ref=make_evm_tx_hash(),
        sequence_index=0,
        timestamp=TimestampMS(0),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        address=make_evm_address(),
        notes=f'Evm event {idx}',
    ) for idx in range(2)])
    all_events.extend(solana_events := [SolanaEvent(
        tx_ref=make_solana_signature(),
        sequence_index=0,
        timestamp=TimestampMS(0),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=ZERO,
        address=make_solana_address(),
        notes=f'Solana event {idx}',
    ) for idx in range(2)])
    all_events.extend([HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=0,
        timestamp=TimestampMS(0),
        location=location,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=asset,
        amount=ZERO,
        notes=f'{asset.identifier} event',
    ) for event_identifier, location, asset in (
        (f'{BTC_EVENT_IDENTIFIER_PREFIX}{btc_tx_id}', Location.BITCOIN, A_BTC),
        (f'{BCH_EVENT_IDENTIFIER_PREFIX}{bch_tx_id}', Location.BITCOIN_CASH, A_BCH),
    )])

    with rotki.data.db.conn.write_ctx() as write_cursor:
        db.add_history_events(write_cursor=write_cursor, history=all_events)

    # Check all evm and solana events are retrieved by their addresses
    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'addresses': [str(x.address) for x in evm_events + solana_events]},
    ))
    assert {x['entry']['user_notes'] for x in result['entries']} == {
        'Evm event 0',
        'Evm event 1',
        'Solana event 0',
        'Solana event 1',
    }

    # Check all events are retrieved by their tx refs
    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'tx_refs': [str(x.tx_ref) for x in evm_events] + [str(x.tx_ref) for x in solana_events] + [btc_tx_id, bch_tx_id]},  # noqa: E501
    ))
    assert {x['entry']['user_notes'] for x in result['entries']} == {
        'Evm event 0',
        'Evm event 1',
        'Solana event 0',
        'Solana event 1',
        'BTC event',
        'BCH event',
    }

    # Check with a combination of addresses and tx_refs
    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={
            'addresses': [str(evm_events[0].address), str(evm_events[1].address), str(solana_events[1].address)],  # noqa: E501
            'tx_refs': [str(evm_events[0].tx_ref), str(solana_events[0].tx_ref), str(solana_events[1].tx_ref), btc_tx_id],  # noqa: E501
        },
    ))
    assert {x['entry']['user_notes'] for x in result['entries']} == {
        'Evm event 0',
        'Solana event 1',
    }


def test_add_edit_solana_swap_events(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that adding and editing Solana swap events works correctly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)

    entries = [{
        'entry_type': 'solana swap event',
        'timestamp': 1569924575000,
        'spend': [
            {'amount': '100', 'asset': (bonk_identifier := 'solana/token:DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'), 'user_notes': 'Swapped BONK', 'location_label': '7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'},  # noqa: E501
            {'amount': '0.5', 'asset': A_SOL.identifier, 'location_label': '8Qp42peZrPfgfORFITw2VEiZsfiyjQOUyDxFTxDVk8Y'},  # noqa: E501
        ],
        'receive': [
            {'amount': '2.5', 'asset': (jup_identifier := 'solana/token:JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN'), 'location_label': 'JUP4LHuHiLdG1qZfzN5JYKmZvSd5mE1kEWy1UQ8K8oP'},  # noqa: E501
        ],
        'fee': [
            {'amount': '0.001', 'asset': A_SOL.identifier},
        ],
        'sequence_index': 0,
        'tx_ref': str(signature := make_solana_signature()),
        'counterparty': 'jupiter',
        'address': '7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W',
    }, {
        'entry_type': 'solana swap event',
        'timestamp': 1569924576000,
        'spend': [{'amount': '50', 'asset': (ray_identifier := 'solana/token:4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R'), 'location_label': '8Qp42peZrPfgfORFITw2VEiZsfiyjQOUyDxFTxDVk8Y'}],  # noqa: E501
        'receive': [{'amount': '1.5', 'asset': A_SOL.identifier, 'location_label': '7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'}],  # noqa: E501
        'sequence_index': 123,
        'tx_ref': str(signature),
        'counterparty': 'orca',
        'address': 'JUP4LHuHiLdG1qZfzN5JYKmZvSd5mE1kEWy1UQ8K8oP',
    }]

    for entry in entries:  # add the events
        assert 'identifier' in assert_proper_sync_response_with_result(requests.put(
            api_url_for(rotkehlchen_api_server, 'historyeventresource'),
            json=entry,
        ))

    # Verify events were added correctly
    with rotki.data.db.conn.read_ctx() as cursor:
        assert (events := db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )) == [SolanaSwapEvent(  # 2 spend + 1 receive + 1 fee + 1 spend + 1 receive = 6 events  # noqa: E501
            tx_ref=signature,
            identifier=1,
            event_identifier=str(signature),
            sequence_index=0,
            timestamp=TimestampMS(1569924575000),
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset(bonk_identifier),
            amount=FVal('100'),
            location_label='7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W',
            notes='Swapped BONK',
            counterparty='jupiter',
            address=SolanaAddress('7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'),
        ), SolanaSwapEvent(
            tx_ref=signature,
            identifier=2,
            event_identifier=str(signature),
            sequence_index=1,
            timestamp=TimestampMS(1569924575000),
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SOL,
            amount=FVal('0.5'),
            location_label='8Qp42peZrPfgfORFITw2VEiZsfiyjQOUyDxFTxDVk8Y',
            notes=None,
            counterparty='jupiter',
            address=SolanaAddress('7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'),
        ), SolanaSwapEvent(
            tx_ref=signature,
            identifier=3,
            event_identifier=str(signature),
            sequence_index=2,
            timestamp=TimestampMS(1569924575000),
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset(jup_identifier),
            amount=FVal('2.5'),
            location_label='JUP4LHuHiLdG1qZfzN5JYKmZvSd5mE1kEWy1UQ8K8oP',
            notes=None,
            counterparty='jupiter',
            address=SolanaAddress('7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'),
        ), SolanaSwapEvent(
            tx_ref=signature,
            identifier=4,
            event_identifier=str(signature),
            sequence_index=3,
            timestamp=TimestampMS(1569924575000),
            event_type=HistoryEventType.MULTI_TRADE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_SOL,
            amount=FVal('0.001'),
            location_label=None,
            notes=None,
            counterparty='jupiter',
            address=SolanaAddress('7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'),
        ), SolanaSwapEvent(
            tx_ref=signature,
            identifier=5,
            event_identifier=str(signature),
            sequence_index=123,
            timestamp=TimestampMS(1569924576000),
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset(ray_identifier),
            amount=FVal('50'),
            location_label='8Qp42peZrPfgfORFITw2VEiZsfiyjQOUyDxFTxDVk8Y',
            notes=None,
            counterparty='orca',
            address=SolanaAddress('JUP4LHuHiLdG1qZfzN5JYKmZvSd5mE1kEWy1UQ8K8oP'),
        ), SolanaSwapEvent(
            tx_ref=signature,
            identifier=6,
            event_identifier=str(signature),
            sequence_index=124,
            timestamp=TimestampMS(1569924576000),
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_SOL,
            amount=FVal('1.5'),
            location_label='7Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W',
            notes=None,
            counterparty='orca',
            address=SolanaAddress('JUP4LHuHiLdG1qZfzN5JYKmZvSd5mE1kEWy1UQ8K8oP'),
        )]

    # Test editing Solana swap events
    # Setup entry's identifiers for editing
    entry = entries[0]
    entry['identifiers'], ids_per_subtype = [], defaultdict(list)
    timestamp_to_edit = TimestampMS(1569924575000)
    for event in events:
        if event.timestamp == timestamp_to_edit:
            entry['identifiers'].append(event.identifier)  # type: ignore
            ids_per_subtype[event.event_subtype.serialize()].append(event.identifier)

    for subtype in ('spend', 'receive', 'fee'):
        assert len(data_list := entry[subtype]) == len(id_list := ids_per_subtype[subtype])  # type: ignore
        for idx, identifier in enumerate(id_list):
            data_list[idx]['identifier'] = identifier  # type: ignore

    # Edit the event: change amounts and add a new receive event
    entry['spend'][0]['amount'] = '120'  # type: ignore  # Change BONK amount
    entry['spend'][1]['amount'] = '0.7'  # type: ignore  # Change SOL amount
    entry['receive'].append({'amount': '1.2', 'asset': A_SOL.identifier, 'location_label': '9Np41oeYqPefeNQEHSv1UDhYrehxin3NStESwCU85j7W'})  # type: ignore  # Add new receive event  # noqa: E501
    entry['fee'] = []  # Remove fee event

    # Apply the edit
    assert_proper_sync_response_with_result(requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    ))

    # Verify the edit was successful
    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(edited_events := db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(event_identifiers=[str(signature)]),
            group_by_event_ids=False,
        )) == 6  # Should have 2 spend + 2 receive + 1 spend + 1 receive = 6 events (fee was removed, new receive added)  # noqa: E501

    # Check that the first swap event was modified correctly
    assert len(spend_events := [e for e in edited_events if e.event_subtype == HistoryEventSubType.SPEND and e.timestamp == timestamp_to_edit]) == 2  # noqa: E501
    assert spend_events[0].amount == FVal('120')  # BONK amount changed
    assert spend_events[1].amount == FVal('0.7')   # SOL amount changed

    # Check that new receive event was added
    assert len(receive_events := [e for e in edited_events if e.event_subtype == HistoryEventSubType.RECEIVE and e.timestamp == timestamp_to_edit]) == 2  # noqa: E501
    assert any(e.amount == FVal('1.2') and e.asset == A_SOL for e in receive_events)

    # Check that fee event was removed
    assert len([e for e in edited_events if e.event_subtype == HistoryEventSubType.FEE and e.timestamp == timestamp_to_edit]) == 0  # noqa: E501
