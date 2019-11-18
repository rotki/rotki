import json
from http import HTTPStatus
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
import requests
from eth_utils.address import to_checksum_address

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    make_ethereum_address,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc


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


def mock_balances_query(eth_map: Dict[str, str], btc_map: Dict[str, str], original_requests_get):

    def mock_requests_get(url, *args, **kwargs):
        if 'etherscan.io/api?module=account&action=balancemulti' in url:
            accounts = []
            for addr, value in eth_map.items():
                accounts.append({'account': addr, 'balance': value['ETH']})
            response = f'{{"status":"1","message":"OK","result":{json.dumps(accounts)}}}'
        elif 'api.etherscan.io/api?module=account&action=tokenbalance' in url:
            response = '{"status":"1","message":"OK","result":"0"}'
            for addr, value in eth_map.items():
                if addr in url and 'RDN' in value:
                    response = f'{{"status":"1","message":"OK","result":"{value["RDN"]}"}}'

        elif 'blockchain.info' in url:
            queried_addr = url.split('/')[-1]
            msg = f'Queried BTC address {queried_addr} is not in the given btc map to mock'
            assert queried_addr in btc_map, msg
            response = btc_map[queried_addr]

        else:
            return original_requests_get(url, *args, **kwargs)

        return MockResponse(200, response)

    return patch('rotkehlchen.utils.misc.requests.get', wraps=mock_requests_get)


@pytest.mark.parametrize('ethereum_accounts', [[make_ethereum_address(), make_ethereum_address()]])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_query_blockchain_balances(rotkehlchen_api_server, ethereum_accounts, btc_accounts):
    """Test that the query blockchain balances endpoint works correctly. That is:

       - Querying only ETH chain returns only ETH and token balances
       - Querying only BTC chain returns only BTC account balances
       - Querying with no chain returns all balances (ETH, tokens and BTC)
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.blockchain.cache_ttl_secs = 0

    eth_acc1 = ethereum_accounts[0]
    eth_acc2 = ethereum_accounts[1]
    eth_balance1 = '1000000'
    eth_balance2 = '2000000'
    btc_balance1 = '3000000'
    btc_balance2 = '5000000'
    rdn_balance = '4000000'

    def assert_eth_result(json_data: Dict[str, Any], also_btc: bool) -> None:
        result = json_data['result']
        per_account = result['per_account']
        if also_btc:
            assert len(per_account) == 2
        else:
            assert len(per_account) == 1
        per_account = per_account['ETH']
        assert len(per_account) == 2
        assert FVal(per_account[eth_acc1]['ETH']) == from_wei(FVal(eth_balance1))
        assert FVal(per_account[eth_acc1]['usd_value']) > ZERO
        assert FVal(per_account[eth_acc2]['ETH']) == from_wei(FVal(eth_balance2))
        assert FVal(per_account[eth_acc2]['RDN']) == from_wei(FVal(rdn_balance))
        assert FVal(per_account[eth_acc2]['usd_value']) > ZERO

        totals = result['totals']
        if also_btc:
            assert len(totals) == 3
        else:
            assert len(totals) == 2

        assert FVal(totals['ETH']['amount']) == (
            from_wei(FVal(eth_balance1)) +
            from_wei(FVal(eth_balance2))
        )
        assert FVal(totals['ETH']['usd_value']) > ZERO
        assert FVal(totals['RDN']['amount']) == from_wei(FVal(rdn_balance))
        assert FVal(totals['RDN']['usd_value']) > ZERO

    def assert_btc_result(json_data: Dict[str, Any], also_eth: bool) -> None:
        result = json_data['result']
        per_account = result['per_account']
        if also_eth:
            assert len(per_account) == 2
        else:
            assert len(per_account) == 1
        per_account = per_account['BTC']
        assert len(per_account) == 2
        assert FVal(per_account[UNIT_BTC_ADDRESS1]['amount']) == satoshis_to_btc(
            FVal(btc_balance1),
        )
        assert FVal(per_account[UNIT_BTC_ADDRESS1]['usd_value']) > ZERO
        assert FVal(per_account[UNIT_BTC_ADDRESS2]['amount']) == satoshis_to_btc(
            FVal(btc_balance2),
        )
        assert FVal(per_account[UNIT_BTC_ADDRESS2]['usd_value']) > ZERO

        totals = result['totals']
        if also_eth:
            assert len(totals) == 3
        else:
            assert len(totals) == 1

        assert FVal(totals['BTC']['amount']) == (
            satoshis_to_btc(FVal(btc_balance1)) +
            satoshis_to_btc(FVal(btc_balance2))
        )
        assert FVal(totals['BTC']['usd_value']) > ZERO

    patched_balances = mock_balances_query(
        eth_map={
            eth_acc1: {'ETH': eth_balance1},
            eth_acc2: {'ETH': eth_balance2, 'RDN': rdn_balance},
        },
        btc_map={btc_accounts[0]: btc_balance1, btc_accounts[1]: btc_balance2},
        original_requests_get=requests.get,
    )

    # First query only ETH and token balances
    with patched_balances:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ))

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_result(json_data, also_btc=False)

    # Then query only BTC balances
    with patched_balances:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='BTC',
        ))
    assert_proper_response(response)
    assert json_data['message'] == ''
    json_data = response.json()
    assert_btc_result(json_data, also_eth=False)

    # Finally query all balances
    with patched_balances:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    assert json_data['message'] == ''
    json_data = response.json()
    assert_eth_result(json_data, also_btc=True)
    assert_btc_result(json_data, also_eth=True)
