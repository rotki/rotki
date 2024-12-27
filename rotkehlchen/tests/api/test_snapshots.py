import csv
import datetime
import os
import tempfile
import zipfile
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_AVAX, A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.snapshots import (
    BALANCES_FILENAME,
    BALANCES_FOR_IMPORT_FILENAME,
    LOCATION_DATA_FILENAME,
    LOCATION_DATA_IMPORT_FILENAME,
)
from rotkehlchen.db.utils import BalanceType, DBAssetBalance, LocationData
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBWriterClient

BALANCES_IMPORT_HEADERS = ['timestamp', 'category', 'asset_identifier', 'amount', 'usd_value']
BALANCES_IMPORT_INVALID_HEADERS = ['timestamp', 'category', 'asset', 'amount', 'value']
LOCATION_DATA_IMPORT_HEADERS = ['timestamp', 'location', 'usd_value']
LOCATION_DATA_IMPORT_INVALID_HEADERS = ['timestamp', 'location', 'value']

NFT_TOKEN_ID = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_11'


def _populate_db_with_balances(
        write_cursor: 'DBWriterClient',
        db: 'DBHandler',
        ts: Timestamp,
) -> None:
    db.add_multiple_balances(
        write_cursor=write_cursor,
        balances=[
            DBAssetBalance(
                category=BalanceType.ASSET,
                time=ts,
                asset=A_BTC,
                amount=FVal('1.00'),
                usd_value=FVal('178.44'),
            ),
            DBAssetBalance(
                category=BalanceType.ASSET,
                time=ts,
                asset=A_AVAX,
                amount=FVal('1.00'),
                usd_value=FVal('87'),
            ),
        ])


def _populate_db_with_balances_unknown_asset(
        write_cursor: 'DBWriterClient',
        ts: Timestamp,
) -> None:
    write_cursor.execute('INSERT INTO assets(identifier) VALUES (?)', ('YABIRXROTKI',))
    serialized_balances = [
        (ts, 'BTC', '1.00', '178.44', BalanceType.ASSET.serialize_for_db()),
        (ts, 'YABIRXROTKI', '1.00', '87', BalanceType.ASSET.serialize_for_db()),
    ]
    write_cursor.executemany(
        'INSERT INTO timed_balances('
        '    timestamp, currency, amount, usd_value, category) '
        ' VALUES(?, ?, ?, ?, ?)',
        serialized_balances,
    )


def _populate_db_with_location_data(
        write_cursor: 'DBWriterClient',
        db: 'DBHandler',
        ts: Timestamp,
    ) -> None:
    db.add_multiple_location_data(
        write_cursor=write_cursor,
        location_data=[
            LocationData(
                time=ts,
                location='A',
                usd_value='100.00',
            ),
            LocationData(
                time=ts,
                location='B',
                usd_value='200.00',
            ),
            LocationData(
                time=ts,
                location='H',
                usd_value='50.00',
            ),
        ],
    )


def _write_balances_csv_row(
        writer: 'csv.DictWriter',
        timestamp: Timestamp,
        include_unknown_asset: bool | None = None,
) -> None:
    if include_unknown_asset:
        writer.writerow(
            {
                'timestamp': timestamp,
                'category': 'asset',
                'asset_identifier': 'XUNKNOWNX',
                'amount': '10.555',
                'usd_value': '100.555',
            },
        )
    writer.writerow(
        {
            'timestamp': timestamp,
            'category': 'asset',
            'asset_identifier': NFT_TOKEN_ID,
            'amount': '10.555',
            'usd_value': '100.555',
        },
    )
    writer.writerow(
        {
            'timestamp': timestamp,
            'category': 'asset',
            'asset_identifier': 'BTC',
            'amount': '1',
            'usd_value': '40000.000',
        },
    )


def _write_location_data_csv_row(writer: 'csv.DictWriter', timestamp: Timestamp) -> None:
    writer.writerow(
        {
            'timestamp': timestamp,
            'location': 'blockchain',
            'usd_value': '100.555',
        },
    )
    writer.writerow(
        {
            'timestamp': timestamp,
            'location': 'total',
            'usd_value': '41000.555',
        },
    )


