from http import HTTPStatus
from typing import List

import requests
from eth_utils.address import to_checksum_address

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response


def check_positive_balances_result(
        response: requests.Response,
        asset_symbols: List[str],
        account: str,
) -> None:
    assert response['result'] is not None
    assert response['message'] == ''
    result = response['result']

    for asset_symbol in asset_symbols:
        if asset_symbol != 'BTC':
            assert asset_symbol in result['per_account']['ETH'][account]
        assert 'usd_value' in result['per_account'][asset_symbol][account]
        assert 'amount' in result['totals'][asset_symbol]
        assert 'usd_value' in result['totals'][asset_symbol]


def check_no_balances_result(
        response: requests.Response,
        asset_symbols: List[str],
        check_per_account: bool = True,
) -> None:
    assert response['result'] is not None
    assert response['message'] == ''
    result = response['result']

    for asset_symbol in asset_symbols:
        if check_per_account:
            assert result['per_account'][asset_symbol] == {}
        assert FVal(result['totals'][asset_symbol]['amount']) == FVal('0')
        assert FVal(result['totals'][asset_symbol]['usd_value']) == FVal('0')


def test_add_remove_blockchain_account(rotkehlchen_api_server):
    """
    Test that the api call to add or remove a blockchain account correctly appends
    the accounts and properly updates the balances

    Also serves as regression for issue https://github.com/rotkehlchenio/rotkehlchen/issues/66
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add/remove an ETH account and check balances
    eth_account = '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    checksummed_eth_account = to_checksum_address(eth_account)
    data = {'accounts': [eth_account]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_proper_response(response)
    check_positive_balances_result(response.json(), ['ETH'], checksummed_eth_account)
    assert checksummed_eth_account in rotki.blockchain.accounts.eth

    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_proper_response(response)
    check_no_balances_result(response.json(), ['ETH'])
    assert checksummed_eth_account not in rotki.blockchain.accounts.eth

    # Add/remove an BTC account and check balances
    btc_account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    data = {'accounts': [btc_account]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )
    check_positive_balances_result(response.json(), ['BTC'], btc_account)
    assert btc_account in rotki.blockchain.accounts.btc

    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )
    assert_proper_response(response)
    check_no_balances_result(response.json(), ['BTC'])
    assert btc_account not in rotki.blockchain.accounts.btc


def test_blockchain_accounts_endpoint_errors(rotkehlchen_api_server, api_port):
    """
    Test /api/(version)/blockchains/(name) for edge cases and errors
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Provide unsupported blockchain name
    account = '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    checksummed_account = to_checksum_address(account)
    data = {'accounts': [account]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='DDASDAS'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unrecognized value DDASDAS given for blockchain name',
    )
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='DDASDAS'),
        json=data,
    )

    # Provide no blockchain name
    response = requests.put(
        f'http://localhost:{api_port}/api/1/blockchains',
        json=data,
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
    )
    response = requests.delete(
        f'http://localhost:{api_port}/api/1/blockchains',
        json=data,
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Do not provide accounts
    data = {'dsadsad': 'foo'}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )

    # Provide wrong type of account
    data = {'accounts': 'foo'}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a valid ETH address',
    )
    assert 'foo' not in rotki.blockchain.accounts.eth
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a valid ETH address',
    )
    assert 'foo' not in rotki.blockchain.accounts.eth

    # Provide list with one valid and one invalid account and make sure that the
    # valid one is added but we get an error for the invalid one
    data = {'accounts': ['142', account]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_proper_response(response=response)
    assert '142 is not a valid ETH address' in response.json()['message']
    assert checksummed_account in rotki.blockchain.accounts.eth
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_proper_response(response=response)
    assert '142 is not a valid ETH address' in response.json()['message']
    assert checksummed_account not in rotki.blockchain.accounts.eth

    # Provide invalid type for accounts
    data = {'accounts': [15]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )
