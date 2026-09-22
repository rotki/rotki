import json
from http import HTTPStatus
from typing import TYPE_CHECKING

import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)

if TYPE_CHECKING:
    from pathlib import Path

    from rotkehlchen.api.server import APIServer

EVENTS_HEADER = 'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp\n'


def _write_events_csv(directory: Path, locations: list[str]) -> Path:
    (filepath := directory / 'events.csv').write_text(EVENTS_HEADER + ''.join(
        f'Deposit,{location},EUR,{idx + 1},,,,{1700000000000 + idx}\n'
        for idx, location in enumerate(locations)
    ))
    return filepath


def _add_location(server: APIServer, name: str, parent_identifier: str) -> str:
    return assert_proper_sync_response_with_result(requests.post(
        api_url_for(server, 'locationstreeresource'),
        json={'name': name, 'parent_identifier': parent_identifier},
    ))['identifier']


def _event_locations(server: APIServer) -> dict[str, str]:
    """The location of the imported events by their amount"""
    with server.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
        return dict(cursor.execute('SELECT amount, location FROM history_events'))


def test_import_preflight_and_mappings(rotkehlchen_api_server: APIServer, tmp_path: Path) -> None:
    """A generic import into a custom location resolves it by name. Unknown and ambiguous
    values are reported by the preflight and refuse the import until they are mapped, and a
    mapping saved as an alias resolves on the next import."""
    server = rotkehlchen_api_server
    old_exchange = _add_location(server, 'My old exchange', 'exchanges')
    ing = _add_location(server, 'ING', 'banks')
    other_ing = _add_location(server, 'ING', 'other')
    filepath = _write_events_csv(tmp_path, ['kraken', 'My old exchange', 'ING', 'luno', 'kraken'])

    def preflight(**payload: object) -> list[dict]:
        return assert_proper_sync_response_with_result(requests.put(
            api_url_for(server, 'dataimportpreflightresource'),
            json={'source': 'rotki_events', 'file': str(filepath)} | payload,
        ))['locations']

    assert preflight() == [
        {'value': 'ING', 'status': 'ambiguous', 'location': None, 'candidates': sorted([ing, other_ing])},  # noqa: E501
        {'value': 'My old exchange', 'status': 'resolved', 'location': old_exchange, 'candidates': []},  # noqa: E501
        {'value': 'kraken', 'status': 'resolved', 'location': 'kraken', 'candidates': []},
        {'value': 'luno', 'status': 'unresolved', 'location': None, 'candidates': []},
    ]
    response = requests.put(
        api_url_for(server, 'dataimportresource'),
        json={'source': 'rotki_events', 'file': str(filepath), 'location_mappings': {'luno': 'external'}},  # noqa: E501
    )
    assert_error_response(response, contained_in_msg='Map them first', status_code=HTTPStatus.CONFLICT, result_exists=True)  # noqa: E501
    assert [x['value'] for x in response.json()['result']['locations'] if x['status'] != 'resolved'] == ['ING']  # noqa: E501
    assert _event_locations(server) == {}

    for mappings, message in (
        ({'ING': 'total'}, 'is the total'),
        ({'ING': 'custom:missing'}, 'does not exist'),
    ):
        assert_error_response(
            response=requests.put(
                api_url_for(server, 'dataimportpreflightresource'),
                json={'source': 'rotki_events', 'file': str(filepath), 'location_mappings': mappings},  # noqa: E501
            ),
            contained_in_msg=message,
        )
    assert all(x['status'] == 'resolved' for x in preflight(location_mappings={'ING': ing, 'luno': 'external'}))  # noqa: E501

    with open(filepath, 'rb') as infile:  # a form upload carries the mappings as JSON
        assert assert_proper_sync_response_with_result(requests.post(
            api_url_for(server, 'dataimportresource'),
            files={'file': infile},
            data={'source': 'rotki_events', 'location_mappings': json.dumps({'ING': ing, 'luno': 'external'})},  # noqa: E501
        )) is True
    assert _event_locations(server) == {'1': 'kraken', '2': old_exchange, '3': ing, '4': 'external', '5': 'kraken'}  # noqa: E501

    # saving the choice as an alias makes the next import of the bank resolve by itself
    aliases_url = api_url_for(server, 'locationaliasesresource')
    assert assert_proper_sync_response_with_result(requests.put(aliases_url, json={'alias': 'ING', 'location_identifier': other_ing})) is True  # noqa: E501
    assert assert_proper_sync_response_with_result(requests.get(aliases_url)) == [{'alias': 'ING', 'location_identifier': other_ing}]  # noqa: E501
    assert preflight()[0] == {'value': 'ING', 'status': 'resolved', 'location': other_ing, 'candidates': []}  # noqa: E501
    assert_error_response(
        response=requests.put(aliases_url, json={'alias': 'All', 'location_identifier': 'total'}),
        contained_in_msg='is the total',
    )
    assert assert_proper_sync_response_with_result(requests.delete(aliases_url, json={'alias': 'ing'})) is True  # noqa: E501
    assert_error_response(
        response=requests.delete(aliases_url, json={'alias': 'ing'}),
        contained_in_msg='does not exist',
        status_code=HTTPStatus.NOT_FOUND,
    )


def test_import_preflight_other_formats(rotkehlchen_api_server: APIServer, tmp_path: Path) -> None:
    """Formats without a location column need no mapping"""
    filepath = _write_events_csv(tmp_path, ['luno'])
    assert assert_proper_sync_response_with_result(requests.put(
        api_url_for(rotkehlchen_api_server, 'dataimportpreflightresource'),
        json={'source': 'cointracking', 'file': str(filepath)},
    )) == {'locations': []}
