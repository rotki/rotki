import csv
import os
import tempfile
import zipfile
from http import HTTPStatus
from pathlib import Path

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_EUR, A_USD
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.snapshots import (
    BALANCES_FILENAME,
    BALANCES_FOR_IMPORT_FILENAME,
    LOCATION_DATA_FILENAME,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_simple_ok_response,
)
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date, ts_now


def _populate_db_with_balances(connection, ts: Timestamp):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO "timed_balances" ("category", "time", "currency", "amount", "usd_value") VALUES
        (?, ?, ?, ?, ?);
        """, ('A', ts, 'ADA', '1.00', '178.44'),
    )
    cursor.execute(
        """
        INSERT INTO "timed_balances" ("category", "time", "currency", "amount", "usd_value") VALUES
        (?, ?, ?, ?, ?);
        """, ('A', ts, 'AVAX', '1.00', '87'),
    )
    connection.commit()


def _populate_db_with_location_data(connection, ts: Timestamp):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO "timed_location_data" ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (ts, 'A', '100.00'),
    )
    cursor.execute(
        """
        INSERT INTO "timed_location_data" ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (ts, 'B', '200.00'),
    )
    cursor.execute(
        """
        INSERT INTO "timed_location_data" ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (ts, 'H', '50.00'),
    )
    connection.commit()


def _create_snapshot_with_valid_data(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = ['timestamp', 'category', 'asset_identifier', 'amount', 'eur_value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                'timestamp': timestamp,
                'category': 'asset',
                'asset_identifier': 'AVAX',
                'amount': '10.555',
                'eur_value': '100.555',
            },
        )
        writer.writerow(
            {
                'timestamp': timestamp,
                'category': 'asset',
                'asset_identifier': 'BTC',
                'amount': '1',
                'eur_value': '40000.000',
            },
        )

    path = Path(directory) / LOCATION_DATA_FILENAME
    with open(path, 'w') as f:
        fieldnames = ['timestamp', 'location', 'eur_value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                'timestamp': timestamp_to_date(timestamp, '%Y-%m-%d %H:%M:%S'),
                'location': 'blockchain',
                'eur_value': '100.555',
            },
        )
        writer.writerow(
            {
                'timestamp': timestamp_to_date(timestamp, '%Y-%m-%d %H:%M:%S'),
                'location': 'total',
                'eur_value': '41000.555',
            },
        )


def _create_snapshot_different_timestamps(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = ['timestamp', 'category', 'asset_identifier', 'amount', 'eur_value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                'timestamp': timestamp,
                'category': 'asset',
                'asset_identifier': 'AVAX',
                'amount': '10.555',
                'eur_value': '100.555',
            },
        )
        writer.writerow(
            {
                'timestamp': timestamp + 500,
                'category': 'asset',
                'asset_identifier': 'BTC',
                'amount': '1',
                'eur_value': '40000.000',
            },
        )

    path = Path(directory) / LOCATION_DATA_FILENAME
    with open(path, 'w') as f:
        fieldnames = ['timestamp', 'location', 'eur_value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                'timestamp': timestamp_to_date(Timestamp(timestamp + 1000), '%Y-%m-%d %H:%M:%S'),
                'location': 'blockchain',
                'eur_value': '100.555',
            },
        )
        writer.writerow(
            {
                'timestamp': timestamp_to_date(timestamp, '%Y-%m-%d %H:%M:%S'),
                'location': 'total',
                'eur_value': '41000.555',
            },
        )


def _create_snapshot_with_invalid_headers(directory: str, timestamp: Timestamp) -> None:
    path = Path(directory) / BALANCES_FOR_IMPORT_FILENAME
    with open(path, 'w') as f:
        fieldnames = ['timestamp', 'category', 'asset', 'amount', 'value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
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

    path = Path(directory) / LOCATION_DATA_FILENAME
    with open(path, 'w') as f:
        fieldnames = ['timestamp', 'location', 'value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                'timestamp': timestamp_to_date(timestamp, '%Y-%m-%d %H:%M:%S'),
                'location': 'blockchain',
                'value': '100.555',
            },
        )
        writer.writerow(
            {
                'timestamp': timestamp_to_date(timestamp, '%Y-%m-%d %H:%M:%S'),
                'location': 'total',
                'value': '41000.555',
            },
        )


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
            assert row[f'{main_currency.symbol.lower()}_value'] is not None
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
        json={
            'timestamp': ts,
        },
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

    # check that importing a valid snapshot passes
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    _create_snapshot_with_valid_data(csv_dir, Timestamp(1651071105))
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir}/{LOCATION_DATA_FILENAME}',
        },
    )
    assert_simple_ok_response(response)

    # check that importing a snapshot that is present in the db fails.
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))
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
    assert_csv_export_response(response, csv_dir2, main_currency=A_EUR, is_download=False)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir2}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir2}/{LOCATION_DATA_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='Adding timed_balance failed',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that importing snapshot with different timestamps fails.
    csv_dir3 = str(tmpdir_factory.mktemp('test_csv_dir3'))
    _create_snapshot_different_timestamps(csv_dir3, ts)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir3}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir3}/{LOCATION_DATA_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='csv file has different timestamps',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that importing snapshot with invalid header fails.
    csv_dir4 = str(tmpdir_factory.mktemp('test_csv_dir4'))
    _create_snapshot_with_invalid_headers(csv_dir4, ts)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotimportingresource',
        ),
        json={
            'balances_snapshot_file': f'{csv_dir4}/{BALANCES_FOR_IMPORT_FILENAME}',
            'location_data_snapshot_file': f'{csv_dir4}/{LOCATION_DATA_FILENAME}',
        },
    )
    assert_error_response(
        response,
        contained_in_msg='csv file has invalid headers',
        status_code=HTTPStatus.CONFLICT,
    )
