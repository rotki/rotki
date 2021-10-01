import os
import shutil
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import requests

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.dataimport import (
    assert_cointracking_import_results,
    assert_cryptocom_import_results,
    assert_cryptocom_special_events_import_results,
    assert_blockfi_transactions_import_results,
    assert_blockfi_trades_import_results,
    assert_nexo_results,
    assert_shapeshift_trades_import_results,
    assert_uphold_transactions_import_results,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.typing import ApiKey, ApiSecret, Location


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

    if file_upload:
        files = {'file': open(filepath, 'rb')}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ),
            files=files,
            data={'source': 'cointracking.info'},
        )
    else:
        json_data = {'source': 'cointracking.info', 'file': str(filepath)}
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ), json=json_data,
        )

    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
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
    # And also assert data was imported succesfully
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
    # And also assert data was imported succesfully
    assert_cryptocom_special_events_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_blockfi_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for blockfi transactions"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-transactions.csv'

    json_data = {'source': 'blockfi-transactions', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_blockfi_transactions_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_blockfi_trades(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for blockfi trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-trades.csv'

    json_data = {'source': 'blockfi-trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
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
    # And also assert data was imported succesfully
    assert_nexo_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_shapeshift_trades(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for shapeshift trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'shapeshift-trade-history.csv'

    json_data = {'source': 'shapeshift-trades', 'file': str(filepath)}
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

    json_data = {'source': 'uphold', 'file': str(filepath)}
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
        if file_upload:
            files = {'file': open(bad_filepath, 'rb')}
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ),
                files=files,
                data={'source': 'cointracking.info'},
            )
        else:
            json_data = {'source': 'cointracking.info', 'file': str(bad_filepath)}
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
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    # Test that if filepath is missing, an error is returned
    json_data = {'source': 'cointracking.info'}
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
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='source": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is invalid an error is returned
    json_data = {'source': 'somewhere', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='source": ["Must be one of: cointracking.info',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is invalid type an error is returned
    json_data = {'source': 'cointracking.info', 'file': 22}
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
    json_data = {'source': 'cointracking.info', 'file': '/not/a/valid/path'}
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
    json_data = {'source': 'cointracking.info', 'file': test_dir}
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


def test_known_locations(user_data_dir, rotkehlchen_api_server):
    """Test that locations imported in different places are correctly stored in database"""

    # Import from nexo
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'nexo.csv'

    json_data = {'source': 'nexo', 'file': str(filepath)}
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )

    # Add transactions from blockfi
    filepath = dir_path / 'data' / 'blockfi-transactions.csv'

    json_data = {'source': 'blockfi-transactions', 'file': str(filepath)}
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )

    # Add cryptocom
    filepath = dir_path / 'data' / 'cryptocom_trades_list.csv'
    json_data = {'source': 'cryptocom', 'file': str(filepath)}
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )

    # Add cointracking multiple exchanges
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'
    files = {'file': open(filepath, 'rb')}
    requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ),
        files=files,
        data={'source': 'cointracking.info'},
    )

    # Add multiple entries for same exchange + connected exchange
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir, '123', msg_aggregator, None)
    kraken_api_key1 = ApiKey('kraken_api_key')
    kraken_api_secret1 = ApiSecret(b'kraken_api_secret')
    kraken_api_key2 = ApiKey('kraken_api_key2')
    kraken_api_secret2 = ApiSecret(b'kraken_api_secret2')
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')

    # add mock kraken and binance
    db.add_exchange('kraken1', Location.KRAKEN, kraken_api_key1, kraken_api_secret1)
    db.add_exchange('kraken2', Location.KRAKEN, kraken_api_key2, kraken_api_secret2)
    db.add_exchange('binance', Location.BINANCE, binance_api_key, binance_api_secret)

    expected_locations = {
        Location.KRAKEN,
        Location.BINANCE,
        Location.BLOCKFI,
        Location.NEXO,
        Location.CRYPTOCOM,
        Location.POLONIEX,
        Location.COINBASE,
    }

    assert set(db.get_connected_locations()) == expected_locations
