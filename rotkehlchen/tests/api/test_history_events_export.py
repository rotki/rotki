import csv
import os
from http import HTTPStatus
from pathlib import Path

import requests

from rotkehlchen.accounting.export.csv import FILENAME_HISTORY_EVENTS_CSV
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test
from rotkehlchen.tests.utils.history_base_entry import add_entries


def assert_csv_export_response(
        response: requests.Response,
        csv_dir: Path,
        expected_count: int = 9,
        is_download: bool = False,
        includes_extra_headers: bool = True,
):
    """
    Asserts that a CSV export response meets certain criteria.
    Args:
        response: The response object returned from the CSV export request.
        csv_dir: The directory where the CSV files are expected to be located.
        expected_count: The expected number of rows in the CSV files.
    Raises:
        AssertionError: If any of the assertions fail.
    """
    if is_download:
        assert response.status_code == HTTPStatus.OK
    else:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert data['result'] is True

    base_headers = (
        'location',
        'identifier',
        'entry_type',
        'event_identifier',
        'sequence_index',
        'timestamp',
        'asset',
        'balance_amount',
        'balance_usd_value',
        'event_type',
        'location_label',
        'notes',
    )

    extra_headers = (
        # evm event
        'tx_hash',
        'counterparty',
        'product',
        'address',

        # eth staking events
        'validator_index',
    )

    # check the csv files were generated succesfully
    with open(os.path.join(csv_dir, FILENAME_HISTORY_EVENTS_CSV), newline='', encoding='utf-8') as csvfile:  # noqa: E501
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            for attr in base_headers:
                assert row[attr] is not None
            if includes_extra_headers:
                for attr in extra_headers:
                    assert attr in row
            count += 1
        assert count == expected_count


def test_history_export_download_csv(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that the csv export/download REST API endpoint works correctly."""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    add_entries(server=rotkehlchen_api_server_with_exchanges, events_db=db, add_directly=True)

    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))
    download_dir = str(tmpdir_factory.mktemp('download_dir'))

    # now query the export endpoint with json body
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={
            'directory_path': csv_dir,
        },
    )
    assert_csv_export_response(response, csv_dir)

    # now query the export endpoint with query params
    response = requests.post(api_url_for(
        rotkehlchen_api_server_with_exchanges,
        'exporthistoryeventresource',
        directory_path=csv_dir2,
        from_timestamp=1500000000,
        to_timestamp=1600000000,
    ))
    assert_csv_export_response(response, csv_dir2, 2, includes_extra_headers=False)

    # now query the download CSV endpoint
    response = requests.put(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
    )
    temp_csv_file = Path(download_dir, FILENAME_HISTORY_EVENTS_CSV)
    temp_csv_file.write_bytes(response.content)
    assert_csv_export_response(response, download_dir, is_download=True)


def test_history_export_csv_errors(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that errors on the csv export REST API endpoint are handled correctly"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
    )
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))

    # Query the export endpoint without first having queried the history
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'directory_path': csv_dir},
    )
    assert_error_response(
        response=response,
        contained_in_msg='No history processed in order to perform an export',
        status_code=HTTPStatus.CONFLICT,
    )

    # Now, add data for exporting
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    db = DBHistoryEvents(rotki.data.db)
    add_entries(server=rotkehlchen_api_server_with_exchanges, events_db=db, add_directly=True)

    # And now provide non-existing path for directory
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'directory_path': '/idont/exist/for/sure/'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"directory_path": ["Given path /idont/exist/for/sure/ does not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # And now provide valid path but not directory
    temporary_file = Path(Path(csv_dir) / 'f.txt')
    temporary_file.touch()
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'directory_path': str(temporary_file)},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a directory',
        status_code=HTTPStatus.BAD_REQUEST,
    )
