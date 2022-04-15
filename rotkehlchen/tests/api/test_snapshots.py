import csv
import os
import tempfile
import zipfile
from http import HTTPStatus
from pathlib import Path

import requests

from rotkehlchen.db.snapshots import BALANCES_FILENAME, LOCATION_DATA_FILENAME
from rotkehlchen.tests.utils.api import api_url_for, assert_simple_ok_response
from rotkehlchen.types import Location


def _populate_db_with_balances(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO "timed_balances" ("category", "time", "currency", "amount", "usd_value") VALUES
        (?, ?, ?, ?, ?);
        """, ('A', 1, 'ADA', '1.00', '178.44'),
    )
    cursor.execute(
        """
        INSERT INTO "timed_balances" ("category", "time", "currency", "amount", "usd_value") VALUES
        (?, ?, ?, ?, ?);
        """, ('A', 1, 'AVAX', '1.00', '87'),
    )
    connection.commit()


def _populate_db_with_location_data(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO "timed_location_data" ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (1, 'A', '100.00'),
    )
    cursor.execute(
        """
        INSERT INTO "timed_location_data" ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (1, 'B', '200.00'),
    )
    cursor.execute(
        """
        INSERT INTO "timed_location_data" ("time", "location", "usd_value") VALUES
        (?, ?, ?);
        """, (1, 'H', '50.00'),
    )
    connection.commit()


def assert_csv_export_response(response, csv_dir, is_download=False):
    if is_download:
        assert response.status_code == HTTPStatus.OK
    else:
        assert_simple_ok_response(response)

    with open(os.path.join(csv_dir, BALANCES_FILENAME), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 4
            assert row['category'] in (
                'asset',
                'liability',
            )
            assert row['amount'] is not None
            assert row['usd_value'] is not None
            count += 1
        assert count == 2

    with open(os.path.join(csv_dir, LOCATION_DATA_FILENAME), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 2
            assert Location.deserialize(row['location']) is not None
            assert row['usd_value'] is not None
            count += 1
        assert count == 3


def test_export_snapshot(rotkehlchen_api_server, tmpdir_factory):
    conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn

    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))
    _populate_db_with_balances(conn)
    _populate_db_with_location_data(conn)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotexportingresource',
        ),
        json={
            'timestamp': 1,
            'path': csv_dir,
        },
    )
    assert_csv_export_response(response, csv_dir, is_download=False)
    # test query params
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotexportingresource',
            timestamp=1,
            path=csv_dir2,
        ),
    )
    assert_csv_export_response(response, csv_dir2, is_download=False)


def test_download_snapshot(rotkehlchen_api_server):
    conn = rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn

    _populate_db_with_balances(conn)
    _populate_db_with_location_data(conn)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotdownloadingresource',
        ),
        json={
            'timestamp': 1,
        },
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempzipfile = Path(tmpdirname, 'temp.zip')
        extractdir = Path(tmpdirname, 'extractdir')
        tempzipfile.write_bytes(response.content)
        with zipfile.ZipFile(tempzipfile, 'r') as zip_ref:
            zip_ref.extractall(extractdir)
        assert_csv_export_response(response, extractdir, is_download=True)
