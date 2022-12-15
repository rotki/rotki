from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.avalanche import AVALANCHE_ACC1_AVAX_ADDR
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_same_evm_account_for_multiple_chains(rotkehlchen_api_server):
    """Test adding an Avalanche blockchain account when the same account is input
    in Ethereum works fine
    """
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=[AVALANCHE_ACC1_AVAX_ADDR],
        btc_accounts=None,
        eth_balances=['10000000000'],
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'blockchainsaccountsresource',
                blockchain=SupportedBlockchain.ETHEREUM.value,
            ),
            json={
                'accounts': [{'address': AVALANCHE_ACC1_AVAX_ADDR}],
            },
        )
        assert_proper_response(response)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'blockchainsaccountsresource',
                blockchain=SupportedBlockchain.AVALANCHE.value,
            ),
            json={
                'accounts': [{'address': AVALANCHE_ACC1_AVAX_ADDR}],
            },
        )
        assert_proper_response(response)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ))
        result = assert_proper_response_with_result(response)

    for chain in ('ETH', 'AVAX'):
        # Check per account
        account_balances = result['per_account'][chain][AVALANCHE_ACC1_AVAX_ADDR]
        assert 'liabilities' in account_balances
        asset_token = account_balances['assets'][chain]
        assert FVal(asset_token['amount']) >= ZERO
        assert FVal(asset_token['usd_value']) >= ZERO

        # Check totals
        assert 'liabilities' in result['totals']
        total_token = result['totals']['assets'][chain]
        assert FVal(total_token['amount']) >= ZERO
        assert FVal(total_token['usd_value']) >= ZERO


@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_deleting_ens_account_works(rotkehlchen_api_server):
    """Test that deleting an ENS eth account can be handled properly

    This test mocks all etherscan queries apart from the ENS ones
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    request_data = {'accounts': ['rotki.eth']}
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_proper_response(response)
    assert rotki.chains_aggregator.accounts.eth == []

    request_data = {'accounts': ['ishouldnotexistforrealz.eth']}
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS address ishouldnotexistforrealz.eth could not be resolved',
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_non_checksummed_eth_account_works(rotkehlchen_api_server):
    """Test that adding a non checksummed eth account can be handled properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    account = '0x7bd904a3db59fa3879bd4c246303e6ef3ac3a4c6'
    new_eth_accounts = [to_checksum_address(account)]
    eth_balances = ['1000000']
    setup = setup_balances(
        rotki,
        ethereum_accounts=new_eth_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=None,
    )
    request_data = {'accounts': [{'address': account}]}
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json=request_data)
    assert_proper_response(response)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_editing_ens_account_works(rotkehlchen_api_server):
    """Test that adding an ENS eth account can be handled properly

    This test mocks all etherscan queries apart from the ENS ones
    """
    resolved_account = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Add an account and see it resolves
    request_data = {'accounts': [{'address': 'rotki.eth'}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)

    result = assert_proper_response_with_result(response)
    assert result == [resolved_account]
    assert rotki.chains_aggregator.accounts.eth[-1] == resolved_account

    # Add an unresolvable account and see it errors
    request_data = {'accounts': [{'address': 'ishouldnotexistforrealz.eth'}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS address ishouldnotexistforrealz.eth could not be resolved',
    )

    # Edit the resolvable account
    label = 'foo'
    request_data = {'accounts': [{'address': 'rotki.eth', 'label': label}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    result = assert_proper_response_with_result(response)[0]
    assert result['address'] == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    assert result['label'] == label

    # Edit an unresolvable account
    label = 'foo'
    request_data = {'accounts': [{'address': 'ishouldnotexistforrealz.eth', 'label': label}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS address ishouldnotexistforrealz.eth could not be resolved',
    )
