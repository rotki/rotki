import csv
import os
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.export.csv import FILENAME_HISTORY_EVENTS_CSV
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test
from rotkehlchen.tests.utils.history_base_entry import add_entries
from rotkehlchen.types import Location, TimestampMS


def assert_csv_export_response(
        response: requests.Response,
        csv_dir: Path,
        expected_count: int = 9,
        is_download: bool = False,
        includes_extra_headers: bool = True,
        csv_delimiter: str = ',',
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
        'identifier',
        'entry_type',
        'event_identifier',
        'sequence_index',
        'timestamp',
        'location',
        'asset',
        'amount',
        'fiat_value',
        'event_type',
        'event_subtype',
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
        reader = csv.DictReader(csvfile, delimiter=csv_delimiter)
        count = 0
        for row in reader:
            assert tuple(row.keys())[:len(base_headers)] == base_headers, 'order of columns does not match'  # noqa: E501

            for attr in base_headers:
                assert row[attr] is not None
            if includes_extra_headers:
                for attr in extra_headers:
                    assert attr in row
            count += 1
        assert count == expected_count


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_history_export_download_csv(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that the csv export/download REST API endpoint works correctly."""
    db = DBHistoryEvents(rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen.data.db)
    add_entries(events_db=db)

    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))
    download_dir = str(tmpdir_factory.mktemp('download_dir'))

    # now query the export endpoint with json body
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'async_query': False, 'directory_path': csv_dir},
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
        json={'async_query': False},
    )
    temp_csv_file = Path(download_dir, FILENAME_HISTORY_EVENTS_CSV)
    temp_csv_file.write_bytes(response.content)
    assert_csv_export_response(response, download_dir, is_download=True)


@pytest.mark.parametrize('db_settings', [{'csv_export_delimiter': ';'}])
def test_history_export_csv_custom_delimiter(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that using a custom csv delimiter works correctly."""
    database = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen.data.db
    add_entries(events_db=DBHistoryEvents(database=database))

    with database.conn.read_ctx() as cursor:
        csv_delimiter = database.get_settings(cursor).csv_export_delimiter

    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'async_query': False, 'directory_path': csv_dir},
    )
    assert_csv_export_response(response, csv_dir, csv_delimiter=csv_delimiter)


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
    db = DBHistoryEvents(rotki.data.db)
    add_entries(events_db=db)

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


@pytest.mark.vcr
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
def test_history_export_csv_free_limit(
        rotkehlchen_api_server_with_exchanges,
        start_with_valid_premium,
        tmpdir_factory,
):
    """Test that the free history events limit is respected."""
    database = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen.data.db
    history_events = DBHistoryEvents(database=database)
    event_identifiers = [make_evm_tx_hash().hex() for _ in range(3)]  # pylint: disable=no-member
    dummy_events = (
        HistoryEvent(
            event_identifier=event_identifiers[0],
            sequence_index=0,
            timestamp=TimestampMS(1700000000000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(FVal(1)),
        ), HistoryEvent(
            event_identifier=event_identifiers[1],
            sequence_index=0,
            timestamp=TimestampMS(1710000000000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(FVal(2)),
        ), HistoryEvent(
            event_identifier=event_identifiers[2],
            sequence_index=0,
            timestamp=TimestampMS(1720000000000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(FVal(3)),
        ),
    )

    with database.conn.write_ctx() as write_cursor:
        history_events.add_history_events(
            write_cursor=write_cursor,
            history=dummy_events,
        )

    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    with patch(target='rotkehlchen.db.history_events.FREE_HISTORY_EVENTS_LIMIT', new=1):
        response = requests.post(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'exporthistoryeventresource',
            directory_path=csv_dir,
        ))
        assert_csv_export_response(
            response=response,
            csv_dir=csv_dir,
            expected_count=3 if start_with_valid_premium else 1,
            includes_extra_headers=False,
        )

        response = requests.post(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'exporthistoryeventresource',
            directory_path=csv_dir,
            from_timestamp=1710000000,
        ))
        assert_csv_export_response(
            response=response,
            csv_dir=csv_dir,
            expected_count=2 if start_with_valid_premium else 1,
            includes_extra_headers=False,
        )
