import os
import shutil
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import requests

from rotkehlchen.db.filtering import AssetMovementsFilterQuery, TradesFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.dataimport import (
    assert_binance_import_results,
    assert_bisq_trades_import_results,
    assert_bitcoin_tax_trades_import_results,
    assert_bitmex_import_wallet_history,
    assert_bitstamp_trades_import_results,
    assert_bittrex_import_results,
    assert_blockfi_trades_import_results,
    assert_blockfi_transactions_import_results,
    assert_cointracking_import_results,
    assert_cryptocom_import_results,
    assert_cryptocom_special_events_import_results,
    assert_custom_cointracking,
    assert_nexo_results,
    assert_rotki_generic_events_import_results,
    assert_rotki_generic_trades_import_results,
    assert_shapeshift_trades_import_results,
    assert_uphold_transactions_import_results,
)

mocked_prices = {
    'BTC': {
        'USD': {
            1576738800: FVal('7159.26'),
            1576825200: FVal('7203.41'),
            1576911600: FVal('7159.47'),
            1576998000: FVal('7517.58'),
            1577084400: FVal('7326.6'),
            1577170800: FVal('7260.91'),
            1577257200: FVal('7202.72'),
        },
    },
}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_data_import_cointracking(rotkehlchen_api_server, file_upload):
    """Test that the data import endpoint works successfully for cointracking

    To test that data import works both with specifying filepath and uploading
    the file try both ways in this test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    with open(filepath, 'rb') as infile:
        if file_upload:
            files = {'file': infile}
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ),
                files=files,
                data={'source': 'cointracking'},
            )
        else:
            json_data = {'source': 'cointracking', 'file': str(filepath)}
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ), json=json_data,
            )

    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_cointracking_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_cryptocom(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for cryptocom"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cryptocom_trades_list.csv'

    json_data = {'source': 'cryptocom', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_cryptocom_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_cryptocom_special_types(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for cryptocom"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cryptocom_special_events.csv'

    json_data = {'source': 'cryptocom', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_cryptocom_special_events_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
def test_data_import_bitmex_wallet_history(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for BitMEX wallet history"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'bitmex_wallet_history.csv'

    json_data = {'source': 'bitmex_wallet_history', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_bitmex_import_wallet_history(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_blockfi_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for blockfi transactions"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-transactions.csv'

    json_data = {'source': 'blockfi_transactions', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_blockfi_transactions_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_blockfi_trades(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for blockfi trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-trades.csv'

    json_data = {'source': 'blockfi_trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_blockfi_trades_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_nexo(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for nexo"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'nexo.csv'

    json_data = {'source': 'nexo', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_nexo_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_shapeshift_trades(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for shapeshift trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'shapeshift-trade-history.csv'

    json_data = {'source': 'shapeshift_trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_shapeshift_trades_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_uphold_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for uphold trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'uphold-transaction-history.csv'

    json_data = {'source': 'uphold_transactions', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_uphold_transactions_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_bisq_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for bisq trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'bisq_trades.csv'

    json_data = {'source': 'bisq_trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_bisq_trades_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_data_import_wrong_extension(rotkehlchen_api_server, file_upload):
    """Test that uploading a file without the proper extension fails"""
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    # Let's also try to upload a file without the csv prefix
    with TemporaryDirectory() as temp_directory:
        bad_filepath = Path(temp_directory) / 'somefile.bad'
        shutil.copyfile(filepath, bad_filepath)
        with open(bad_filepath, 'rb') as infile:
            if file_upload:
                files = {'file': infile}
                response = requests.post(
                    api_url_for(
                        rotkehlchen_api_server,
                        'dataimportresource',
                    ),
                    files=files,
                    data={'source': 'cointracking'},
                )
            else:
                json_data = {'source': 'cointracking', 'file': str(bad_filepath)}
                response = requests.put(
                    api_url_for(
                        rotkehlchen_api_server,
                        'dataimportresource',
                    ), json=json_data,
                )

    assert_error_response(
        response=response,
        contained_in_msg='does not end in any of .csv',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_errors(rotkehlchen_api_server, tmpdir_factory):
    """Test that errors in the data import endpoint are handled correctly"""
    dir_path = Path(__file__).resolve().parent.parent
    corrupt_nexo_filepath = dir_path / 'data' / 'corrupt_nexo.csv'
    json_data = {'source': 'cointracking', 'file': str(corrupt_nexo_filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with database.conn.read_ctx() as cursor:
        _, trades_count = database.get_trades_and_limit_info(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
    _, asset_movements_count = database.get_asset_movements_and_limit_info(filter_query=AssetMovementsFilterQuery.make(), has_premium=True)  # noqa: E501
    assert trades_count == asset_movements_count == 0

    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    # Test that if filepath is missing, an error is returned
    json_data = {'source': 'cointracking'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='file": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is missing, an error is returned
    json_data = {'filepath': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='source": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is an invalid type an error is returned
    json_data = {'source': 55, 'filepath': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"source": ["Failed to deserialize DataImportSource value',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is invalid an error is returned
    json_data = {'source': 'somewhere', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"source": ["Failed to deserialize DataImportSource value',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is invalid type an error is returned
    json_data = {'source': 'cointracking', 'file': 22}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Provided non string or file type for file',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is not a valid path an error is returned
    json_data = {'source': 'cointracking', 'file': '/not/a/valid/path'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Given path /not/a/valid/path does not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is a directory an error is returned
    test_dir = str(tmpdir_factory.mktemp('test_dir'))
    json_data = {'source': 'cointracking', 'file': test_dir}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a file',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_data_import_custom_format(rotkehlchen_api_server, file_upload):
    """Test that the data import endpoint works successfully for cointracking
    when using custom date formats at the moment of making the import

    To test that data import works both with specifying filepath and uploading
    the file try both ways in this test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    filepath = dir_path / 'data' / 'cointracking_custom_dates.csv'

    with open(filepath, 'rb') as infile:
        if file_upload:
            files = {'file': infile}
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ),
                files=files,
                data={'source': 'cointracking', 'timestamp_format': '%d/%m/%Y %H:%M'},
            )
        else:
            json_data = {
                'source': 'cointracking',
                'file': str(filepath),
                'timestamp_format': '%d/%m/%Y %H:%M',
            }
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ), json=json_data,
            )

    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_custom_cointracking(rotki)


