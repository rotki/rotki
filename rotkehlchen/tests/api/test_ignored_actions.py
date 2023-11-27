from http import HTTPStatus

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_simple_ok_response,
)
from rotkehlchen.types import Location, TimestampMS


def _populate_ignored_actions(rotkehlchen_api_server) -> dict[str, list[str]]:
    data = [
        ('trade', ['1', '2', '3']),
        ('asset_movement', ['1', '4', '5', '7']),
        (
            'history_event',
            [
                '10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53',
                '10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
                '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
            ]),
    ]

    for action_type, action_ids in data:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'ignoredactionsresource',
            ), json={'action_type': action_type, 'data': action_ids},
        )
        assert_simple_ok_response(response)

    # get all entries and make sure nothing new slipped in
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    serialized_result = {k.serialize(): v for k, v in result.items()}
    assert serialized_result == {
        'trade': {'1', '2', '3'},
        'asset_movement': {'1', '4', '5', '7'},
        'history_event': {
            '10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53',
            '10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
            '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
        },
    }
    return serialized_result


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ignored_actions(rotkehlchen_api_server):
    data = _populate_ignored_actions(rotkehlchen_api_server)

    # try to add at least one already existing id
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'trade', 'data': ['1', '9', '11']},
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='One of the given action ids already exists in the database',
    )

    # get all entries and make sure nothing new slipped in
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    serialized_result = {k.serialize(): v for k, v in result.items()}
    assert serialized_result == data


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_ignored_actions(rotkehlchen_api_server):
    _populate_ignored_actions(rotkehlchen_api_server)
    # remove a few entries of one type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'asset_movement', 'data': ['1', '7']},
    )
    assert_simple_ok_response(response)

    # remove an evm transaction
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={
            'action_type': 'history_event',
            'data': ['10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53'],
        },
    )
    assert_simple_ok_response(response)

    # remove all entries of one type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'trade', 'data': ['1', '2', '3']},
    )
    assert_simple_ok_response(response)

    # try to remove non existing entries
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'history_event', 'data': ['42', '666']},
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Tried to remove 2 ignored actions that do not exist',
    )

    # get all entries again and make sure deleted ones do not appear
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    serialized_result = {k.serialize(): v for k, v in result.items()}
    assert serialized_result == {
        'asset_movement': {'4', '5'},
        'history_event': {
            '10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53',
            '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
        },
    }


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_ignore_history_events_in_accountant(rotkehlchen_api_server):
    """Test that ignored history events are correctly ignored by the accountant"""
    accountant = rotkehlchen_api_server.rest_api.rotkehlchen.accountant
    events_list = [
        HistoryEvent(
            event_identifier='a',
            sequence_index=0,
            timestamp=TimestampMS(1467279735000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(FVal(1000)),
            asset=A_ETH,
        ), HistoryEvent(
            event_identifier='b',
            sequence_index=0,
            timestamp=TimestampMS(1467279736000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(FVal(5)),
            asset=A_DAI,
            notes='boo',
        ),
    ]

    # Set the server to ignore second event
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'history_event', 'data': ['b']},
    )
    assert_simple_ok_response(response)

    # Retrieve ignored actions mapping. Should contain 2
    with accountant.db.conn.read_ctx() as cursor:
        ignored_actions = accountant.db.get_ignored_action_ids(cursor, action_type=None)
    ignored = []
    # Call the should_ignore method used in the accountant
    for event in events_list:
        should_ignore = event.should_ignore(ignored_actions)
        ignored.append(should_ignore)

    assert ignored == [False, True]