def _write_balances_csv_row_with_invalid_headers(
        writer: 'csv.DictWriter',
        timestamp: Timestamp,
) -> None:
    writer.writerow(
        {
            'timestamp': timestamp,
            'category': 'asset',
            'asset': 'AVAX',
            'amount': '10.555',
            'value': '100.555',
        },
    )
    writer.writerow(
        {
            'timestamp': timestamp,
            'category': 'asset',
            'asset': 'BTC',
            'amount': '1',
            'value': '40000.000',
        },
    )


def _write_location_data_csv_row_with_invalid_headers(
        writer: 'csv.DictWriter',
        timestamp: Timestamp,
) -> None:
    writer.writerow(
        {
            'timestamp': timestamp,
            'location': 'blockchain',
            'value': '100.555',
        },
    )
    writer.writerow(
        {
            'timestamp': timestamp,
            'location': 'total',
            'value': '41000.555',
        },
    )


def _create_snapshot_with_valid_data(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)


def _create_snapshot_with_unknown_asset(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp, include_unknown_asset=True)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)


def _create_snapshot_with_valid_data_for_post(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)


def _create_snapshot_different_timestamps(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp)
        _write_balances_csv_row(writer, Timestamp(timestamp + 500))

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)
        _write_location_data_csv_row(writer, Timestamp(timestamp + 1000))


