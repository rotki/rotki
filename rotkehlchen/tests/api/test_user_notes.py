from http import HTTPStatus

import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_user_notes_entries


def test_add_get_user_notes(rotkehlchen_api_server):
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'title': '#1',
            'content': 'Romero Uno',
            'location': 'manual balances',
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result == 1

    # try adding more user notes
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'title': '#2',
            'content': 'ETH/MOON TP@GOBLIN',
            'location': 'ledger actions',
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result == 2
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'title': '#3',
            'content': 'Let us try a new approach',
            'location': 'trades',
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result == 3

    # check that a total of user notes are in the db.
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert len(result) == 3


def test_edit_user_notes(rotkehlchen_api_server):
    generated_entries = make_user_notes_entries()
    for entry in generated_entries:
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_user_note(
            title=entry['title'],
            content=entry['content'],
            location=entry['location'],
        )

    # check that editing a user note works as expected.
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 1,
            'title': 'TODO List',
            'content': 'Dont sleep, wake up!!!!!',
            'location': 'manual balances',
            'last_update_timestamp': 12345678,
        },
    )
    assert_simple_ok_response(response)
    # confirm that the note was actually edited in the db
    user_notes = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.get_all_user_notes()
    for note in user_notes:
        if note.identifier == 1:
            assert note.content == 'Dont sleep, wake up!!!!!'

    # check that editing a user note with an invalid identifier fails
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 10,
            'title': 'INVALID 101',
            'content': 'Dont sleep, wake up!!!!!',
            'location': 'manual balances',
            'last_update_timestamp': 12345678,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='User note with identifier 10 does not exist',
        status_code=HTTPStatus.CONFLICT,
    )


def test_delete_user_notes(rotkehlchen_api_server):
    generated_entries = make_user_notes_entries()
    for entry in generated_entries:
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_user_note(
            title=entry['title'],
            content=entry['content'],
            location=entry['location'],
        )

    # check that deleting a user note works as expected
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 1,
        },
    )
    assert_proper_response(response, status_code=HTTPStatus.OK)

    # check that the user notes count reduced in db
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert len(result) == 2

    # check that deleting a user note that is deleted already fails.
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 1,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='User note with identifier 1 not found in database',
        status_code=HTTPStatus.CONFLICT,
    )
