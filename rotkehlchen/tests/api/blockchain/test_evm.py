from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import gevent
import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.avalanche import AVALANCHE_ACC1_AVAX_ADDR
from rotkehlchen.tests.utils.blockchain import setup_filter_active_evm_addresses_mock
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

ADDY = string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('avalanche_mock_data', [{'covalent_balances': 'test_balances/covalent_query_balances.json'}])  # noqa: E501
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


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('avalanche_mock_data', [{'covalent_balances': 'test_avalanche/covalent_query_transactions.json'}])  # noqa: E501
def test_add_multievm_accounts(rotkehlchen_api_server):
    """Test that adding accounts to multiple evm chains works fine

    TODO: Needs mocking with the data at the time of test writing
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    common_account = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    contract_account = '0x9008D19f58AAbD9eD0D60971565AA8510560ab41'

    # Add a tag
    tag1 = {
        'name': 'metamask',
        'description': 'Metamask stuff',
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

    with ExitStack() as stack:
        setup_filter_active_evm_addresses_mock(
            stack=stack,
            chains_aggregator=rotki.chains_aggregator,
            contract_addresses=[contract_account],
            avalanche_addresses=[common_account],
            optimism_addresses=[common_account],
        )

        # add two addresses for all evm chains, one with tag
        label = 'rotki account'
        request_data = {
            'accounts': [{
                'address': common_account,
                'label': label,
                'tags': ['metamask'],
            }, {
                'address': contract_account,
            }]}
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'evmaccountsresource',
        ), json=request_data)

    result = assert_proper_response_with_result(response)
    assert result == {
        'ETH': [common_account, contract_account],
        'AVAX': [common_account],
        'OPTIMISM': [common_account],
    }

    # Now get accounts to make sure they are all input correctly
    # TODO: As per the note in tags we may need to change this when tags
    # go per address/chain. We need to achieve a functionality where a
    # tag can either go to all accounts or a single chain/account. Right now
    # it only maps to an address so it mirrors to all.
    # Also perhaps we should have an all blockchains
    # version of this endpoint
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ))
    result = assert_proper_response_with_result(response)
    assert result == [
        {'address': contract_account, 'label': None, 'tags': None},
        {'address': common_account, 'label': label, 'tags': ['metamask']},
    ]
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='AVAX',
    ))
    result = assert_proper_response_with_result(response)
    assert result == [
        {'address': common_account, 'label': label, 'tags': ['metamask']},
    ]
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='OPTIMISM',
    ))
    result = assert_proper_response_with_result(response)
    assert result == [
        {'address': common_account, 'label': label, 'tags': ['metamask']},
    ]


@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address() for _ in range(3)]])
def test_evm_account_deletion_does_not_wait_for_pending_txn_queries(
        rotkehlchen_api_server,
        ethereum_accounts,
) -> None:
    """
    Test that if transactions for an address are being queried and removal is
    requested for that address, the transactions querying greenlets are killed
    and the account is subsequently deleted.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    task_manager = rotki.task_manager
    gevent.killall(rotki.task_manager.greenlet_manager.greenlets)
    task_manager.max_tasks_num = 2
    now = ts_now()
    task_manager.potential_tasks = [task_manager._maybe_query_evm_transactions]
    for address in ethereum_accounts[:-1]:  # leave last address to run via task manager
        task_manager.last_evm_tx_query_ts[(address, SupportedBlockchain.ETHEREUM)] = now
    task_manager_addy = ethereum_accounts[-1]
    api_addies = ethereum_accounts[:2].copy()

    def patch_single_query(**kwargs):  # pylint: disable=unused-argument
        while True:
            gevent.sleep(2)

    patch_obj = patch('rotkehlchen.chain.evm.transactions.EvmTransactions._get_transactions_for_range', side_effect=patch_single_query)  # noqa: E501
    with patch_obj:

        # schedule last address query through task manager
        task_manager.schedule()
        assert len(task_manager.running_greenlets) == 1
        greenlets = task_manager.running_greenlets[task_manager._maybe_query_evm_transactions]  # noqa: E501
        assert len(greenlets) == 1
        assert not greenlets[0].dead
        # query first two addresses via the api
        for idx, address in enumerate(api_addies):
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'evmtransactionsresource',
                ), json={
                    'async_query': True,
                    'only_cache': False,
                    'limit': 1000,
                    'accounts': [{'address': address, 'evm_chain': 'ethereum'}],
                    'evm_chain': 'ethereum',
                },
            )
            assert_ok_async_response(response)
            api_task_greenlets = rotkehlchen_api_server.rest_api.rotkehlchen.api_task_greenlets
            assert len(api_task_greenlets) == idx + 1  # the transactions fetching greenlets
            assert not api_task_greenlets[idx].dead

    # now delete one address from api task and 1 from periodic task manager and see it's immediate
    with gevent.Timeout(2):
        for address in (api_addies[0], task_manager_addy):
            response = requests.delete(
                api_url_for(
                    rotkehlchen_api_server,
                    'blockchainsaccountsresource',
                    blockchain='eth',
                ), json={
                    'async_query': False,
                    'accounts': [address],
                },
            )
            assert_proper_response(response)

    # Check that the 1 api greenlet and 1 task manager greenlet got killed
    assert len(api_task_greenlets) == 2
    assert api_task_greenlets[0].dead
    assert len(task_manager.running_greenlets) == 1
    assert task_manager.running_greenlets[task_manager._maybe_query_evm_transactions][0].dead  # noqa: E501
    assert not api_task_greenlets[1].dead, 'The other address api greenlet should still run'

    # retrieve ethereum accounts from the DB and see they are deleted
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
        assert accounts.eth == [api_addies[1]]
