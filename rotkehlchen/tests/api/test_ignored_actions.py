from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

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

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _populate_ignored_actions(rotkehlchen_api_server: 'APIServer') -> set[str]:
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'data': [
            '10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53',
            '10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
            '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
            '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b54',
            '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846df4b53',
        ]},
    )
    assert_simple_ok_response(response)

    # get all entries and make sure nothing new slipped in
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor)
    assert result == {
        '10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53',
        '10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
        '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
        '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b54',
        '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846df4b53',
    }
    return result


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ignored_actions(rotkehlchen_api_server: 'APIServer') -> None:
    data = _populate_ignored_actions(rotkehlchen_api_server)

    # try to add at least one already existing id
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={
            'data': [
                '10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
                '10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53',
                '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
            ],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='One of the given action ids already exists in the database',
    )

    # get all entries and make sure nothing new slipped in
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor)
    assert result == data


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_ignored_actions(rotkehlchen_api_server: 'APIServer') -> None:
    _populate_ignored_actions(rotkehlchen_api_server)
    # remove a few entries of one type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'data': ['10x9c7096c0a2a5e1b8bcf444a6929881af55d83fb0b713ad3f7f0028006ff9ec53']},
    )
    assert_simple_ok_response(response)

    # remove an evm transaction
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'data': ['10x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53']},
    )
    assert_simple_ok_response(response)

    # remove all entries of one type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={
            'data': [
                '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b53',
                '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846af4b54',
                '100x6328a70f18534d60f6fc085c22a1273fd4a7c7f2e6cdc3bb49168c2846df4b53',
            ],
        },
    )
    assert_simple_ok_response(response)

    # try to remove non-existing entries
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'data': ['42', '666']},
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Tried to remove 2 ignored actions that do not exist',
    )

    # get all entries again and make sure deleted ones do not appear
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor)
    assert result == set()


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_ignore_history_events_in_accountant(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that ignored history events are correctly ignored by the accountant"""
    accountant = rotkehlchen_api_server.rest_api.rotkehlchen.accountant
    events_list = [
        HistoryEvent(
            group_identifier='a',
            sequence_index=0,
            timestamp=TimestampMS(1467279735000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal(1000),
            asset=A_ETH,
        ), HistoryEvent(
            group_identifier='b',
            sequence_index=0,
            timestamp=TimestampMS(1467279736000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal(5),
            asset=A_DAI,
            notes='boo',
        ),
    ]

    # Set the server to ignore second event
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'data': ['b']},
    )
    assert_simple_ok_response(response)

    # Retrieve ignored actions mapping. Should contain 2
    with accountant.db.conn.read_ctx() as cursor:
        ignored_actions = accountant.db.get_ignored_action_ids(cursor)
    ignored = []
    # Call the should_ignore method used in the accountant
    for event in events_list:
        should_ignore = event.should_ignore(ignored_actions)
        ignored.append(should_ignore)

    assert ignored == [False, True]
