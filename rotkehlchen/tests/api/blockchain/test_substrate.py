import random
from http import HTTPStatus

import pytest
import requests
from flaky import flaky

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.ens import ENS_BRUNO, ENS_BRUNO_KSM_ADDR
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_TEST_NODES,
    SUBSTRATE_ACC1_DOT_ADDR,
    SUBSTRATE_ACC1_KSM_ADDR,
    SUBSTRATE_ACC2_KSM_ADDR,
)
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ksm_blockchain_account_invalid(rotkehlchen_api_server):
    """Test adding an invalid Kusama blockchain account works as expected.
    """
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.value,
        ),
        json={'accounts': [{'address': SUBSTRATE_ACC1_DOT_ADDR}]},
    )

    assert_error_response(
        response=response,
        contained_in_msg=f'{SUBSTRATE_ACC1_DOT_ADDR} is not a valid kusama address',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@flaky(max_runs=3, min_passes=1)  # Kusama open nodes some times time out
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_add_ksm_blockchain_account(rotkehlchen_api_server):
    """Test adding a Kusama blockchain account when there is none in the db
    works as expected, by triggering the logic that attempts to connect to the
    nodes.
    """
    async_query = random.choice([False, True])

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.value,
        ),
        json={
            'accounts': [{'address': SUBSTRATE_ACC1_KSM_ADDR}],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id)
    else:
        assert_proper_response(response)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain=SupportedBlockchain.KUSAMA.value,
    ))
    result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account']['KSM'][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO


@flaky(max_runs=3, min_passes=1)  # Kusama open nodes some times time out
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, SUBSTRATE_ACC2_KSM_ADDR]])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_remove_ksm_blockchain_account(rotkehlchen_api_server):
    """Test removing a Kusama blockchain account works as expected by returning
    only the balances of the other Kusama accounts.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])

    requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))  # to populate balances
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.value,
        ),
        json={
            'accounts': [SUBSTRATE_ACC2_KSM_ADDR],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    # Check per account
    assert SUBSTRATE_ACC2_KSM_ADDR not in result['per_account']['KSM']
    account_balances = result['per_account']['KSM'][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO

    # Also make sure it's removed from the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        db_accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert db_accounts.ksm[0] == SUBSTRATE_ACC1_KSM_ADDR


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ksm_blockchain_account_invalid_ens_domain(rotkehlchen_api_server):
    """Test adding an invalid Kusama blockchain account via ENS domain works as
    expected.
    """
    invalid_ens_domain = 'craigwright.eth'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.value,
        ),
        json={'accounts': [{'address': invalid_ens_domain}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg=(
            f'Given ENS address {invalid_ens_domain} could not be resolved for kusama'
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )


@flaky(max_runs=3, min_passes=1)  # Kusama open nodes some times time out
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_add_ksm_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test adding a Kusama blockchain account via ENS domain when there is none
    in the db works as expected"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])
    # check that we are not connected to the nodes in the beginning
    assert rotki.chains_aggregator.kusama.available_nodes_call_order == []
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.value,
        ),
        json={
            'accounts': [{'address': ENS_BRUNO}],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert result == [ENS_BRUNO_KSM_ADDR]
    assert set(rotki.chains_aggregator.accounts.ksm) == {ENS_BRUNO_KSM_ADDR}
    # check that we did connect to the nodes after account addition
    assert rotki.chains_aggregator.kusama.available_nodes_call_order != []


@flaky(max_runs=3, min_passes=1)  # Kusama open nodes some times time out
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, ENS_BRUNO_KSM_ADDR]])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_remove_ksm_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test removing a Kusama blockchain account via ENS domain works as expected
    Also tests Totals calculation."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.value,
        ),
        json={
            'accounts': [ENS_BRUNO],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id)
    else:
        assert_proper_response(response)

    assert set(rotki.chains_aggregator.accounts.ksm) == {SUBSTRATE_ACC1_KSM_ADDR}

    # Also make sure it's removed from the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        db_accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert db_accounts.ksm[0] == SUBSTRATE_ACC1_KSM_ADDR
