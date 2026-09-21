from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.images import location_images_dir
from rotkehlchen.locations.types import LocationIdentifier
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

PACKAGED_IMAGES_DIR = Path(__file__).resolve().parents[3] / 'frontend' / 'app' / 'public' / 'assets' / 'images' / 'protocols'  # noqa: E501


def _add_location(server: APIServer, **payload: str) -> dict:
    return assert_proper_sync_response_with_result(requests.post(
        api_url_for(server, 'locationstreeresource'),
        json=payload,
    ))


def _edit_location(server: APIServer, identifier: str, **payload: object) -> requests.Response:
    return requests.patch(
        api_url_for(server, 'customlocationresource', identifier=identifier),
        json=payload,
    )


def test_custom_location_crud(rotkehlchen_api_server: APIServer) -> None:
    """Custom locations can be created anywhere in the tree, edited, archived and deleted
    when unused, while built-in locations stay immutable"""
    server = rotkehlchen_api_server
    locations = assert_proper_sync_response_with_result(
        requests.get(api_url_for(server, 'locationstreeresource')),
    )
    assert {'identifier': 'ethereum', 'name': 'Ethereum Mainnet', 'parent_identifier': 'evm chains', 'is_builtin': True, 'is_active': True, 'icon': None, 'image': 'ethereum.svg'} in locations  # noqa: E501

    ing = _add_location(server, name='ING', parent_identifier='banks', icon='lu-landmark')
    assert ing['identifier'].startswith('custom:')
    assert {k: v for k, v in ing.items() if k != 'identifier'} == {
        'name': 'ING', 'parent_identifier': 'banks', 'is_builtin': False, 'is_active': True,
        'icon': 'lu-landmark', 'image': None,
    }
    savings = _add_location(server, name='Savings', parent_identifier=ing['identifier'])
    for payload, message in (
        ({'name': 'ing', 'parent_identifier': 'banks'}, 'already exists at the same level'),
        ({'name': 'DKB', 'parent_identifier': 'nowhere'}, 'does not exist'),
        ({'name': 'DKB', 'parent_identifier': 'banks', 'icon': 'landmark'}, 'is not an icon name'),
        ({'name': '', 'parent_identifier': 'banks'}, 'name'),
    ):
        assert_error_response(
            response=requests.post(api_url_for(server, 'locationstreeresource'), json=payload),
            contained_in_msg=message,
        )

    # a dry run reports the paths of a move without doing it
    result = assert_proper_sync_response_with_result(
        _edit_location(server, savings['identifier'], parent_identifier='other', dry_run=True),
    )
    assert (result['old_path'], result['new_path']) == (['Total', 'Banks', 'ING', 'Savings'], ['Total', 'Other', 'Savings'])  # noqa: E501
    assert result['location']['parent_identifier'] == 'other'
    locations = {x['identifier']: x for x in assert_proper_sync_response_with_result(
        requests.get(api_url_for(server, 'locationstreeresource')),
    )}
    assert locations[savings['identifier']]['parent_identifier'] == ing['identifier']

    result = assert_proper_sync_response_with_result(_edit_location(
        server, ing['identifier'], name='ING DiBa', parent_identifier='other', icon=None,
    ))
    assert result['location'] == ing | {'name': 'ING DiBa', 'parent_identifier': 'other', 'icon': None}  # noqa: E501
    assert result['new_path'] == ['Total', 'Other', 'ING DiBa']
    edit_errors: tuple[tuple[str, dict[str, Any], str, HTTPStatus], ...] = (
        ('kraken', {'name': 'Krakenn'}, 'shipped by rotki', HTTPStatus.BAD_REQUEST),
        (ing['identifier'], {'parent_identifier': savings['identifier']}, 'below itself', HTTPStatus.BAD_REQUEST),  # noqa: E501
        (ing['identifier'], {'is_active': False}, 'has active children', HTTPStatus.BAD_REQUEST),
        ('custom:missing', {'name': 'x'}, 'does not exist', HTTPStatus.NOT_FOUND),
    )
    for identifier, payload, message, status in edit_errors:
        assert_error_response(
            response=_edit_location(server, identifier, **payload),
            contained_in_msg=message,
            status_code=status,
        )

    # data at a location blocks its deletion, archiving keeps it
    db = server.rest_api.rotkehlchen.data.db
    with db.user_write() as write_cursor:
        DBHistoryEvents(db).add_history_event(write_cursor, HistoryEvent(
            group_identifier='deposit',
            sequence_index=0,
            timestamp=TimestampMS(1700000000000),
            location=LocationIdentifier(savings['identifier']),
            asset=A_EUR,
            amount=ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
        ))

    for identifier, expected in (
        (savings['identifier'], {'usage': {'history_events': 1}, 'deletable': False}),
        (ing['identifier'], {'usage': {'children': 1}, 'deletable': False}),
        ('kraken', {'usage': {}, 'deletable': False}),
    ):
        assert assert_proper_sync_response_with_result(requests.get(
            api_url_for(server, 'locationusageresource', identifier=identifier),
        )) == expected

    assert_error_response(
        response=requests.delete(api_url_for(server, 'customlocationresource', identifier=savings['identifier'])),  # noqa: E501
        contained_in_msg='still in use',
        status_code=HTTPStatus.CONFLICT,
    )
    assert assert_proper_sync_response_with_result(
        _edit_location(server, savings['identifier'], is_active=False),
    )['location']['is_active'] is False

    unused = _add_location(server, name='Unused', parent_identifier='exchanges')
    assert assert_proper_sync_response_with_result(requests.delete(
        api_url_for(server, 'customlocationresource', identifier=unused['identifier']),
    )) is True
    assert_error_response(
        response=requests.delete(api_url_for(server, 'customlocationresource', identifier=unused['identifier'])),  # noqa: E501
        contained_in_msg='does not exist',
        status_code=HTTPStatus.NOT_FOUND,
    )


