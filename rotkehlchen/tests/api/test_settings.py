from http import HTTPStatus
from typing import Dict, List
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.constants import CLOUDFLARE_NODE_NAME, MYCRYPTO_NODE_NAME
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION, DBSettings
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.constants import A_JPY
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.mock import MockWeb3
from rotkehlchen.types import (
    ChecksumEthAddress,
    CostBasisMethod,
    ExchangeLocationID,
    Location,
    ModuleName,
)


def test_querying_settings(rotkehlchen_api_server, username):
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
        'last_data_migration',
    )
    for setting, value in original_settings.items():
        if setting in unmodifiable_settings:
            continue

        if setting == 'date_display_format':
            value = '%d/%m/%Y-%H:%M:%S'
        elif setting == 'eth_rpc_endpoint':
            value = 'http://working.nodes.com:8545'
        elif setting == 'main_currency':
            value = 'JPY'
        elif type(value) == bool:  # pylint: disable=unidiomatic-typecheck
            # here and below we HAVE to use type() equality checks since
            # isinstance of a bool succeeds for both bool and int (due to inheritance)
            value = not value
        elif type(value) == int:  # pylint: disable=unidiomatic-typecheck
            value += 1
        elif setting == 'active_modules':
            value = ['makerdao_vaults']
        elif setting == 'frontend_settings':
            value = ''
        elif setting == 'ksm_rpc_endpoint':
            value = 'http://kusama.node.com:9933'
        elif setting == 'dot_rpc_endpoint':
            value = 'http://polkadot.node.com:9934'
        elif setting == 'current_price_oracles':
            value = ['coingecko', 'cryptocompare', 'uniswapv2', 'uniswapv3', 'saddle']
        elif setting == 'historical_price_oracles':
            value = ['coingecko', 'cryptocompare']
        elif setting == 'taxable_ledger_actions':
            value = ['income']
        elif setting == 'non_syncing_exchanges':
            value = [ExchangeLocationID(name='test_name', location=Location.KRAKEN).serialize()]
        elif setting == 'cost_basis_method':
            value = CostBasisMethod.LIFO.serialize()
        elif setting == 'ethereum_nodes_to_connect':
            value = [
                {
                    'node_name': CLOUDFLARE_NODE_NAME.name,
                    'weight': 40,
                },
                {
                    'node_name': MYCRYPTO_NODE_NAME.name,
                    'weight': 60,
                },
            ]
        else:
            raise AssertionError(f'Unexpected settting {setting} encountered')

        new_settings[setting] = value

    expected_nodes_settings = [
        {
            'node': 'cloudflare',
            'endpoint': 'https://cloudflare-eth.com/',
            'weight': 40,
            'owned': False,
        },
        {
            'node': 'mycrypto',
            'endpoint': 'https://api.mycryptoapi.com/eth',
            'weight': 60,
            'owned': False,
        },
    ]

    # modify the settings
    block_query = patch(
        'rotkehlchen.chain.ethereum.manager.EthereumManager.query_eth_highest_block',
        return_value=0,
    )
    mock_web3 = patch('rotkehlchen.chain.ethereum.manager.Web3', MockWeb3)
    ksm_connect_node = patch(
        'rotkehlchen.chain.substrate.manager.SubstrateManager._connect_node',
        return_value=(True, ''),
    )
    with block_query, mock_web3, ksm_connect_node:
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
        if setting == 'ethereum_nodes_to_connect':
            assert result[setting] == expected_nodes_settings
        else:
            assert result[setting] == value, msg

    # now check that the same settings are returned in a settings query
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    for setting, value in new_settings.items():
        if setting == 'ethereum_nodes_to_connect':
            assert result[setting] == expected_nodes_settings
        else:
            assert result[setting] == value


@pytest.mark.parametrize('rpc_setting, error_msg', [
    (
        'ksm_rpc_endpoint',
        'Kusama failed to connect to own node at endpoint',
    ),
])
def test_set_rpc_endpoint_fail_not_set_others(
        rotkehlchen_api_server,
        rpc_setting,
        error_msg,
):
    """Test that setting a non-existing eth rpc along with other settings does not modify them"""
    rpc_endpoint = 'http://working.nodes.com:8545'
    main_currency = A_JPY
    data = {'settings': {
        rpc_setting: rpc_endpoint,
        'main_currency': main_currency.identifier,
    }}

    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg=f'{error_msg} {rpc_endpoint}',
        status_code=HTTPStatus.CONFLICT,
    )

    # Get settings and make sure they have not been modified
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    assert result['main_currency'] != 'JPY'
    assert result[rpc_setting] != rpc_endpoint


