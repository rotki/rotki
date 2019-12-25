from http import HTTPStatus

import pytest
import requests
from eth_utils.address import to_checksum_address

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
    rotki.blockchain.cache_ttl_secs = 0

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)

    # First query only ETH and token balances
    with setup.blockchain_patch:
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
    with setup.blockchain_patch:
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
    with setup.blockchain_patch:
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
    rotki.blockchain.cache_ttl_secs = 0

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)

    # First query only ETH and token balances
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "named_blockchain_balances_resource",
        blockchain='ETH',
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    with setup.blockchain_patch:
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

    with setup.blockchain_patch:
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

    with setup.blockchain_patch:
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
    rotki.blockchain.cache_ttl_secs = 0

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
    with setup.blockchain_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': new_eth_accounts})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,  # All blockchain assets have not been queried yet
    )

    # Now try to query all balances to make sure the result is the stored
    with setup.blockchain_patch:
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
    with setup.blockchain_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS3]})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_btc_balances_result(
        json_data=json_data,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )

    # Now try to query all balances to make sure the result is also stored
    with setup.blockchain_patch:
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
    rotki.blockchain.cache_ttl_secs = 0
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
    with setup.blockchain_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': new_eth_accounts, 'async_query': True})
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

    # Now try to query all balances to make sure the result is the stored
    with setup.blockchain_patch:
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
    with setup.blockchain_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS3], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_btc_balances_result(
        json_data=outcome,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )

    # Now try to query all balances to make sure the result is also stored
    with setup.blockchain_patch:
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


@pytest.mark.parametrize('method', ['put', 'delete'])
def test_blockchain_accounts_endpoint_errors(rotkehlchen_api_server, api_port, method):
    """
    Test /api/(version)/blockchains/(name) for edge cases and errors.

    Test for errors when both adding and removing a blockhain account. Both put/delete
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Provide unsupported blockchain name
    account = '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    checksummed_account = to_checksum_address(account)
    data = {'accounts': [account]}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='DDASDAS'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unrecognized value DDASDAS given for blockchain name',
    )

    # Provide no blockchain name
    response = getattr(requests, method)(
        f'http://localhost:{api_port}/api/1/blockchains',
        json=data,
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Do not provide accounts
    data = {'dsadsad': 'foo'}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )

    # Provide wrong type of account
    data = {'accounts': 'foo'}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a valid ETH address',
    )
    assert 'foo' not in rotki.blockchain.accounts.eth

    # Provide empty list
    data = {'accounts': []}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Empty list of blockchain accounts to add was given',
    )

    # Provide invalid ETH account (more byes)
    data = {'accounts': ['0x554FFc77f4251a9fB3c0E3590a6a205f8d4e067d01']}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    msg = 'string 0x554FFc77f4251a9fB3c0E3590a6a205f8d4e067d01 is not a valid ETH address'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
    )

    # Provide invalid BTC account
    data = {'accounts': ['18ddjB7HWTaxzvTbLp1nWvaixU3U2oTZ1']}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )
    # Since validation depends on the querying of the balance for BTC the error only
    # is seen at addition and at removal another error is seen. But that's okay
    if method == 'put':
        msg = 'string 18ddjB7HWTaxzvTbLp1nWvaixU3U2oTZ1 is not a valid BTC address'
    else:
        msg = 'Tried to remove a non existing BTC account'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
    )

    # Provide not existing but valid ETH account for removal
    data = {'accounts': [make_ethereum_address()]}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to remove a non existing ETH account',
    )

    # Provide not existing but valid BTC account for removal
    data = {'accounts': ['18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2']}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to remove a non existing BTC account',
    )

    # Provide list with one valid and one invalid account and make sure that the
    # valid one is added/removed but we get an error for the invalid one
    if method == 'delete':
        # Account should be an existing account
        account = rotki.blockchain.accounts.eth[0]
    # else keep the new account to add

    data = {'accounts': ['142', account]}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_proper_response(response=response)
    assert '142 is not a valid ETH address' in response.json()['message']
    if method == 'put':
        assert checksummed_account in rotki.blockchain.accounts.eth
    else:
        assert checksummed_account not in rotki.blockchain.accounts.eth

    # Provide invalid type for accounts
    data = {'accounts': [15]}
    response = getattr(requests, method)(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
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
    rotki.blockchain.cache_ttl_secs = 0

    if query_balances_before_first_modification:
        # Also test by having balances queried before removing an account
        removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
        all_eth_accounts = [ethereum_accounts[1], ethereum_accounts[3]]
        eth_balances = ['3000000', '4000000']
        token_balances = {'RDN': ['0', '250000000']}
        setup = setup_balances(
            rotki,
            ethereum_accounts=all_eth_accounts,
            btc_accounts=btc_accounts,
            eth_balances=eth_balances,
            token_balances=token_balances,
        )
        with setup.blockchain_patch:
            response = requests.get(api_url_for(
                rotkehlchen_api_server,
                "blockchainbalancesresource",
            ))

    # Accounts to remove. Assure they are not in order to test that it does not affect anything
    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    all_eth_accounts = [ethereum_accounts[1], ethereum_accounts[3]]
    eth_balances = ['3000000', '4000000']
    token_balances = {'RDN': ['0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    # The application has started with 4 ethereum accounts. Remove two and see that balances match
    with setup.blockchain_patch:
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
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,  # All blockchain assets have not been queried yet
    )

    # Now try to query all balances to make sure the result is the stored
    with setup.blockchain_patch:
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

    # Now we will try to remove a BTC account. Setup the mocking infrastructure again
    all_btc_accounts = [UNIT_BTC_ADDRESS2]
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
        btc_balances=['600000000'],
    )
    # remove the new BTC account
    with setup.blockchain_patch:
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
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )

    # Now try to query all balances to make sure the result is also stored
    with setup.blockchain_patch:
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
    rotki.blockchain.cache_ttl_secs = 0

    # Test by having balances queried before removing an account
    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    all_eth_accounts = [ethereum_accounts[1], ethereum_accounts[3]]
    eth_balances = ['3000000', '4000000']
    token_balances = {'RDN': ['0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )
    with setup.blockchain_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ))

    # Accounts to remove. Assure they are not in order to test that it does not affect anything
    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    all_eth_accounts = [ethereum_accounts[1], ethereum_accounts[3]]
    eth_balances = ['3000000', '4000000']
    token_balances = {'RDN': ['0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    # The application has started with 4 ethereum accounts. Remove two and see that balances match
    with setup.blockchain_patch:
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
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,  # All blockchain assets have not been queried yet
    )

    # Now try to query all balances to make sure the result is the stored
    with setup.blockchain_patch:
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

    # Now we will try to remove a BTC account. Setup the mocking infrastructure again
    all_btc_accounts = [UNIT_BTC_ADDRESS2]
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
        btc_balances=['600000000'],
    )
    # remove the new BTC account
    with setup.blockchain_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS1], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_btc_balances_result(
        json_data=outcome,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )

    # Now try to query all balances to make sure the result is also stored
    with setup.blockchain_patch:
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