def _create_snapshot_with_invalid_headers(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = BALANCES_IMPORT_INVALID_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row_with_invalid_headers(writer, timestamp)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w', encoding='utf8') as f:
        fieldnames = LOCATION_DATA_IMPORT_INVALID_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row_with_invalid_headers(writer, timestamp)


def validate_timestamp(
        received_serialized_timestamp: str,
        expected_utc_timestamp: Timestamp,
        display_date_in_localtime: bool,
        is_for_import: bool,
) -> None:
    """Validate exported timestamp.

    If is_for_import is True, then the timestamp should be a utc timestamp in seconds.
    If display_date_in_localtime is True, then timestamp should be stringified in local timezone.
    Otherwise the timestamp should be stringified in utc.
    """
    if is_for_import:  # Should always be a numeric utc timestamp
        deserialized_timestamp = deserialize_timestamp(received_serialized_timestamp)
        assert deserialized_timestamp == expected_utc_timestamp
    else:
        if display_date_in_localtime:  # Check that it respects the timezone
            expected_datetime = datetime.datetime.fromtimestamp(
                expected_utc_timestamp,
                tz=datetime.datetime.now(datetime.UTC).astimezone().tzinfo,
            ).strftime('%Y-%m-%d %H:%M:%S')
        else:  # Should be a stringified utc timestamp
            expected_datetime = datetime.datetime.fromtimestamp(
                expected_utc_timestamp,
                tz=datetime.UTC,
            ).strftime('%Y-%m-%d %H:%M:%S')

        assert received_serialized_timestamp == expected_datetime


def assert_csv_export_response(
        response: requests.Response,
        csv_dir: str,
        main_currency: AssetWithOracles,
        is_download: bool = False,
        expected_entries: int = 2,
        timestamp_validation_data: tuple[Timestamp, bool] | None = None,
) -> None:
    if is_download:
        assert response.status_code == HTTPStatus.OK
    else:
        assert_simple_ok_response(response)

    with open(os.path.join(csv_dir, BALANCES_FILENAME), newline='', encoding='utf8') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 6
            assert row['category'] in {
                'asset',
                'liability',
            }
            assert row['amount'] is not None
            assert row['asset'] is not None
            assert row['asset_symbol'] == Asset(row['asset']).symbol_or_name()
            if timestamp_validation_data is None:
                assert row['timestamp'] is not None
            else:
                validate_timestamp(
                    received_serialized_timestamp=row['timestamp'],
                    expected_utc_timestamp=timestamp_validation_data[0],
                    display_date_in_localtime=timestamp_validation_data[1],
                    is_for_import=False,
                )
            assert row[f'{main_currency.symbol.lower()}_value'] is not None
            count += 1
        assert count == expected_entries

    with open(os.path.join(csv_dir, BALANCES_FOR_IMPORT_FILENAME), newline='', encoding='utf8') as csvfile:  # noqa: E501
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 5
            assert row['category'] in {
                'asset',
                'liability',
            }
            assert row['amount'] is not None
            assert row['asset_identifier'] is not None
            if timestamp_validation_data is None:
                assert row['timestamp'] is not None
            else:
                validate_timestamp(
                    received_serialized_timestamp=row['timestamp'],
                    expected_utc_timestamp=timestamp_validation_data[0],
                    display_date_in_localtime=timestamp_validation_data[1],
                    is_for_import=True,
                )
            assert row['usd_value'] is not None
            count += 1
        assert count == expected_entries

    with open(os.path.join(csv_dir, LOCATION_DATA_FILENAME), newline='', encoding='utf8') as csvfile:  # noqa: E501
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 3
            if timestamp_validation_data is None:
                assert row['timestamp'] is not None
            else:
                validate_timestamp(
                    received_serialized_timestamp=row['timestamp'],
                    expected_utc_timestamp=timestamp_validation_data[0],
                    display_date_in_localtime=timestamp_validation_data[1],
                    is_for_import=False,
                )
            assert Location.deserialize(row['location']) is not None
            assert row[f'{main_currency.symbol.lower()}_value'] is not None
            count += 1
        assert count == 3

    with open(os.path.join(csv_dir, LOCATION_DATA_IMPORT_FILENAME), newline='', encoding='utf8') as csvfile:  # noqa: E501
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 3
            if timestamp_validation_data is None:
                assert row['timestamp'] is not None
            else:
                validate_timestamp(
                    received_serialized_timestamp=row['timestamp'],
                    expected_utc_timestamp=timestamp_validation_data[0],
                    display_date_in_localtime=timestamp_validation_data[1],
                    is_for_import=True,
                )
            assert Location.deserialize(row['location']) is not None
            assert row['usd_value'] is not None
            count += 1
        assert count == 3


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('db_settings', [
    {'display_date_in_localtime': True},
    {'display_date_in_localtime': False},
])
@freeze_time('2023-05-16 19:00:00', tz_offset=6)  # Set timezone to something different than UTC
def test_export_snapshot(
        rotkehlchen_api_server: 'APIServer',
        tmpdir_factory: pytest.TempdirFactory,
    ) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.conn.read_ctx() as cursor:
        display_date_in_localtime = db.get_settings(cursor).display_date_in_localtime

    ts = ts_now()
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))
    with db.user_write() as cursor:
        _populate_db_with_balances(cursor, db, ts)
        _populate_db_with_location_data(cursor, db, ts)
        db.set_settings(cursor, ModifiableDBSettings(
            main_currency=A_EUR.resolve_to_asset_with_oracles()),
        )
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_timestamp_db_snapshots_resource',
                timestamp=ts,
                path=csv_dir,
                action='export',
            ),
        )
        assert_csv_export_response(
            response=response,
            csv_dir=csv_dir,
            main_currency=A_EUR.resolve_to_asset_with_oracles(),
            is_download=False,
            timestamp_validation_data=(ts, display_date_in_localtime),
        )

        db.set_settings(cursor, ModifiableDBSettings(
            main_currency=A_ETH.resolve_to_asset_with_oracles()),
        )
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_timestamp_db_snapshots_resource',
                timestamp=ts,
                path=csv_dir2,
                action='export',
            ),
        )
        assert_csv_export_response(
            response=response,
            csv_dir=csv_dir2,
            main_currency=A_ETH.resolve_to_asset_with_oracles(),
            is_download=False,
            timestamp_validation_data=(ts, display_date_in_localtime),
        )

        db.set_settings(cursor, ModifiableDBSettings(
            main_currency=A_USD.resolve_to_asset_with_oracles()),
        )
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_timestamp_db_snapshots_resource',
                timestamp=ts,
                action='export',
            ),
        )
        assert_error_response(
            response,
            contained_in_msg='A path has to be provided when action is export',
        )


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_export_snapshot_unknown_asset(
        rotkehlchen_api_server: 'APIServer',
        tmpdir_factory: pytest.TempdirFactory,
    ) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    ts = ts_now()
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    with db.user_write() as cursor:
        _populate_db_with_balances_unknown_asset(cursor, ts)
        _populate_db_with_location_data(cursor, db, ts)
        db.set_settings(cursor, ModifiableDBSettings(
            main_currency=A_EUR.resolve_to_asset_with_oracles()),
        )
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_timestamp_db_snapshots_resource',
                timestamp=ts,
                path=csv_dir,
                action='export',
            ),
        )
        assert_csv_export_response(
            response,
            csv_dir,
            main_currency=A_EUR.resolve_to_asset_with_oracles(),
            is_download=False,
            expected_entries=1,
        )
        errors = rotkehlchen_api_server.rest_api.rotkehlchen.msg_aggregator.consume_errors()
        assert len(errors) == 1
        assert 'Failed to include balance for asset YABIRXROTKI.' in errors[0]


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_download_snapshot(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    ts = ts_now()
    with db.user_write() as cursor:
        _populate_db_with_balances(cursor, db, ts)
        _populate_db_with_location_data(cursor, db, ts)
        db.set_settings(cursor, ModifiableDBSettings(
            main_currency=A_EUR.resolve_to_asset_with_oracles()),
        )

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
            action='download',
        ),
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempzipfile = Path(tmpdirname, 'temp.zip')
        extractdir = Path(tmpdirname, 'extractdir')
        tempzipfile.write_bytes(response.content)
        with zipfile.ZipFile(tempzipfile, 'r') as zip_ref:
            zip_ref.extractall(extractdir)
        assert_csv_export_response(
            response=response,
            csv_dir=str(extractdir),
            main_currency=A_EUR.resolve_to_asset_with_oracles(),
            is_download=True,
        )


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_import_snapshot(
        rotkehlchen_api_server: 'APIServer',
        tmpdir_factory: pytest.TempdirFactory,
    ) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    ts = ts_now()
    with db.user_write() as cursor:
        _populate_db_with_balances(cursor, db, ts)
        _populate_db_with_location_data(cursor, db, ts)
        db.set_settings(cursor, ModifiableDBSettings(
            main_currency=A_EUR.resolve_to_asset_with_oracles()),
        )

    # check that importing a valid snapshot passes using PUT
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    _create_snapshot_with_valid_data(csv_dir, Timestamp(1651071105))
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir}/{LOCATION_DATA_IMPORT_FILENAME}',
        },
    )
    assert_simple_ok_response(response)

    # check that POST with the file works.
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir_2'))
    _create_snapshot_with_valid_data_for_post(csv_dir2, Timestamp(1651075))
    with open(f'{csv_dir2}/{BALANCES_FOR_IMPORT_FILENAME}', encoding='utf8') as balances_file, open(f'{csv_dir2}/{LOCATION_DATA_IMPORT_FILENAME}', encoding='utf8') as locations_file:  # noqa: E501
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'dbsnapshotsresource',
            ),
            files={
                'balances_snapshot_file': balances_file,
                'location_data_snapshot_file': locations_file,
            },
        )
        assert_simple_ok_response(response)

    # check that importing a snapshot that is present in the db fails.
    csv_dir3 = str(tmpdir_factory.mktemp('test_csv_dir3'))
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
            action='export',
            path=csv_dir3,
        ),
    )
    assert_csv_export_response(
        response=response,
        csv_dir=csv_dir3,
        main_currency=A_EUR.resolve_to_asset_with_oracles(),
        is_download=False,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir3}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir3}/{LOCATION_DATA_IMPORT_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='Adding timed_balance failed',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that importing snapshot with different timestamps fails.
    csv_dir4 = str(tmpdir_factory.mktemp('test_csv_dir4'))
    _create_snapshot_different_timestamps(csv_dir4, ts)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir4}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir4}/{LOCATION_DATA_IMPORT_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='csv file has different timestamps',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that importing snapshot with invalid header fails.
    csv_dir5 = str(tmpdir_factory.mktemp('test_csv_dir5'))
    _create_snapshot_with_invalid_headers(csv_dir5, ts)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir5}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir5}/{LOCATION_DATA_IMPORT_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='csv file has invalid headers',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that importing snapshot with unknown asset_identifier fails.
    csv_dir6 = str(tmpdir_factory.mktemp('test_csv_dir6'))
    _create_snapshot_with_unknown_asset(csv_dir6, ts)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir6}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir6}/{LOCATION_DATA_IMPORT_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='snapshot contains an unknown asset',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_delete_snapshot(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    ts = ts_now()
    with db.user_write() as write_cursor:
        _populate_db_with_balances(write_cursor, db, ts)
        _populate_db_with_location_data(write_cursor, db, ts)
        db.set_settings(write_cursor, ModifiableDBSettings(
            main_currency=A_EUR.resolve_to_asset_with_oracles()),
        )

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={'timestamp': ts},
    )
    assert_simple_ok_response(response)
    cursor = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn.cursor()
    assert len(cursor.execute('SELECT timestamp FROM timed_balances WHERE timestamp=?', (ts,)).fetchall()) == 0  # noqa: E501
    assert len(cursor.execute('SELECT timestamp FROM timed_location_data WHERE timestamp=?', (ts,)).fetchall()) == 0  # noqa: E501

    # check that an error is thrown for invalid timestamp
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
        ),
        json={'timestamp': 1000000},
    )
    assert_error_response(
        response,
        contained_in_msg='No snapshot found for the specified timestamp',
        status_code=HTTPStatus.CONFLICT,
    )