def test_custom_location_image(rotkehlchen_api_server: APIServer) -> None:
    """An uploaded image replaces the previous one, is served with an etag, and is removed
    together with its location"""
    server = rotkehlchen_api_server
    images_dir = location_images_dir(server.rest_api.rotkehlchen.data.user_data_dir)  # type: ignore[arg-type]  # logged in
    identifier = _add_location(server, name='ING', parent_identifier='banks')['identifier']
    image_url = api_url_for(server, 'locationimageresource', identifier=identifier)

    def upload(image: str) -> requests.Response:
        with open(PACKAGED_IMAGES_DIR / image, 'rb') as infile:
            return requests.post(image_url, files={'file': infile})

    assert requests.get(image_url).status_code == HTTPStatus.NOT_FOUND
    first = assert_proper_sync_response_with_result(upload('kraken.svg'))['image']
    assert [x.name for x in images_dir.iterdir()] == [first]
    response = requests.get(image_url)
    assert response.status_code == HTTPStatus.OK
    assert response.content == (PACKAGED_IMAGES_DIR / 'kraken.svg').read_bytes()
    assert response.headers['Content-Type'] == 'image/svg+xml'
    assert requests.get(image_url, headers={'If-None-Match': response.headers['ETag']}).status_code == HTTPStatus.NOT_MODIFIED  # noqa: E501

    second = assert_proper_sync_response_with_result(upload('binance.svg'))['image']
    assert second != first
    assert [x.name for x in images_dir.iterdir()] == [second]
    locations = {x['identifier']: x for x in assert_proper_sync_response_with_result(
        requests.get(api_url_for(server, 'locationstreeresource')),
    )}
    assert locations[identifier]['image'] == second

    with open(PACKAGED_IMAGES_DIR / 'kraken.svg', 'rb') as infile:
        assert_error_response(
            response=requests.post(image_url, files={'file': ('kraken.txt', infile)}),
            contained_in_msg='does not end in any of',
        )
        infile.seek(0)
        assert_error_response(
            response=requests.post(
                api_url_for(server, 'locationimageresource', identifier='kraken'),
                files={'file': infile},
            ),
            contained_in_msg='shipped by rotki',
        )
    assert [x.name for x in images_dir.iterdir()] == [second]

    assert assert_proper_sync_response_with_result(requests.delete(image_url)) is True
    assert list(images_dir.iterdir()) == []
    assert requests.get(image_url).status_code == HTTPStatus.NOT_FOUND

    upload('kraken.svg')
    assert requests.delete(api_url_for(server, 'customlocationresource', identifier=identifier)).status_code == HTTPStatus.OK  # noqa: E501
    assert list(images_dir.iterdir()) == []