@pytest.mark.parametrize('rpc_setting', ['ksm_rpc_endpoint'])
def test_unset_rpc_endpoint(rotkehlchen_api_server, rpc_setting):
    """Test the rpc endpoint can be unset"""
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert result[rpc_setting] != ''

    data = {'settings': {rpc_setting: ''}}

    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_proper_response(response)

    json_data = response.json()
    result = json_data['result']
    assert json_data['message'] == ''
    assert result[rpc_setting] == ''


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

    # Invalid asset for main currency
    data = {
        'settings': {'main_currency': 'DSDSDSAD'},
    }
    response = requests.put(api_url_for(rotkehlchen_api_server, "settingsresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset DSDSDSAD',
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


def assert_queried_addresses_match(
        result: Dict[ModuleName, List[ChecksumEthAddress]],
        expected: Dict[ModuleName, List[ChecksumEthAddress]],
) -> None:
    assert len(result) == len(expected)
    for key, value in expected.items():
        assert key in result, f'Was expecting module {key} but did not find it'
        assert set(value) == set(result[key])


def test_queried_addresses_per_protocol(rotkehlchen_api_server):
    # First add some queried addresses per protocol
    address1 = make_ethereum_address()
    data = {'module': 'aave', 'address': address1}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    result = assert_proper_response_with_result(response)
    assert result == {'aave': [address1]}

    address2 = make_ethereum_address()
    data = {'module': 'makerdao_vaults', 'address': address2}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    result = assert_proper_response_with_result(response)
    assert_queried_addresses_match(result, {
        'aave': [address1],
        'makerdao_vaults': [address2],
    })

    # add same address to another module/protocol
    data = {'module': 'aave', 'address': address2}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    result = assert_proper_response_with_result(response)
    assert_queried_addresses_match(result, {
        'aave': [address1, address2],
        'makerdao_vaults': [address2],
    })

    # try to add an address that already exists for a module/protocol and assert we get an error
    data = {'module': 'aave', 'address': address1}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'{address1} is already in the queried addresses for aave',
        status_code=HTTPStatus.CONFLICT,
    )

    # add an address and then remove it
    address3 = make_ethereum_address()
    data = {'module': 'makerdao_dsr', 'address': address3}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    result = assert_proper_response_with_result(response)
    assert_queried_addresses_match(result, {
        'aave': [address1, address2],
        'makerdao_vaults': [address2],
        'makerdao_dsr': [address3],
    })

    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    result = assert_proper_response_with_result(response)
    assert_queried_addresses_match(result, {
        'aave': [address1, address2],
        'makerdao_vaults': [address2],
    })

    # try to remove a non-existing address and module combination and assert we get an error
    data = {'module': 'makerdao_vaults', 'address': address1}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "queriedaddressesresource"), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'{address1} is not in the queried addresses for makerdao_vaults',
        status_code=HTTPStatus.CONFLICT,
    )

    # test that getting the queried addresses per module works
    response = requests.get(api_url_for(rotkehlchen_api_server, "queriedaddressesresource"))
    result = assert_proper_response_with_result(response)
    assert_queried_addresses_match(result, {
        'aave': [address1, address2],
        'makerdao_vaults': [address2],
    })


def test_excluded_exchanges_settings(rotkehlchen_api_server):
    exchanges_input = {
        'settings': {
            'non_syncing_exchanges': [
                ExchangeLocationID(name="test_name", location=Location.KRAKEN).serialize(),
                ExchangeLocationID(name="test_name2", location=Location.KRAKEN).serialize(),
            ],
        },
    }
    exchanges_expected = [
        ExchangeLocationID(name="test_name", location=Location.KRAKEN).serialize(),
        ExchangeLocationID(name="test_name2", location=Location.KRAKEN).serialize(),
    ]

    exchanges_bad_input = {
        'settings': {
            'non_syncing_exchanges': [
                ExchangeLocationID(name="bad_name", location=Location.KRAKEN).serialize(),
                ExchangeLocationID(name="bad_name", location=Location.KRAKEN).serialize(),
            ],
        },
    }

    requests.put(
        api_url_for(rotkehlchen_api_server, "settingsresource"),
        json=exchanges_input,
    )
    response = requests.get(api_url_for(rotkehlchen_api_server, "settingsresource")).json()
    assert response['result']['non_syncing_exchanges'] == exchanges_expected

    response = requests.put(
        api_url_for(rotkehlchen_api_server, "settingsresource"),
        json=exchanges_bad_input,
    )
    assert response.status_code == 400