def test_get_snapshot_json(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    ts = ts_now()
    with db.user_write() as cursor:
        _populate_db_with_balances(cursor, db, ts)
        _populate_db_with_location_data(cursor, db, ts)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['balances_snapshot']) == 2
    assert len(result['location_data_snapshot']) == 3

    # check that requesting for a snapshot with invalid timestamp fails.
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts + 1,
        ),
    )
    assert_error_response(
        response,
        'No snapshot data found for the given timestamp',
        status_code=HTTPStatus.NOT_FOUND,
    )


def test_edit_snapshot(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    ts = ts_now()
    with db.user_write() as cursor:
        _populate_db_with_balances(cursor, db, ts)
        _populate_db_with_location_data(cursor, db, ts)

    snapshot_payload = {
        'balances_snapshot': [
            {
                'timestamp': ts,
                'category': 'asset',
                'asset_identifier': 'AVAX',
                'amount': '1000.00',
                'usd_value': '12929.00',
            },
            {
                'timestamp': ts,
                'category': 'asset',
                'asset_identifier': NFT_TOKEN_ID,
                'amount': '1000.00',
                'usd_value': '12929.00',
            },
        ],
        'location_data_snapshot': [
            {'timestamp': ts, 'location': 'external', 'usd_value': '12929.00'},
            {'timestamp': ts, 'location': 'total', 'usd_value': '12929.00'},
        ],
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
        ),
        json=snapshot_payload,
    )
    assert_proper_response(response)

    # compare the updated snapshot with snapshot in db
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['balances_snapshot']) == 2
    assert len(result['location_data_snapshot']) == 2
    assert result == snapshot_payload

    # test that editing a snapshot rollbacks previous snapshot if failure.
    invalid_snapshot_payload = {
        'balances_snapshot': [
            {
                'timestamp': ts,
                'category': 'asset',
                'asset_identifier': 'MEME',
                'amount': '1000.00',
                'usd_value': '100.00',
            },
            {
                'timestamp': ts,
                'category': 'asset',
                'asset_identifier': 'MEME',
                'amount': '1000.00',
                'usd_value': '100.00',
            },
        ],
        'location_data_snapshot': [
            {'timestamp': ts, 'location': 'external', 'usd_value': '200.00'},
            {'timestamp': ts, 'location': 'total', 'usd_value': '200.00'},
        ],
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
        ),
        json=invalid_snapshot_payload,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Adding timed_balance failed',
        status_code=HTTPStatus.CONFLICT,
    )
    # check that the previous snapshot remains unchanged
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['balances_snapshot']) == 2
    assert len(result['location_data_snapshot']) == 2
    assert result == snapshot_payload
