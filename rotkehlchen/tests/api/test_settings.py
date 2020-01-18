from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants.assets import A_JPY
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION, DBSettings
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.mock import MockWeb3


def test_qerying_settings(rotkehlchen_api_server, username):
    """Make sure that querying settings works for logged in user"""
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()

    result = json_data['result']
    assert json_data['message'] == ''
    assert result['version'] == ROTKEHLCHEN_DB_VERSION
    for setting in DBSettings._fields:
        assert setting in result

    # Logout of the active user
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, "usersbynameresource", name=username),
        json=data,
    )
    assert_simple_ok_response(response)

    # and now with no logged in user it should fail
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_error_response(
        response=response,
        contained_in_msg='No user is currently logged in',
        status_code=HTTPStatus.CONFLICT,
    )


def test_set_settings(rotkehlchen_api_server):
    """Happy case settings modification test"""
    # Get the starting settings
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    original_settings = json_data['result']
    assert json_data['message'] == ''
    # Create new settings which modify all of the original ones
    new_settings = {}
    unmodifiable_settings = (
        'version',
        'last_write_ts',
        'last_data_upload_ts',
        'last_balance_save',
    )
    for setting, value in original_settings.items():
        if setting in unmodifiable_settings:
            continue
        elif setting == 'historical_data_start':
            value = '10/10/2016'
        elif setting == 'date_display_format':
            value = '%d/%m/%Y-%H:%M:%S'
        elif setting == 'eth_rpc_endpoint':
            value = 'http://working.nodes.com:8545'
        elif setting == 'main_currency':
            value = 'JPY'
        elif type(value) == bool:
            value = not value
        elif type(value) == int:
            value += 1
        else:
            raise AssertionError(f'Unexpected settting {setting} encountered')

        new_settings[setting] = value

    # modify the settings
    block_query = patch('rotkehlchen.ethchain.Ethchain.query_eth_highest_block', return_value=0)
    mock_web3 = patch('rotkehlchen.ethchain.Web3', MockWeb3)
    with block_query, mock_web3:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "settingsresource"),
            json=new_settings,
        )
    # Check that new settings are returned in the response
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert result['version'] == ROTKEHLCHEN_DB_VERSION
    for setting, value in new_settings.items():
        msg = f'Error for {setting} setting. Expected: {value}. Got: {result[setting]}'
        assert result[setting] == value, msg

    # now check that the same settings are returned in a settings query
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    for setting, value in new_settings.items():
        assert result[setting] == value


def test_set_rpc_endpoint_fail_not_set_others(rotkehlchen_api_server):
    """Test that setting a non-existing eth rpc along with other settings does not modify them"""
    eth_rpc_endpoint = 'http://working.nodes.com:8545'
    main_currency = A_JPY
    data = {
        'eth_rpc_endpoint': eth_rpc_endpoint,
        'main_currency': main_currency.identifier,
    }

    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to connect to ethereum node at endpoint',
        status_code=HTTPStatus.CONFLICT,
    )

    # Get settings and make sure they have not been modified
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    assert result['main_currency'] != 'JPY'
    assert result['eth_rpc_endpoint'] != 'http://working.nodes.com:8545'


def test_disable_taxfree_after_period(rotkehlchen_api_server):
    """Test that providing -1 for the taxfree_after_period setting disables it """
    data = {
        'taxfree_after_period': -1,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['result']['taxfree_after_period'] is None


@pytest.mark.xfail(
    strict=True,
    reason='webargs does not yet handle UNKNOWN=RAISE properly. Check: '
    ' https://github.com/marshmallow-code/webargs/issues/435',
)
def test_set_unknown_settings(rotkehlchen_api_server):
    """Test that setting an unknown setting """
    # Unknown setting
    data = {
        'invalid_setting': 5555,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='todo',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_set_settings_errors(rotkehlchen_api_server):
    """set settings errors and edge cases test"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # set timeout to 1 second to timeout faster
    rotki.blockchain.ethchain.eth_rpc_timeout = 1

    # Eth rpc endpoint to which we can't connect
    data = {
        'eth_rpc_endpoint': 'http://lol.com:5555',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to connect to ethereum node at endpoint',
        status_code=HTTPStatus.CONFLICT,
    )

    # Invalid type for eth_rpc_endpoint
    data = {
        'eth_rpc_endpoint': 5555,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for premium_should_sync
    data = {
        'premium_should_sync': 444,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for include_crypto2crypto
    data = {
        'include_crypto2crypto': 'ffdsdasd',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for anonymized_logs
    data = {
        'anonymized_logs': 555.1,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for ui_floating_precision
    data = {
        'ui_floating_precision': -1,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Floating numbers precision in the UI must be between 0 and 8',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    data = {
        'ui_floating_precision': 9,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Floating numbers precision in the UI must be between 0 and 8',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for ui_floating_precision
    data = {
        'ui_floating_precision': 'dasdsds',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid integer',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for taxfree_after_period
    data = {
        'taxfree_after_period': -2,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Number of seconds after which taxfree period starts should not be negat',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for taxfree_after_period
    data = {
        'taxfree_after_period': 'dsad',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid integer',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for balance_save_frequency
    data = {
        'balance_save_frequency': 0,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='The number of hours after which balances should be saved should be >= 1',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for balance_save_frequency
    data = {
        'balance_save_frequency': 'dasdsd',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid integer',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for include_gas_cost
    data = {
        'include_gas_costs': 55.1,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for historical_data_start
    data = {
        'historical_data_start': 12,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid asset for main currenty
    data = {
        'main_currency': 'DSDSDSAD',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset DSDSDSAD',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # non FIAT asset for main currency
    data = {
        'main_currency': 'ETH',
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Asset ETH is not a FIAT asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type main currency
    data = {
        'main_currency': 243243,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type date_display_format
    data = {
        'date_display_format': 124.1,
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
