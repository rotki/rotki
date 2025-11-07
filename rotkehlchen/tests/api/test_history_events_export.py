import csv
import re
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DEFAULT_DATE_DISPLAY_FORMAT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test
from rotkehlchen.tests.utils.history_base_entry import add_entries
from rotkehlchen.types import Location, TimestampMS


def assert_csv_export_response(
        response: requests.Response,
        csv_path: Path,
        expected_count: int = 14,
        is_download: bool = False,
        includes_extra_headers: bool = True,
        csv_delimiter: str = ',',
) -> None:
    """
    Asserts that a CSV export response meets certain criteria.
    Args:
        response: The response object returned from the CSV export request.
        csv_path: The path where the CSV files are expected to be located.
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
        'timestamp',
        'event_type',
        'event_subtype',
        'location',
        'location_label',
        'asset',
        'asset_symbol',
        'amount',
        'fiat_value',
        'identifier',
        'entry_type',
        'group_identifier',
        'sequence_index',
        'direction',
        'extra_data',
    )  # skip auto_notes and user_notes here since they may or may not be present

    extra_headers = (
        # evm event
        'tx_ref',
        'counterparty',
        'address',

        # eth staking events
        'validator_index',
    )

    # check the csv files were generated successfully
    timestamp_check = re.compile(r'\d{2}/\d{2}/\d{4}')
    with csv_path.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=csv_delimiter)
        count, last_ts = 0, 0.0
        for idx, row in enumerate(reader):
            assert tuple(row.keys())[:len(base_headers)] == base_headers, 'order of columns does not match'  # noqa: E501

            for attr in base_headers:
                if attr == 'timestamp':
                    timestamp_as_int = datetime.strptime(
                        row['timestamp'],
                        DEFAULT_DATE_DISPLAY_FORMAT,
                    ).astimezone().timestamp()
                    if idx > 0:  # ensure that the events are sorted by timestamp
                        assert timestamp_as_int <= last_ts

                    last_ts = timestamp_as_int
                    assert timestamp_check.search(row['timestamp']), 'timestamp is not properly formatted'  # noqa: E501

                assert row[attr] is not None
            if includes_extra_headers:
                for attr in extra_headers:
                    assert attr in row
            count += 1
        assert count == expected_count


@pytest.mark.vcr(filter_query_parameters=['api_key'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
@pytest.mark.freeze_time('2025-04-30')
def test_history_export_download_csv(
        rotkehlchen_api_server_with_exchanges: APIServer,
        tmpdir_factory: pytest.TempdirFactory,
) -> None:
    """Test that the csv export/download REST API endpoint works correctly."""
    db = DBHistoryEvents(rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen.data.db)
    add_entries(events_db=db)

    csv_dir = Path(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = Path(tmpdir_factory.mktemp('test_csv_dir2'))
    download_dir = Path(tmpdir_factory.mktemp('download_dir'))

    # now query the export endpoint with json body
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'async_query': False, 'directory_path': str(csv_dir)},
    )
    assert_csv_export_response(response, csv_dir / 'historyevents_until_20250430.csv')

    # now query the export endpoint with query params
    response = requests.post(api_url_for(
        rotkehlchen_api_server_with_exchanges,
        'exporthistoryeventresource',
        directory_path=csv_dir2,
        from_timestamp=1500000000,
        to_timestamp=1600000000,
    ))
    assert_csv_export_response(response, csv_dir2 / 'historyevents_20170714_to_20200913.csv', 2, includes_extra_headers=False)  # noqa: E501

    # now query the export endpoint with no directory specified
    response = requests.put(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'async_query': True},
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(
        rotkehlchen_api_server_with_exchanges,
        task_id,
    )
    file_path = outcome['result']['file_path']

    # download the csv exported in the last api call
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistorydownloadresource'),
        json={'file_path': file_path},
    )

    temp_csv_file = Path(download_dir, 'historyevents_until_20250430.csv')
    temp_csv_file.write_bytes(response.content)
    assert_csv_export_response(response, temp_csv_file, is_download=True)


@pytest.mark.vcr
@pytest.mark.parametrize('db_settings', [{'csv_export_delimiter': ';'}])
@pytest.mark.freeze_time('2025-04-30')
def test_history_export_csv_custom_delimiter(
        rotkehlchen_api_server_with_exchanges: APIServer,
        tmpdir_factory: pytest.TempdirFactory,
) -> None:
    """Test that using a custom csv delimiter works correctly."""
    database = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen.data.db
    add_entries(events_db=DBHistoryEvents(database=database))

    with database.conn.read_ctx() as cursor:
        csv_delimiter = database.get_settings(cursor).csv_export_delimiter

    csv_dir = Path(tmpdir_factory.mktemp('test_csv_dir'))
    response = requests.post(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'exporthistoryeventresource'),
        json={'async_query': False, 'directory_path': str(csv_dir)},
    )
    assert_csv_export_response(response, csv_dir / 'historyevents_until_20250430.csv', csv_delimiter=csv_delimiter)  # noqa: E501


def test_history_export_csv_errors(
        rotkehlchen_api_server_with_exchanges: APIServer,
        tmpdir_factory: pytest.TempdirFactory,
) -> None:
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


@pytest.mark.vcr(filter_query_parameters=['api_key'])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.freeze_time('2025-04-30')
def test_history_export_csv_free_limit(
        rotkehlchen_api_server_with_exchanges: APIServer,
        start_with_valid_premium: bool,
        tmpdir_factory: Any,
) -> None:
    """Test that the free history events limit is respected."""
    database = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen.data.db
    history_events = DBHistoryEvents(database=database)
    group_identifiers = [str(make_evm_tx_hash()) for _ in range(3)]
    dummy_events = (
        HistoryEvent(
            group_identifier=group_identifiers[0],
            sequence_index=0,
            timestamp=TimestampMS(1700000000000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ONE,
        ), HistoryEvent(
            group_identifier=group_identifiers[1],
            sequence_index=0,
            timestamp=TimestampMS(1710000000000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ), HistoryEvent(
            group_identifier=group_identifiers[2],
            sequence_index=0,
            timestamp=TimestampMS(1720000000000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(3),
        ),
    )

    with database.conn.write_ctx() as write_cursor:
        history_events.add_history_events(
            write_cursor=write_cursor,
            history=dummy_events,
        )

    csv_dir = Path(tmpdir_factory.mktemp('test_csv_dir'))
    with patch(target='rotkehlchen.premium.premium.FREE_HISTORY_EVENTS_LIMIT', new=1):
        response = requests.post(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'exporthistoryeventresource',
            directory_path=csv_dir,
        ))
        assert_csv_export_response(
            response=response,
            csv_path=csv_dir / 'historyevents_until_20250430.csv',
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
            csv_path=csv_dir / 'historyevents_20240309_to_20250430.csv',
            expected_count=2 if start_with_valid_premium else 1,
            includes_extra_headers=False,
        )

        response = requests.post(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'exporthistoryeventresource',
        ), json={
            'directory_path': str(csv_dir),
            'event_types': [HistoryEventType.TRADE.serialize(), HistoryEventType.TRANSFER.serialize()],  # noqa: E501
            'event_subtypes': [HistoryEventSubType.NONE.serialize()],
        })
        assert_csv_export_response(
            response=response,
            csv_path=csv_dir / 'historyevents_until_20250430_types_trade-transfer_subtypes_none.csv',  # noqa: E501
            expected_count=3 if start_with_valid_premium else 1,
            includes_extra_headers=False,
        )
