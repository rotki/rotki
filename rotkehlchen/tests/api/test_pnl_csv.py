import csv
import os
import tempfile
import zipfile
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path

import pytest
import requests

from rotkehlchen.accounting.export.csv import FILENAME_ALL_CSV
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.constants import ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test, prices
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import create_timestamp


def assert_csv_export_response(response, csv_dir, is_download=False):
    if is_download:
        assert response.status_code == HTTPStatus.OK
    else:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert data['result'] is True

    # and check the csv files were generated succesfully. Here we are only checking
    # for valid CSV and not for the values to be valid. Valid values are tested
    # in unit/test_accounting.py
    with open(os.path.join(csv_dir, FILENAME_ALL_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 12
            assert row['location'] in (
                'kraken',
                'bittrex',
                'binance',
                'poloniex',
                'blockchain',
                'bitmex',
            )
            assert row['type'] in (
                str(AccountingEventType.TRADE),
                str(AccountingEventType.FEE),
                str(AccountingEventType.ASSET_MOVEMENT),
                str(AccountingEventType.PREFORK_ACQUISITION),
                str(AccountingEventType.TRANSACTION_EVENT),
                str(AccountingEventType.MARGIN_POSITION),
            )
            assert create_timestamp(row['timestamp'], '%d/%m/%Y %H:%M:%S %Z') > 0
            assert row['notes'] is not None
            assert row['asset'] is not None
            assert row['taxable_amount'] is not None
            assert row['free_amount'] is not None
            assert row['price'] is not None
            assert row['pnl_taxable'] is not None
            assert row['cost_basis_taxable'] is not None
            assert row['pnl_free'] is not None
            assert row['cost_basis_free'] is not None
            count += 1
    assert count == 43


@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITTREX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [
    {'pnl_csv_with_formulas': False},
])
def test_history_export_download_csv(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that the csv export/download REST API endpoint works correctly"""
    # Query history api to have report data to export
    query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1601040361,
        prepare_mocks=True,
    )
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))

    # now query the export endpoint with json body
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource'),
        json={'directory_path': csv_dir},
    )
    assert_csv_export_response(response, csv_dir)
    # now query the export endpoint with query params
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource') +
        f'?directory_path={csv_dir2}',
    )
    assert_csv_export_response(response, csv_dir2)
    # query it again and make sure that csv is recreated and events are not duplicated
    query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1601040361,
        prepare_mocks=True,
    )
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource') +
        f'?directory_path={csv_dir2}',
    )
    assert_csv_export_response(response, csv_dir2)
    # now query the download CSV endpoint
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historydownloadingresource'))
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempzipfile = Path(tmpdirname, 'temp.zip')
        extractdir = Path(tmpdirname, 'extractdir')
        tempzipfile.write_bytes(response.content)
        with zipfile.ZipFile(tempzipfile, 'r') as zip_ref:
            zip_ref.extractall(extractdir)
        assert_csv_export_response(response, extractdir, is_download=True)
    # query it again and make sure that csv is recreated and events are not duplicated
    query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1601040361,
        prepare_mocks=True,
    )
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historydownloadingresource'))
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempzipfile = Path(tmpdirname, 'temp.zip')
        extractdir = Path(tmpdirname, 'extractdir')
        tempzipfile.write_bytes(response.content)
        with zipfile.ZipFile(tempzipfile, 'r') as zip_ref:
            zip_ref.extractall(extractdir)
        assert_csv_export_response(response, extractdir, is_download=True)


@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITTREX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_history_export_csv_errors(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that errors on the csv export REST API endpoint are handled correctly"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
    )
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))

    # Query the export endpoint without first having queried the history
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource'),
        json={'directory_path': csv_dir},
    )
    assert_error_response(
        response=response,
        contained_in_msg='No history processed in order to perform an export',
        status_code=HTTPStatus.CONFLICT,
    )

    # Now, query history processing to have data for exporting
    with ExitStack() as stack:
        for manager in setup:
            if manager is None:
                continue
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, 'historyprocessingresource'),
        )
    assert_proper_response(response)

    # And now provide non-existing path for directory
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource'),
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
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource'),
        json={'directory_path': str(temporary_file)},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a directory',
        status_code=HTTPStatus.BAD_REQUEST,
    )
