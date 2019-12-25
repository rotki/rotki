from http import HTTPStatus

import pytest
import requests

from rotkehlchen.constants.assets import FIAT_CURRENCIES
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_qerying_fiat_exchange_rates(rotkehlchen_api_server):
    """Make sure that querying fiat exchange rates works also without logging in"""
    # Test with empty list of currencies
    data = {'currencies': []}
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource'), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Empy list of currencies provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    def assert_okay(response):
        """Helper function for DRY checking below assertions"""
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        result = json_data['result']
        assert len(result) == 3
        assert FVal(result['EUR']) > 0
        assert FVal(result['USD']) > 0
        assert FVal(result['KRW']) > 0

    # Test with some currencies, both JSON body and query parameters
    data = {'currencies': ['EUR', 'USD', 'KRW']}
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource'), json=data,
    )
    assert_okay(response)
    # The query parameters test serves as a test that a list of parametrs works with query args too
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource') + '?currencies=' +
        ','.join(data['currencies']),
    )
    assert_okay(response)

    # Test with all currencies (give no input)
    response = requests.get(api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource'))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert len(result) == len(FIAT_CURRENCIES)
    for currency in FIAT_CURRENCIES:
        assert FVal(result[currency.identifier]) > 0


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_qerying_fiat_exchange_rates_errors(rotkehlchen_api_server):
    """Make sure that querying fiat exchange rates with wrong input is handled"""

    # Test with invalid type for currency
    data = {'currencies': [4234324.21]}
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource'), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test with invalid asset
    data = {'currencies': ['DDSAS']}
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource'), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset DDSAS provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test with non FIAT asset
    data = {'currencies': ['ETH']}
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'fiatexchangeratesresource'), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Asset ETH is not a FIAT asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )
