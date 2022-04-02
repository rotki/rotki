import csv
import os
import re
import tempfile
import zipfile
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict

import pytest
import requests

from rotkehlchen.accounting.export.csv import FILENAME_ALL_CSV
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.constants import ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test, prices
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import create_timestamp, ts_now


def _assert_column(keys, letter, expected_column_name, location):
    msg = f'{location} should be {expected_column_name}'
    assert keys[ord(letter) - ord('A')] == expected_column_name, msg


CSV_SELL_RE = re.compile(r'=IF\(([A-Z]).*=0;0;([A-Z]).*-([A-Z]).*\)')
CSV_PROFITLOSS_RE = re.compile(r'=IF\(P.*=0;-K.*;P.*\)')


def assert_csv_formulas_all_events(row: Dict[str, Any], db_settings: DBSettings):
    keys = list(row.keys())
    if db_settings.pnl_csv_with_formulas is False:
        return

    profit_currency = db_settings.main_currency
    net_profit_loss = row['pnl']
    if row['type'] == str(AccountingEventType.TRADE):
        match = CSV_SELL_RE.search(net_profit_loss)
        assert match
        groups = match.groups()
        assert len(groups) == 3
        _assert_column(
            keys=keys,
            letter=groups[0],
            expected_column_name='taxable_amount',
            location='conditional column name in all events sell pnl',
        )
        _assert_column(
            keys=keys,
            letter=groups[1],
            expected_column_name=f'taxable_received_in_{profit_currency.identifier}',
            location='taxable received in all events sell pnl',
        )
        _assert_column(
            keys=keys,
            letter=groups[2],
            expected_column_name=f'taxable_bought_cost_in_{profit_currency.identifier}',
            location='taxable bought cost in all events sell pnl',
        )
    elif row['type'] in (str(AccountingEventType.ASSET_MOVEMENT), str(AccountingEventType.LOAN)):
        _assert_column(
            keys=keys,
            letter=net_profit_loss[2],
            expected_column_name=f'paid_in_{profit_currency.identifier}',
            location='paid in profit currency in all events tx gas cost and more pnl',
        )
    elif row['type'] == EV_INTEREST_PAYMENT:
        _assert_column(
            keys=keys,
            letter=net_profit_loss[1],
            expected_column_name=f'taxable_received_in_{profit_currency.identifier}',
            location='gained in profit currenty in all events defi and more',
        )
    elif row['type'] in (EV_LEDGER_ACTION, EV_MARGIN_CLOSE, EV_DEFI):
        match = CSV_PROFITLOSS_RE.search(net_profit_loss)
        assert match, 'entry does not match the expected formula'
    elif row['type'] == EV_BUY:
        pass  # nothing to check for these types
    else:
        raise AssertionError(f'Unexpected CSV row type {row["type"]} encountered')


def assert_csv_export_response(response, db_settings, csv_dir, is_download=False):
    if is_download:
        assert response.status_code == HTTPStatus.OK
    else:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert data['result'] is True

    # and check the csv files were generated succesfully. Here we are only checking
    # for valid CSV and not for the values to be valid.
    # TODO: In the future make a test that checks the values are also valid
    with open(os.path.join(csv_dir, FILENAME_ALL_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert_csv_formulas_all_events(row, db_settings)
            assert len(row) == 10
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
                str(AccountingEventType.LOAN),
            )
            assert create_timestamp(row['timestamp'], '%d/%m/%Y %H:%M:%S') > 0
            assert row['notes'] is not None
            assert row['asset'] is not None
            assert row['taxable_amount'] is not None
            assert row['free_amount'] is not None
            assert row['price'] is not None
            assert row['pnl'] is not None
            assert row['cost_basis'] is not None
            count += 1
    assert count == 50


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
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    # Query history api to have report data to export
    query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=ts_now(),
        prepare_mocks=True,
    )
    db_settings = rotki.accountant.pots[0].settings
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))

    # now query the export endpoint with json body
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource'),
        json={'directory_path': csv_dir},
    )
    assert_csv_export_response(response, db_settings, csv_dir)
    # now query the export endpoint with query params
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historyexportingresource') +
        f'?directory_path={csv_dir2}',
    )
    assert_csv_export_response(response, db_settings, csv_dir2)
    # now query the download CSV endpoint
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'historydownloadingresource'))
    with tempfile.TemporaryDirectory() as tmpdirname:
        tempzipfile = Path(tmpdirname, 'temp.zip')
        extractdir = Path(tmpdirname, 'extractdir')
        tempzipfile.write_bytes(response.content)
        with zipfile.ZipFile(tempzipfile, 'r') as zip_ref:
            zip_ref.extractall(extractdir)
        assert_csv_export_response(response, db_settings, extractdir, is_download=True)


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
        api_url_for(rotkehlchen_api_server_with_exchanges, "historyexportingresource"),
        json={'directory_path': str(temporary_file)},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a directory',
        status_code=HTTPStatus.BAD_REQUEST,
    )
