from http import HTTPStatus
from unittest.mock import patch

import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_simple_ok_response,
)

API_KEYPAIR_VALIDATION_PATCH = patch(
    'rotkehlchen.exchanges.kraken.Kraken.validate_api_key',
    return_value=(True, ''),
)


def test_setup_exchange(rotkehlchen_api_server):
    """Test that setting up an exchange via the api works"""
    # Check that no exchanges are registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []

    # First test that if api key validation fails we get an error
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    response = requests.put(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Provided API Key or secret is in invalid Format',
        status_code=HTTPStatus.CONFLICT,
    )

    # Mock the api pair validation and make sure that the exchange is setup
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == ['kraken']

    # Check that we get an error if we try to re-setup an already setup exchange
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Exchange kraken is already registered',
        status_code=HTTPStatus.CONFLICT,
    )


def test_setup_exchange_errors(rotkehlchen_api_server):
    """Test errors and edge cases of setup_exchange endpoint"""

    # Provide unsupported exchange name
    data = {'name': 'superexchange', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Exchange superexchange is not supported',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type exchange name
    data = {'name': 3434, 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Exchange name should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit exchange name
    data = {'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for api key
    data = {'name': 'kraken', 'api_key': True, 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api key
    data = {'name': 'kraken', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for api secret
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 234.1}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api secret
    data = {'name': 'kraken', 'api_key': 'ddddd'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_remove_exchange(rotkehlchen_api_server):
    """Test that removing a setup exchange via the api works"""
    # Setup kraken exchange
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == ['kraken']

    # Now remove the registered kraken exchange
    data = {'name': 'kraken'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_simple_ok_response(response)
    # and check that it's not registered anymore
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []

    # now try to remove a non-registered exchange
    data = {'name': 'binance'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Exchange binance is not registered',
        status_code=HTTPStatus.CONFLICT,
    )


def test_remove_exchange_errors(rotkehlchen_api_server):
    """Errors and edge cases when using the remove exchange endpoint"""
    # remove unsupported exchange
    data = {'name': 'wowexchange'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Exchange wowexchange is not supported',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for exchange name
    data = {'name': 5533}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Exchange name should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # omit exchange name at removal
    data = {'name': 5533}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
