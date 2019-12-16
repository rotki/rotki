import os
from http import HTTPStatus

import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.dataimport import assert_cointracking_import_results


def test_data_import_cointracking(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for cointracking"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    filepath = os.path.join(dir_path, 'data', 'cointracking_trades_list.csv')

    json_data = {'source': 'cointracking.info', 'filepath': filepath}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] is True
    # And also assert data was imported succesfully
    assert_cointracking_import_results(rotki)


def test_data_import_errors(rotkehlchen_api_server, tmpdir_factory):
    """Test that errors in the data import endpoint are handled correctly"""
    dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    filepath = os.path.join(dir_path, 'data', 'cointracking_trades_list.csv')

    # Test that if filepath is missing, an error is returned
    json_data = {'source': 'cointracking.info'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg="filepath': ['Missing data for required field",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is missing, an error is returned
    json_data = {'filepath': filepath}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg="source': ['Missing data for required field",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is an invalid type an error is returned
    json_data = {'source': 55, 'filepath': filepath}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg="source': ['Not a valid string.'",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is invalid an error is returned
    json_data = {'source': 'somewhere', 'filepath': filepath}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg="source': ['Must be one of: cointracking.info",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is invalid type an error is returned
    json_data = {'source': 'cointracking.info', 'filepath': 22}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Provided non string type for filepath",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is not a valid path an error is returned
    json_data = {'source': 'cointracking.info', 'filepath': '/not/a/valid/path'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Given path /not/a/valid/path does not exist",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is a directory an error is returned
    test_dir = str(tmpdir_factory.mktemp('test_dir'))
    json_data = {'source': 'cointracking.info', 'filepath': test_dir}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a file',
        status_code=HTTPStatus.BAD_REQUEST,
    )
