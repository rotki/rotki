import csv
import os
import tempfile
import zipfile
from http import HTTPStatus
from pathlib import Path
from typing import Optional

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_EUR, A_USD
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.snapshots import (
    BALANCES_FILENAME,
    BALANCES_FOR_IMPORT_FILENAME,
    LOCATION_DATA_FILENAME,
    LOCATION_DATA_IMPORT_FILENAME,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_simple_ok_response,
)
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

BALANCES_IMPORT_HEADERS = ['timestamp', 'category', 'asset_identifier', 'amount', 'usd_value']
BALANCES_IMPORT_INVALID_HEADERS = ['timestamp', 'category', 'asset', 'amount', 'value']
LOCATION_DATA_IMPORT_HEADERS = ['timestamp', 'location', 'usd_value']
LOCATION_DATA_IMPORT_INVALID_HEADERS = ['timestamp', 'location', 'value']

NFT_TOKEN_ID = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_11'


def _populate_db_with_balances(connection, ts: Timestamp):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO timed_balances ("category", "time", "currency", "amount", "usd_value") VALUES
        (?, ?, ?, ?, ?);
        """, ('A', ts, 'BTC', '1.00', '178.44'),
    )
    cursor.execute(
        """
        INSERT INTO timed_balances ("category", "time", "currency", "amount", "usd_value") VALUES
        (?, ?, ?, ?, ?);
        """, ('A', ts, 'AVAX', '1.00', '87'),
    )
    connection.commit()


def _populate_db_with_location_data(connection, ts: Timestamp):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO timed_location_data ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (ts, 'A', '100.00'),
    )
    cursor.execute(
        """
        INSERT INTO timed_location_data ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (ts, 'B', '200.00'),
    )
    cursor.execute(
        """
        INSERT INTO timed_location_data ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (ts, 'H', '50.00'),
    )
    connection.commit()


def _write_balances_csv_row(
    writer: 'csv.DictWriter',
    timestamp: Timestamp,
    include_unknown_asset: Optional[bool] = None,
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
    with open(path, 'w') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)


def _create_snapshot_with_unknown_asset(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp, include_unknown_asset=True)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)


def _create_snapshot_with_valid_data_for_post(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)


def _create_snapshot_different_timestamps(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = BALANCES_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row(writer, timestamp)
        _write_balances_csv_row(writer, Timestamp(timestamp + 500))

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = LOCATION_DATA_IMPORT_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row(writer, timestamp)
        _write_location_data_csv_row(writer, Timestamp(timestamp + 1000))


def _create_snapshot_with_invalid_headers(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = BALANCES_IMPORT_INVALID_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_balances_csv_row_with_invalid_headers(writer, timestamp)

    path = Path(directory) / LOCATION_DATA_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = LOCATION_DATA_IMPORT_INVALID_HEADERS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        _write_location_data_csv_row_with_invalid_headers(writer, timestamp)


def assert_csv_export_response(response, csv_dir, main_currency: Asset, is_download=False):
    if is_download:
        assert response.status_code == HTTPStatus.OK
    else:
        assert_simple_ok_response(response)

    with open(os.path.join(csv_dir, BALANCES_FILENAME), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 5
            assert row['category'] in (
                'asset',
                'liability',
            )
            assert row['amount'] is not None
            assert row['asset'] is not None
            assert row['timestamp'] is not None
            assert row[f'{main_currency.symbol.lower()}_value'] is not None
            count += 1
        assert count == 2

    with open(os.path.join(csv_dir, BALANCES_FOR_IMPORT_FILENAME), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 5
            assert row['category'] in (
                'asset',
                'liability',
            )
            assert row['amount'] is not None
            assert row['asset_identifier'] is not None
            assert row['timestamp'] is not None
            assert row['usd_value'] is not None
            count += 1
        assert count == 2

    with open(os.path.join(csv_dir, LOCATION_DATA_FILENAME), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 3
            assert row['timestamp'] is not None
            assert Location.deserialize(row['location']) is not None
            assert row[f'{main_currency.symbol.lower()}_value'] is not None
            count += 1
        assert count == 3

    with open(os.path.join(csv_dir, LOCATION_DATA_IMPORT_FILENAME), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 3
            assert row['timestamp'] is not None
            assert Location.deserialize(row['location']) is not None
            assert row['usd_value'] is not None
            count += 1
        assert count == 3


def test_export_snapshot(rotkehlchen_api_server, tmpdir_factory):
    conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn
    ts = Timestamp(ts_now())
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))
    _populate_db_with_balances(conn, ts)
    _populate_db_with_location_data(conn, ts)

    rotkehlchen_api_server.rest_api.rotkehlchen.data.db.set_settings(ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotexportingresource',
        ),
        json={
            'timestamp': ts,
            'path': csv_dir,
        },
    )
    assert_csv_export_response(response, csv_dir, main_currency=A_EUR, is_download=False)

    rotkehlchen_api_server.rest_api.rotkehlchen.data.db.set_settings(ModifiableDBSettings(main_currency=A_ETH))  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotexportingresource',
        ),
        json={
            'timestamp': ts,
            'path': csv_dir2,
        },
    )
    assert_csv_export_response(response, csv_dir2, main_currency=A_ETH, is_download=False)

    rotkehlchen_api_server.rest_api.rotkehlchen.data.db.set_settings(ModifiableDBSettings(main_currency=A_USD))  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotexportingresource',
        ),
        json={
            'timestamp': ts,
            'path': csv_dir2,
        },
    )
    assert_csv_export_response(response, csv_dir2, main_currency=A_USD, is_download=False)


def test_download_snapshot(rotkehlchen_api_server):
    conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn
    ts = Timestamp(ts_now())
    _populate_db_with_balances(conn, ts)
    _populate_db_with_location_data(conn, ts)

    rotkehlchen_api_server.rest_api.rotkehlchen.data.db.set_settings(ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotdownloadingresource',
        ),
        json={'timestamp': ts},
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempzipfile = Path(tmpdirname, 'temp.zip')
        extractdir = Path(tmpdirname, 'extractdir')
        tempzipfile.write_bytes(response.content)
        with zipfile.ZipFile(tempzipfile, 'r') as zip_ref:
            zip_ref.extractall(extractdir)
        assert_csv_export_response(response, extractdir, main_currency=A_EUR, is_download=True)


def test_import_snapshot(rotkehlchen_api_server, tmpdir_factory):
    conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn
    ts = Timestamp(ts_now())
    _populate_db_with_balances(conn, ts)
    _populate_db_with_location_data(conn, ts)
    rotkehlchen_api_server.rest_api.rotkehlchen.data.db.set_settings(ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501

    # check that importing a valid snapshot passes using PUT
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    _create_snapshot_with_valid_data(csv_dir, Timestamp(1651071105))
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
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
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
        ),
        files={
            'balances_snapshot_file': open(f'{csv_dir2}/{BALANCES_FOR_IMPORT_FILENAME}'),
            'location_data_snapshot_file': open(f'{csv_dir2}/{LOCATION_DATA_IMPORT_FILENAME}'),
        },
    )
    assert_simple_ok_response(response)

    # check that importing a snapshot that is present in the db fails.
    csv_dir3 = str(tmpdir_factory.mktemp('test_csv_dir3'))
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotexportingresource',
        ),
        json={
            'timestamp': ts,
            'path': csv_dir3,
        },
    )
    assert_csv_export_response(response, csv_dir3, main_currency=A_EUR, is_download=False)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
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
            'dbsnapshotimportingresource',
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
            'dbsnapshotimportingresource',
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
            'dbsnapshotimportingresource',
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


def test_delete_snapshot(rotkehlchen_api_server):
    conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn
    ts = Timestamp(ts_now())
    _populate_db_with_balances(conn, ts)
    _populate_db_with_location_data(conn, ts)
    rotkehlchen_api_server.rest_api.rotkehlchen.data.db.set_settings(ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotdeletingresource',
        ),
        json={'timestamp': ts},
    )
    assert_simple_ok_response(response)
    cursor = conn.cursor()
    assert len(cursor.execute('SELECT time FROM timed_balances WHERE time=?', (ts,)).fetchall()) == 0  # noqa: 501
    assert len(cursor.execute('SELECT time FROM timed_location_data WHERE time=?', (ts,)).fetchall()) == 0  # noqa: 501

    # check that an error is thrown for invalid timestamp
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotdeletingresource',
        ),
        json={'timestamp': 1000000},
    )
    assert_error_response(
        response,
        contained_in_msg='No snapshot found for the specified timestamp',
        status_code=HTTPStatus.CONFLICT,
    )
