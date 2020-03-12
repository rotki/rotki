from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.blockchain import (
    assert_btc_balances_result,
    assert_eth_balances_result,
    compare_account_data,
)
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    UNIT_BTC_ADDRESS3,
    make_ethereum_address,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_query_blockchain_balances(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """Test that the query blockchain balances endpoint works correctly. That is:

       - Querying only ETH chain returns only ETH and token balances
       - Querying only BTC chain returns only BTC account balances
       - Querying with no chain returns all balances (ETH, tokens and BTC)
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)

    # First query only ETH and token balances
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ))

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # Then query only BTC balances
    with setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='BTC',
        ))
    assert_proper_response(response)
    assert json_data['message'] == ''
    json_data = response.json()
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=False,
    )

    # Finally query all balances
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    assert json_data['message'] == ''
    json_data = response.json()
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )

    # Try to query not existing blockchain
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "named_blockchain_balances_resource",
        blockchain='NOTEXISTING',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Unrecognized value NOTEXISTING given for blockchain name',
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_query_blockchain_balances_async(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """Test that the query blockchain balances endpoint works when queried asynchronously
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)

    # First query only ETH and token balances
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "named_blockchain_balances_resource",
        blockchain='ETH',
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    with setup.etherscan_patch:
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_eth_balances_result(
        rotki=rotki,
        json_data=outcome,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # Then query only BTC balances
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "named_blockchain_balances_resource",
        blockchain='BTC',
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    with setup.bitcoin_patch:
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_btc_balances_result(
        json_data=outcome,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=False,
    )

    # Finally query all balances
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainbalancesresource",
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    with setup.etherscan_patch, setup.bitcoin_patch:
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_eth_balances_result(
        rotki=rotki,
        json_data=outcome,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )
    assert_btc_balances_result(
        json_data=outcome,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_query_blockchain_balances_ignore_cache(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """Test that the query blockchain balances endpoint can ignore the cache"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)
    eth_query = patch.object(
        rotki.chain_manager,
        'query_ethereum_balances',
        wraps=rotki.chain_manager.query_ethereum_balances,
    )
    tokens_query = patch.object(
        rotki.chain_manager,
        'query_ethereum_tokens',
        wraps=rotki.chain_manager.query_ethereum_tokens,
    )

    with setup.etherscan_patch, setup.bitcoin_patch, eth_query as eth_mock, tokens_query as tokens_mock:  # noqa: E501
        # Query ETH and token balances once
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ))
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        assert_eth_balances_result(
            rotki=rotki,
            json_data=json_data,
            eth_accounts=ethereum_accounts,
            eth_balances=setup.eth_balances,
            token_balances=setup.token_balances,
            also_btc=False,
        )
        assert eth_mock.call_count == 1
        assert tokens_mock.call_count == 1

        # Query again and make sure this time cache is used
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ))
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        assert_eth_balances_result(
            rotki=rotki,
            json_data=json_data,
            eth_accounts=ethereum_accounts,
            eth_balances=setup.eth_balances,
            token_balances=setup.token_balances,
            also_btc=False,
        )
        assert eth_mock.call_count == 1
        assert tokens_mock.call_count == 1

        # Finally query with ignoring the cache
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ), json={'ignore_cache': True})
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        assert_eth_balances_result(
            rotki=rotki,
            json_data=json_data,
            eth_accounts=ethereum_accounts,
            eth_balances=setup.eth_balances,
            token_balances=setup.token_balances,
            also_btc=False,
        )
        assert eth_mock.call_count == 2
        assert tokens_mock.call_count == 2


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('query_balances_before_first_modification', [True, False])
def test_add_blockchain_accounts(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
        query_balances_before_first_modification,
):
    """Test that the endpoint adding blockchain accounts works properly"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    if query_balances_before_first_modification:
        # Also test by having balances queried before adding an account
        eth_balances = ['1000000', '2000000']
        token_balances = {'RDN': ['0', '4000000']}
        setup = setup_balances(
            rotki,
            ethereum_accounts=ethereum_accounts,
            btc_accounts=btc_accounts,
            eth_balances=eth_balances,
            token_balances=token_balances,
        )
        with setup.etherscan_patch, setup.bitcoin_patch:
            response = requests.get(api_url_for(
                rotkehlchen_api_server,
                "blockchainbalancesresource",
            ))

    new_eth_accounts = [make_ethereum_address(), make_ethereum_address()]
    all_eth_accounts = ethereum_accounts + new_eth_accounts
    eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {'RDN': ['0', '4000000', '0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    # The application has started only with 2 ethereum accounts. Let's add two more
    with setup.etherscan_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': [{'address': x} for x in new_eth_accounts]})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=query_balances_before_first_modification,
    )
    # Also make sure they are added in the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 2
    assert all(acc in accounts.btc for acc in btc_accounts)

    # Now try to query all balances to make sure the result is the stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )

    # Now we will try to add a new BTC account. Setup the mocking infrastructure again
    all_btc_accounts = btc_accounts + [UNIT_BTC_ADDRESS3]
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
        btc_balances=['3000000', '5000000', '600000000'],
    )
    # add the new BTC account
    with setup.bitcoin_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [{'address': UNIT_BTC_ADDRESS3}]})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )
    # Also make sure it's added in the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 3
    assert all(acc in accounts.btc for acc in all_btc_accounts)

    # Now try to query all balances to make sure the result is also stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_add_blockchain_accounts_async(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """A simpler version of the above test for adding blockchain accounts for async

    The main purpose of this test is to see that querying the endpoint asynchronously also works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    # Test by having balances queried before adding an account
    eth_balances = ['1000000', '2000000']
    token_balances = {'RDN': ['0', '4000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    new_eth_accounts = [make_ethereum_address(), make_ethereum_address()]
    all_eth_accounts = ethereum_accounts + new_eth_accounts
    eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {'RDN': ['0', '4000000', '0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    # The application has started only with 2 ethereum accounts. Let's add two more
    with setup.etherscan_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': [{'address': x} for x in new_eth_accounts], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_eth_balances_result(
        rotki=rotki,
        json_data=outcome,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,  # All blockchain assets have not been queried yet
    )
    # Also make sure they are added in the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 2
    assert all(acc in accounts.btc for acc in btc_accounts)

    # Now try to query all balances to make sure the result is the stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )

    # Now we will try to add a new BTC account. Setup the mocking infrastructure again
    all_btc_accounts = btc_accounts + [UNIT_BTC_ADDRESS3]
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
        btc_balances=['3000000', '5000000', '600000000'],
    )
    # add the new BTC account
    with setup.bitcoin_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [{'address': UNIT_BTC_ADDRESS3}], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_btc_balances_result(
        json_data=outcome,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )
    # Also make sure it's added in the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 3
    assert all(acc in accounts.btc for acc in all_btc_accounts)

    # Now try to query all balances to make sure the result is also stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_addding_non_checksummed_eth_account_is_error(
        rotkehlchen_api_server,
):
    """Test that adding a non checksummed eth account leads to an error"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    account = '0x7bd904a3db59fa3879bd4c246303e6ef3ac3a4c6'
    new_eth_accounts = [account]
    eth_balances = ['1000000']
    setup = setup_balances(
        rotki,
        ethereum_accounts=new_eth_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=None,
    )
    request_data = {'accounts': [{'address': account}]}
    with setup.etherscan_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg=f'Given value {account} is not a checksummed ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_blockchain_accounts_endpoint_errors(rotkehlchen_api_server, api_port, method):
    """
    Test /api/(version)/blockchains/(name) for edge cases and errors.

    Test for errors when both adding and removing a blockhain account. Both put/delete
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    # Provide unsupported blockchain name
    account = '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    data = {'accounts': [account]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='DDASDAS'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unrecognized value DDASDAS given for blockchain name',
    )

    # Provide no blockchain name
    response = requests.request(
        method,
        f'http://localhost:{api_port}/api/1/blockchains',
        json=data,
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Do not provide accounts
    data = {'dsadsad': 'foo'}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )

    # Provide wrong type of account
    data = {'accounts': 'foo'}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    if method == 'GET':
        message = "'accounts': ['Not a valid list.'"
    elif method == 'DELETE':
        message = 'Given value foo is not a checksummed ethereum address'
    else:
        message = "'accounts': {0: {'_schema': ['Invalid input type.'"
    assert_error_response(
        response=response,
        contained_in_msg=message,
    )
    assert 'foo' not in rotki.chain_manager.accounts.eth

    # Provide empty list
    data = {'accounts': []}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    verb = 'add' if method == 'PUT' else 'remove'
    assert_error_response(
        response=response,
        contained_in_msg=f'Empty list of blockchain accounts to {verb} was given',
    )

    # Provide invalid ETH account (more bytes)
    invalid_eth_account = '0x554FFc77f4251a9fB3c0E3590a6a205f8d4e067d01'
    msg = f'Given value {invalid_eth_account} is not a checksummed ethereum address'
    if method == 'PUT':
        data = {'accounts': [{'address': invalid_eth_account}]}
    else:
        data = {'accounts': [invalid_eth_account]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=msg,
    )

    # Provide invalid BTC account
    invalid_btc_account = '18ddjB7HWTaxzvTbLp1nWvaixU3U2oTZ1'
    if method == 'PUT':
        data = {'accounts': [{'address': invalid_btc_account}]}
    else:
        data = {'accounts': [invalid_btc_account]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )

    msg = f'Given value {invalid_btc_account} is not a valid bitcoin address'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
    )
    assert_msg = 'Invalid BTC account should not have been added'
    assert invalid_btc_account not in rotki.chain_manager.accounts.btc, assert_msg

    # Provide not existing but valid ETH account for removal
    unknown_account = make_ethereum_address()
    data = {'accounts': [unknown_account]}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown ETH accounts {unknown_account}',
    )

    # Provide not existing but valid BTC account for removal
    unknown_btc_account = '18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2'
    data = {'accounts': [unknown_btc_account]}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown BTC accounts {unknown_btc_account}',
    )

    # Provide list with one valid and one invalid account and make sure that nothing
    # is added / removed and the valid one is skipped
    msg = 'Given value 142 is not a checksummed ethereum address'
    if method == 'DELETE':
        # Account should be an existing account
        account = rotki.chain_manager.accounts.eth[0]
        data = {'accounts': ['142', account]}
    else:
        # else keep the new account to add
        data = {'accounts': [{'address': '142'}, {'address': account}]}

    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for accounts
    if method == 'PUT':
        data = {'accounts': [{'address': 15}]}
    else:
        data = {'accounts': [15]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )

    # Test that providing an account more than once in request data is an error
    account = '0x7BD904A3Db59fA3879BD4c246303E6Ef3aC3A4C6'
    if method == 'PUT':
        data = {'accounts': [{'address': account}, {'address': account}]}
    else:
        data = {'accounts': [account, account]}
    response = requests.request(method, api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=data)
    assert_error_response(
        response=response,
        contained_in_msg=f'Address {account} appears multiple times in the request data',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_add_blockchain_accounts_with_tags_and_label_and_querying_them(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    """Test that adding account with labels and tags works correctly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add three tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)
    tag3 = {
        'name': 'hardware',
        'description': 'hardware wallets',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag3,
    )
    assert_proper_response(response)

    # Now add 3 accounts. Some of them  use these tags, some dont
    new_eth_accounts = [make_ethereum_address(), make_ethereum_address(), make_ethereum_address()]
    eth_balances = ['1000000', '4000000', '2000000']
    token_balances = {'RDN': ['100000', '350000', '2223']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=new_eth_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )
    accounts_data = [{
        "address": new_eth_accounts[0],
        "label": 'my metamask',
        'tags': ['public', 'desktop'],
    }, {
        "address": new_eth_accounts[1],
        "label": 'geth account',
    }, {
        "address": new_eth_accounts[2],
        'tags': ['public', 'hardware'],
    }]
    # Make sure that even adding accounts with label and tags, balance query works fine
    with setup.etherscan_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': accounts_data})
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=new_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # Now query the ethereum account data to see that tags and labels are added
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ))
    assert_proper_response(response)
    response_data = response.json()['result']
    assert len(response_data) == len(accounts_data)
    for entry in response_data:
        # find the corresponding account in accounts data
        compare_account = None
        for account in accounts_data:
            if entry['address'] == account['address']:
                compare_account = account
                break
        assert compare_account, 'Found unexpected address {entry["address"]} in response'

        assert entry['address'] == compare_account['address']
        assert entry['label'] == compare_account.get('label', None)
        if entry['tags'] is not None:
            assert set(entry['tags']) == set(compare_account['tags'])
        else:
            assert 'tags' not in compare_account


@pytest.mark.parametrize('number_of_eth_accounts', [3])
def test_edit_blockchain_accounts(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    """Test that the endpoint editing blockchain accounts works properly"""
    # Add two tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)

    # Edit 2 out of the 3 accounts so that they have tags
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'Second account in the array',
        'tags': ['public'],
    }, {
        'address': ethereum_accounts[2],
        'label': 'Thirds account in the array',
        'tags': ['public', 'desktop'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    expected_result = request_data['accounts'] + [
        {'address': ethereum_accounts[0]},
    ]
    compare_account_data(json_data['result'], expected_result)

    # Also make sure that when querying the endpoint we get the edited account data
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ))
    assert_proper_response(response)
    json_data = response.json()
    compare_account_data(json_data['result'], expected_result)


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_edit_blockchain_account_errors(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that errors are handled properly in the edit accounts endpoint"""
    # Add two tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)

    request_data = {'accounts': [{
        'address': ethereum_accounts[0],
        'label': 'Second account in the array',
        'tags': ['public'],
    }, {
        'address': ethereum_accounts[1],
        'label': 'Thirds account in the array',
        'tags': ['public', 'desktop'],
    }]}

    # Missing accounts
    request_data = {'foo': ['a']}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg="accounts': ['Missing data for required field",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for accounts
    request_data = {'accounts': 142}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing address for an account
    request_data = {'accounts': [{
        'label': 'Second account in the array',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg="address': ['Missing data for required field",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for an account's address
    request_data = {'accounts': [{
        'address': 55,
        'label': 'Second account in the array',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg="address': ['Not a valid string",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid address for an account's address
    request_data = {'accounts': [{
        'address': 'dsadsd',
        'label': 'Second account in the array',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='Given value dsadsd is not a checksummed ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for label
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 55,
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg="label': ['Not a valid string",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for tags
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': 231,
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg="tags': ['Not a valid list",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for tags list entry
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': [55.221],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg="tags': {0: ['Not a valid string",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # One non existing tag
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['nonexistant'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='When editing blockchain accounts, unknown tags nonexistant were found',
        status_code=HTTPStatus.CONFLICT,
    )

    # Mix of existing and non-existing tags
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='When editing blockchain accounts, unknown tags ',
        status_code=HTTPStatus.CONFLICT,
    )

    # Provide same account multiple times in request data
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }, {
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }]}
    msg = f'Address {ethereum_accounts[1]} appears multiple times in the request data'
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [4])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('query_balances_before_first_modification', [True, False])
def test_remove_blockchain_accounts(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
        query_balances_before_first_modification,
):
    """Test that the endpoint removing blockchain accounts works properly"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    eth_accounts_after_removal = [ethereum_accounts[1], ethereum_accounts[3]]
    all_eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {'RDN': ['0', '0', '450000000', '0']}
    eth_balances_after_removal = ['2000000', '4000000']
    token_balances_after_removal = {'RDN': ['0', '0']}
    if query_balances_before_first_modification:
        # Also test by having balances queried before removing an account
        setup = setup_balances(
            rotki,
            ethereum_accounts=ethereum_accounts,
            btc_accounts=btc_accounts,
            eth_balances=all_eth_balances,
            token_balances=token_balances,
        )
        with setup.etherscan_patch, setup.bitcoin_patch:
            response = requests.get(api_url_for(
                rotkehlchen_api_server,
                "blockchainbalancesresource",
            ))
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        eth_balances=all_eth_balances,
        token_balances=token_balances,
    )

    # The application has started with 4 ethereum accounts. Remove two and see that balances match
    with setup.etherscan_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': removed_eth_accounts})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=query_balances_before_first_modification,
    )
    # Also make sure they are removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 2
    assert all(acc in accounts.btc for acc in btc_accounts)

    # Now try to query all balances to make sure the result is the stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=True,
    )

    # Now we will try to remove a BTC account. Setup the mocking infrastructure again
    all_btc_accounts = [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    btc_accounts_after_removal = [UNIT_BTC_ADDRESS2]
    setup = setup_balances(
        rotki,
        ethereum_accounts=eth_accounts_after_removal,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        btc_balances=['3000000', '5000000'],
    )
    # remove the new BTC account
    with setup.bitcoin_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS1]})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )
    # Also make sure it's removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 1
    assert all(acc in accounts.btc for acc in btc_accounts_after_removal)

    # Now try to query all balances to make sure the result is also stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [4])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
def test_remove_blockchain_accounts_async(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """A simpler version of the above test for removing blockchain accounts for async

    The main purpose of this test is to see that querying the endpoint asynchronously also works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    # Test by having balances queried before removing an account
    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    eth_accounts_after_removal = [ethereum_accounts[1], ethereum_accounts[3]]
    all_eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {'RDN': ['0', '250000000', '450000000', '0']}
    eth_balances_after_removal = ['2000000', '4000000']
    token_balances_after_removal = {'RDN': ['250000000', '0']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        eth_balances=all_eth_balances,
        token_balances=token_balances,
    )
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        eth_balances=all_eth_balances,
        token_balances=token_balances,
    )

    # The application has started with 4 ethereum accounts. Remove two and see that balances match
    with setup.etherscan_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': removed_eth_accounts, 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_eth_balances_result(
        rotki=rotki,
        json_data=outcome,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=True,  # We queried all balances at the start
    )
    # Also make sure they are removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 2
    assert all(acc in accounts.btc for acc in btc_accounts)

    # Now try to query all balances to make sure the result is the stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=True,
    )

    # Now we will try to remove a BTC account. Setup the mocking infrastructure again
    all_btc_accounts = [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    btc_accounts_after_removal = [UNIT_BTC_ADDRESS2]
    setup = setup_balances(
        rotki,
        ethereum_accounts=eth_accounts_after_removal,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        btc_balances=['3000000', '5000000'],
    )
    # remove the new BTC account
    with setup.bitcoin_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS1], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_btc_balances_result(
        json_data=outcome,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )
    # Also make sure it's removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 1
    assert all(acc in accounts.btc for acc in btc_accounts_after_removal)

    # Now try to query all balances to make sure the result is also stored
    with setup.etherscan_patch, setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_remove_nonexisting_blockchain_account_along_with_existing(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    """Test that if an existing and a non-existing account are given to remove, nothing is"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add a tag
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    # Edit the first ethereum account which we will attempt to delete
    # to have this tag so that we see the mapping is still there afterwards
    request_data = {'accounts': [{'address': ethereum_accounts[0], 'tags': ['public']}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_proper_response(response)
    expected_data = request_data['accounts'] + [
        {'address': ethereum_accounts[1]},
    ]
    compare_account_data(response.json()['result'], expected_data)

    eth_balances = ['11110', '22222']
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=None,
    )
    unknown_account = make_ethereum_address()
    with setup.etherscan_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': [ethereum_accounts[0], unknown_account]})
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown ETH accounts {unknown_account}',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Also make sure that no account was removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in ethereum_accounts)
    # Also make sure no tag mappings were removed
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == ethereum_accounts[0]
    assert query[0][1] == 'public'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_blockchain_account_with_tags_removes_mapping(
        rotkehlchen_api_server,
        number_of_eth_accounts,
):
    """Test that removing an account with tags remove the mappings"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add two tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)

    # Now add 2 accounts both of them using tags
    new_btc_accounts = [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    btc_balances = ['10000', '500500000']
    setup = setup_balances(
        rotki,
        ethereum_accounts=None,
        btc_accounts=new_btc_accounts,
        eth_balances=None,
        token_balances=None,
        btc_balances=btc_balances,
    )
    accounts_data = [{
        "address": new_btc_accounts[0],
        "label": 'my btc miner',
        'tags': ['public', 'desktop'],
    }, {
        "address": new_btc_accounts[1],
        'label': 'other account',
        'tags': ['desktop'],
    }]
    with setup.bitcoin_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': accounts_data})
    assert_proper_response(response)
    assert_btc_balances_result(
        json_data=response.json(),
        btc_accounts=new_btc_accounts,
        btc_balances=btc_balances,
        also_eth=False,
    )

    # now remove one account
    with setup.bitcoin_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS1]})
    assert_proper_response(response)
    assert_btc_balances_result(
        json_data=response.json(),
        btc_accounts=[UNIT_BTC_ADDRESS2],
        btc_balances=['500500000'],
        also_eth=False,
    )

    # Now check the DB directly and see that tag mappings of the deleted account are gone
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == UNIT_BTC_ADDRESS2
    assert query[0][1] == 'desktop'
