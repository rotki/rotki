from http import HTTPStatus
from typing import Any, Dict, List

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDT
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.types import Location, Timestamp, TimestampMS


def entry_to_input_dict(entry: HistoryBaseEntry, include_identifier: bool) -> Dict[str, Any]:
    serialized = entry.serialize()
    if include_identifier:
        assert entry.identifier is not None
        serialized['identifier'] = entry.identifier
    return serialized


def _add_entries(server) -> List[HistoryBaseEntry]:
    entries = [HistoryBaseEntry(
        event_identifier=HistoryBaseEntry.deserialize_event_identifier('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),  # noqa: E501
        sequence_index=162,
        timestamp=TimestampMS(1569924574000),
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.INFORMATIONAL,
        asset=A_DAI,
        balance=Balance(amount=FVal('1.542'), usd_value=FVal('1.675')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Approve 1 DAI of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',  # noqa: E501
        event_subtype=HistoryEventSubType.APPROVE,
        counterparty='0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
    ), HistoryBaseEntry(
        event_identifier=HistoryBaseEntry.deserialize_event_identifier('0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e'),  # noqa: E501
        sequence_index=163,
        timestamp=TimestampMS(1569924574000),
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.INFORMATIONAL,
        asset=A_USDT,
        balance=Balance(amount=FVal('1.542'), usd_value=FVal('1.675')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Approve 1 USDT of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',  # noqa: E501
        event_subtype=HistoryEventSubType.APPROVE,
        counterparty='0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
    ), HistoryBaseEntry(
        event_identifier=HistoryBaseEntry.deserialize_event_identifier('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),  # noqa: E501
        sequence_index=2,
        timestamp=TimestampMS(1619924574000),
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.0001'), usd_value=FVal('5.31')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Burned 0.0001 ETH for gas',
        event_subtype=HistoryEventSubType.FEE,
        counterparty=CPT_GAS,
    ), HistoryBaseEntry(
        event_identifier=HistoryBaseEntry.deserialize_event_identifier('0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc'),  # noqa: E501
        sequence_index=3,
        timestamp=TimestampMS(1619924574000),
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.DEPOSIT,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.0001'), usd_value=FVal('5.31')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Deposit something somewhere',
        event_subtype=HistoryEventSubType.NONE,
        counterparty='somewhere',
    ), HistoryBaseEntry(
        event_identifier=HistoryBaseEntry.deserialize_event_identifier('0x4b5489ed325483db3a8c4831da1d5ac08fb9ab0fd8c570aa3657e0c267a7d023'),  # noqa: E501
        sequence_index=55,
        timestamp=TimestampMS(1629924574000),
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=ONE, usd_value=FVal('1525.11')),
        location_label='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        notes='Receive 1 ETH from 0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a',
        event_subtype=HistoryEventSubType.NONE,
        counterparty='0x0EbD2E2130b73107d0C45fF2E16c93E7e2e10e3a',
    )]

    for entry in entries:
        json_data = entry_to_input_dict(entry, include_identifier=False)
        response = requests.put(
            api_url_for(server, 'historybaseentryresource'),
            json=json_data,
        )
        result = assert_proper_response_with_result(response)
        assert 'identifier' in result
        entry.identifier = result['identifier']

    return entries


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_edit_delete_entries(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    entries = _add_entries(rotkehlchen_api_server)
    db = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)
    for idx, event in enumerate(saved_events):
        assert event == entries[idx]

    entry = entries[2]
    # test editing unknown fails
    unknown_id = 42
    json_data = entry_to_input_dict(entry, include_identifier=True)
    json_data['identifier'] = unknown_id
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to edit event with id {unknown_id} but could not find it in the DB',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )
    # test editing by making sequence index same as an existing one fails
    entry.sequence_index = 3
    entry.timestamp = Timestamp(1649924575000)
    json_data = entry_to_input_dict(entry, include_identifier=True)
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to edit event to have event_identifier 0xf32e81dbaae8a763cad17bc96b77c7d9e8c59cc31ed4378b8109ce4b301adbbc and sequence_index 3 but it already exists',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )
    # test adding event with  sequence index same as an existing one fails
    entry.sequence_index = 3
    entry.timestamp = Timestamp(1649924575000)
    json_data = entry_to_input_dict(entry, include_identifier=True)
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
        json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to add event to the DB due to a DB error: UNIQUE constraint failed: history_events.event_identifier, history_events.sequence_index',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )
    # test editing works
    entry.sequence_index = 4
    entry.timestamp = Timestamp(1639924575000)
    entry.location = Location.UNISWAP
    entry.event_type = HistoryEventType.DEPOSIT
    entry.asset = A_USDT
    entry.balance = Balance(amount=FVal('1500.1'), usd_value=FVal('1499.45'))
    entry.location_label = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    entry.notes = 'Deposit stuff for staking somewhere'
    entry.event_subtype = HistoryEventSubType.NONE
    entry.counterparty = '0xAB8d71d59827dcc90fEDc5DDb97f87eFfB1B1A5B'
    json_data = entry_to_input_dict(entry, include_identifier=True)
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
        json=json_data,
    )
    assert_simple_ok_response(response)

    entries.sort(key=lambda x: x.timestamp)  # resort by timestamp
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_events = db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)
        assert len(saved_events) == 5
        for idx, event in enumerate(saved_events):
            assert event == entries[idx]

        # test deleting unknown fails
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
            json={'identifiers': [19, 1, 3]},
        )
        assert_error_response(
            response=response,
            contained_in_msg='Tried to remove history event with id 19 which does not exist',
            status_code=HTTPStatus.CONFLICT,
        )
        saved_events = db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)
        assert len(saved_events) == 5
        for idx, event in enumerate(saved_events):
            assert event == entries[idx]

        # test deleting works
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
            json={'identifiers': [2, 4]},
        )
        result = assert_proper_response_with_result(response)
        assert result is True
        saved_events = db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)
        # entry is now last since the timestamp was modified
        assert saved_events == [entries[0], entries[3], entry]

        # test that deleting last event of a transaction hash fails
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
            json={'identifiers': [1]},
        )
        assert_error_response(
            response=response,
            contained_in_msg='Tried to remove history event with id 1 which was the last event of a transaction',  # noqa: E501
            status_code=HTTPStatus.CONFLICT,
        )
        saved_events = db.get_history_events(cursor, HistoryEventFilterQuery.make(), True)
        assert saved_events == [entries[0], entries[3], entry]
