import random
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.substrate.types import KusamaNodeName
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.constants.assets import A_KSM
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.ens import ENS_BRUNO, ENS_BRUNO_KSM_ADDR
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_TEST_RPC_ENDPOINT,
    SUBSTRATE_ACC1_DOT_ADDR,
    SUBSTRATE_ACC1_KSM_ADDR,
    SUBSTRATE_ACC2_KSM_ADDR,
    wait_until_all_substrate_nodes_connected,
)
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ksm_blockchain_account_invalid(rotkehlchen_api_server: 'APIServer') -> None:
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [(KusamaNodeName.OWN,)])
@pytest.mark.parametrize('ksm_rpc_endpoint', [KUSAMA_TEST_RPC_ENDPOINT], ids=['KUSAMA_TEST_RPC_ENDPOINT'])  # setting ids to rename the argument to be processed by vcr since its value can contain characters that are illegal in windows. Affects all other similar fixtures in this file # noqa: E501
@pytest.mark.parametrize('network_mocking', [False])
def test_add_ksm_blockchain_account(
        rotkehlchen_api_server: 'APIServer',
        kusama_manager_connect_at_start: Sequence[KusamaNodeName],
) -> None:
    """Test adding a Kusama blockchain account when there is none in the db
    works as expected, by triggering the logic that attempts to connect to the
    nodes.
    """
    ksm_manager = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.kusama
    ksm_manager.attempt_connections()  # since we start with no accounts we need to force connections here  # noqa: E501
    wait_until_all_substrate_nodes_connected(
        substrate_manager_connect_at_start=kusama_manager_connect_at_start,
        substrate_manager=ksm_manager,
    )
    kusama_chain_key = SupportedBlockchain.KUSAMA.serialize()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=kusama_chain_key,
        ),
        json={
            'accounts': [{'address': SUBSTRATE_ACC1_KSM_ADDR}],
            'async_query': True,
        },
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task(rotkehlchen_api_server, task_id)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain=kusama_chain_key,
    ))
    result = assert_proper_sync_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][kusama_chain_key][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, SUBSTRATE_ACC2_KSM_ADDR]])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [(KusamaNodeName.OWN,)])
@pytest.mark.parametrize('ksm_rpc_endpoint', [KUSAMA_TEST_RPC_ENDPOINT], ids=['KUSAMA_TEST_RPC_ENDPOINT'])  # noqa: E501
@pytest.mark.parametrize('network_mocking', [False])
def test_remove_ksm_blockchain_account(rotkehlchen_api_server: 'APIServer') -> None:
    """Test removing a Kusama blockchain account works as expected by returning
    only the balances of the other Kusama accounts.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    kusama_chain_key = SupportedBlockchain.KUSAMA.serialize()
    requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))  # to populate balances
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=kusama_chain_key,
        ),
        json={
            'accounts': [SUBSTRATE_ACC2_KSM_ADDR],
            'async_query': False,
        },
    )
    result = assert_proper_sync_response_with_result(response)

    # Check per account
    assert SUBSTRATE_ACC2_KSM_ADDR not in result['per_account'][kusama_chain_key]
    account_balances = result['per_account'][kusama_chain_key][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO

    # Also make sure it's removed from the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        db_accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert db_accounts.ksm[0] == SUBSTRATE_ACC1_KSM_ADDR


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ksm_blockchain_account_invalid_ens_domain(rotkehlchen_api_server: 'APIServer') -> None:  # noqa: E501
    """Test adding an invalid Kusama blockchain account via ENS domain works as
    expected.
    """
    invalid_ens_domain = 'craigwright.eth'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.serialize(),
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [(KusamaNodeName.OWN,)])
@pytest.mark.parametrize('ksm_rpc_endpoint', [KUSAMA_TEST_RPC_ENDPOINT], ids=['KUSAMA_TEST_RPC_ENDPOINT'])  # noqa: E501
@pytest.mark.parametrize('network_mocking', [False])
def test_add_ksm_blockchain_account_ens_domain(rotkehlchen_api_server: 'APIServer') -> None:
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
            blockchain=SupportedBlockchain.KUSAMA.serialize(),
        ),
        json={
            'accounts': [{'address': ENS_BRUNO}],
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert result == [ENS_BRUNO_KSM_ADDR]
    assert set(rotki.chains_aggregator.accounts.ksm) == {ENS_BRUNO_KSM_ADDR}
    # check that we did connect to the nodes after account addition
    assert rotki.chains_aggregator.kusama.available_nodes_call_order != []


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, ENS_BRUNO_KSM_ADDR]])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [(KusamaNodeName.OWN,)])
@pytest.mark.parametrize('ksm_rpc_endpoint', [KUSAMA_TEST_RPC_ENDPOINT], ids=['KUSAMA_TEST_RPC_ENDPOINT'])  # noqa: E501
@pytest.mark.parametrize('network_mocking', [False])
def test_remove_ksm_blockchain_account_ens_domain(rotkehlchen_api_server: 'APIServer') -> None:
    """Test removing a Kusama blockchain account via ENS domain works as expected
    Also tests Totals calculation."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.KUSAMA.serialize(),
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