def test_data_import_binance_history(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for binance data"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'binance_history.csv'

    json_data = {'source': 'binance', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert_binance_import_results(rotki)


def test_data_import_rotki_generic_trades(rotkehlchen_api_server):
    """Test that data import works for rotki generic trades import csv file."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'rotki_generic_trades.csv'

    json_data = {'source': 'rotki_trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_rotki_generic_trades_import_results(rotki)

    # check that passing `timestamp_format` does not break anything
    json_data = {
        'source': 'rotki_trades',
        'file': str(filepath),
        'timestamp_format': '%Y-%m-%d %H:%M:%S',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_rotki_generic_trades_import_results(rotki)


def test_data_import_rotki_generic_events(rotkehlchen_api_server):
    """Test that data import works for rotki generic events import csv file."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'rotki_generic_events.csv'

    json_data = {'source': 'rotki_events', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_rotki_generic_events_import_results(rotki)


def test_docker_async_import(rotkehlchen_api_server):
    """Test that docker async csv import using POST on /import is initialized properly
        The test doesn't wait for import completion, it only tests successful import initialization
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'binance_history.csv'
    with open(filepath, 'rb') as infile:
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ), data={
                'async_query': True,
                'source': 'binance',
            }, files={
                'file': infile,
            },
        )
        result = assert_proper_response_with_result(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, result['task_id'])
    assert outcome['message'] == ''
    assert outcome['result'] is True
    assert_binance_import_results(rotki)


def test_bitcoin_tax_import(rotkehlchen_api_server):
    """Test that data import works for Bitcoin_Tax csv files of types trades and spending."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent

    # First test a trades type csv import
    filepath = dir_path / 'data' / 'bitcoin_tax_trades.csv'
    json_data = {'source': 'bitcoin_tax', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_bitcoin_tax_trades_import_results(rotki, filepath.name)

    # Reimport the same csv file to test that no new events are created
    filepath = dir_path / 'data' / 'bitcoin_tax_trades.csv'
    json_data = {'source': 'bitcoin_tax', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_bitcoin_tax_trades_import_results(rotki, filepath.name)

    # After the trades have been successfully imported, test a spending/income type csv import
    filepath = dir_path / 'data' / 'bitcoin_tax_spending.csv'
    json_data = {'source': 'bitcoin_tax', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_bitcoin_tax_trades_import_results(rotki, filepath.name)


def test_bitstamp_import(rotkehlchen_api_server):
    """Test that data import works for Bitstamp transaction csv files"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent

    # First test a trades type csv import
    filepath = dir_path / 'data' / 'bitstamp.csv'
    json_data = {'source': 'bitstamp', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert assert_proper_response_with_result(response) is True
    assert_bitstamp_trades_import_results(rotki)


def test_bittrex_history_import(rotkehlchen_api_server):
    """Test that data import works both for bittrex csv files"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    for filename, time_format in (
        ('bittrex_tx_history.csv', None),
        ('bittrex_tx_history_deposits.csv', '%m/%d/%Y %I:%M:%S %p'),
        ('bittrex_tx_history_deposits_old.csv', '%Y-%m-%d %H:%M:%S'),
        ('bittrex_tx_history_withdrawals.csv', '%m/%d/%Y %I:%M:%S %p'),
        ('bittrex_tx_history_withdrawals_old.csv', '%Y-%m-%d %H:%M:%S'),
        ('bittrex_order_history.csv', None),
        ('bittrex_order_history_old.csv', '%m/%d/%Y %I:%M:%S %p'),
        ('bittrex_order_history_older.csv', '%m/%d/%Y %I:%M:%S %p'),
    ):
        filepath = dir_path / 'data' / filename
        json_data = {'source': 'bittrex', 'file': str(filepath), 'timestamp_format': time_format}
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ), json=json_data,
        )
        assert assert_proper_response_with_result(response) is True

    assert_bittrex_import_results(rotki)
