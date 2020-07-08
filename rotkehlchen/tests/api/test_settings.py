from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants.assets import A_JPY
from rotkehlchen.db.settings import DEFAULT_KRAKEN_ACCOUNT_TYPE, ROTKEHLCHEN_DB_VERSION, DBSettings
from rotkehlchen.exchanges.kraken import KrakenAccountType
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
        'have_premium',
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
        elif setting == 'kraken_account_type':
            # Change the account type to anything other than default
            assert value != str(KrakenAccountType.PRO)
            value = str(KrakenAccountType.PRO)
        elif setting == 'active_modules':
            value = ['makerdao_vaults']
        else:
            raise AssertionError(f'Unexpected settting {setting} encountered')

        new_settings[setting] = value

    # modify the settings
    block_query = patch(
        'rotkehlchen.chain.ethereum.manager.EthereumManager.query_eth_highest_block',
        return_value=0,
    )
    mock_web3 = patch('rotkehlchen.chain.ethereum.manager.Web3', MockWeb3)
    with block_query, mock_web3:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "settingsresource"),
            json={'settings': new_settings},
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
    data = {'settings': {
        'eth_rpc_endpoint': eth_rpc_endpoint,
        'main_currency': main_currency.identifier,
    }}

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


def test_unset_rpc_endpoint(rotkehlchen_api_server):
    """Test the rpc endpoint can be unset"""
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert result['eth_rpc_endpoint'] != ''

    data = {
        'settings': {'eth_rpc_endpoint': ''},
    }

    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_proper_response(response)

    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    assert result['eth_rpc_endpoint'] == ''


@pytest.mark.parametrize('added_exchanges', [('kraken',)])
def test_set_kraken_account_type(rotkehlchen_api_server_with_exchanges):
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    kraken = rotki.exchange_manager.get('kraken')
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE
    assert kraken.call_limit == 15
    assert kraken.reduction_every_secs == 3

    data = {'settings': {'kraken_account_type': 'intermediate'}}
    response = requests.put(api_url_for(server, "settingsresource"), json=data)
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    assert result['kraken_account_type'] == 'intermediate'
    assert kraken.account_type == KrakenAccountType.INTERMEDIATE
    assert kraken.call_limit == 20
    assert kraken.reduction_every_secs == 2


def test_disable_taxfree_after_period(rotkehlchen_api_server):
    """Test that providing -1 for the taxfree_after_period setting disables it """
    data = {
        'settings': {'taxfree_after_period': -1},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['result']['taxfree_after_period'] is None

    # Test that any other negative value is refused
    data = {
        'settings': {'taxfree_after_period': -5},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='The taxfree_after_period value can not be negative',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that zero value is refused
    data = {
        'settings': {'taxfree_after_period': 0},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='The taxfree_after_period value can not be set to zero',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_set_unknown_settings(rotkehlchen_api_server):
    """Test that setting an unknown setting results in an error

    This is the only test for unknown arguments in marshmallow schemas after
    https://github.com/rotki/rotki/issues/532 was implemented"""
    # Unknown setting
    data = {
        'settings': {'invalid_setting': 5555},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='{"invalid_setting": ["Unknown field."',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_set_settings_errors(rotkehlchen_api_server):
    """set settings errors and edge cases test"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # set timeout to 1 second to timeout faster
    rotki.chain_manager.ethereum.eth_rpc_timeout = 1

    # Eth rpc endpoint to which we can't connect
    data = {
        'settings': {'eth_rpc_endpoint': 'http://lol.com:5555'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to connect to ethereum node at endpoint',
        status_code=HTTPStatus.CONFLICT,
    )

    # Invalid type for eth_rpc_endpoint
    data = {
        'settings': {'eth_rpc_endpoint': 5555},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for premium_should_sync
    data = {
        'settings': {'premium_should_sync': 444},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for include_crypto2crypto
    data = {
        'settings': {'include_crypto2crypto': 'ffdsdasd'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for anonymized_logs
    data = {
        'settings': {'anonymized_logs': 555.1},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for ui_floating_precision
    data = {
        'settings': {'ui_floating_precision': -1},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Floating numbers precision in the UI must be between 0 and 8',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    data = {
        'settings': {'ui_floating_precision': 9},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Floating numbers precision in the UI must be between 0 and 8',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for ui_floating_precision
    data = {
        'settings': {'ui_floating_precision': 'dasdsds'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid integer',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for taxfree_after_period
    data = {
        'settings': {'taxfree_after_period': -2},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='The taxfree_after_period value can not be negative, except',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for taxfree_after_period
    data = {
        'settings': {'taxfree_after_period': 'dsad'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='dsad is not a valid integer',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for balance_save_frequency
    data = {
        'settings': {'balance_save_frequency': 0},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='The number of hours after which balances should be saved should be >= 1',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid range for balance_save_frequency
    data = {
        'settings': {'balance_save_frequency': 'dasdsd'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid integer',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for include_gas_cost
    data = {
        'settings': {'include_gas_costs': 55.1},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for historical_data_start
    data = {
        'settings': {'historical_data_start': 12},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid asset for main currenty
    data = {
        'settings': {'main_currency': 'DSDSDSAD'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset DSDSDSAD',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # non FIAT asset for main currency
    data = {
        'settings': {'main_currency': 'ETH'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Asset ETH is not a FIAT asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type main currency
    data = {
        'settings': {'main_currency': 243243},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type date_display_format
    data = {
        'settings': {'date_display_format': 124.1},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type kraken_account_type
    data = {
        'settings': {'kraken_account_type': 124.1},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='is not a valid kraken account type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid value kraken_account_type
    data = {
        'settings': {'kraken_account_type': 'super hyper pro'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='is not a valid kraken account type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for active modules
    data = {
        'settings': {'active_modules': 55},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='"active_modules": ["Not a valid list."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid module for active modules
    data = {
        'settings': {'active_modules': ['makerdao_dsr', 'foo']},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='"active_modules": ["foo is not a valid module"]',
        status_code=HTTPStatus.BAD_REQUEST,
    )
