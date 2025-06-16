import random
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.constants.assets import A_AVAX
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
from rotkehlchen.tests.utils.avalanche import AVALANCHE_ACC1_AVAX_ADDR, AVALANCHE_ACC2_AVAX_ADDR
from rotkehlchen.tests.utils.substrate import SUBSTRATE_ACC1_DOT_ADDR
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_avax_blockchain_account_invalid(rotkehlchen_api_server: 'APIServer') -> None:
    """Test adding an invalid Avalanche blockchain account works as expected.
    """
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.AVALANCHE.value,
        ),
        json={'accounts': [{'address': SUBSTRATE_ACC1_DOT_ADDR}]},
    )

    assert_error_response(
        response=response,
        contained_in_msg=f'{SUBSTRATE_ACC1_DOT_ADDR} is not an evm address',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_avax_blockchain_account(rotkehlchen_api_server: 'APIServer') -> None:
    """Test adding an Avalanche blockchain account when there is none in the db
    works as expected."""
    async_query = random.choice([False, True])

    avalanche_chain_key = SupportedBlockchain.AVALANCHE.serialize()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=avalanche_chain_key,
        ),
        json={
            'accounts': [{'address': AVALANCHE_ACC1_AVAX_ADDR}],
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
        blockchain=avalanche_chain_key,
    ))
    result = assert_proper_sync_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][avalanche_chain_key][AVALANCHE_ACC1_AVAX_ADDR]
    assert 'liabilities' in account_balances
    asset_avax = account_balances['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_avax['amount']) >= ZERO
    assert FVal(asset_avax['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_avax = result['totals']['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_avax['amount']) >= ZERO
    assert FVal(total_avax['usd_value']) >= ZERO


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('avax_accounts', [[AVALANCHE_ACC1_AVAX_ADDR, AVALANCHE_ACC2_AVAX_ADDR]])
def test_remove_avax_blockchain_account(rotkehlchen_api_server: 'APIServer') -> None:
    """Test removing an Avalanche blockchain account works as expected"""
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
            blockchain=SupportedBlockchain.AVALANCHE.serialize(),
        ),
        json={
            'accounts': [AVALANCHE_ACC2_AVAX_ADDR],
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    # Check per account
    avax_chain_key = SupportedBlockchain.AVALANCHE.serialize()
    assert AVALANCHE_ACC2_AVAX_ADDR not in result['per_account'][avax_chain_key]
    account_balances = result['per_account'][avax_chain_key][AVALANCHE_ACC1_AVAX_ADDR]
    assert 'liabilities' in account_balances
    asset_avax = account_balances['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_avax['amount']) >= ZERO
    assert FVal(asset_avax['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_avax = result['totals']['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_avax['amount']) >= ZERO
    assert FVal(total_avax['usd_value']) >= ZERO
    # Also make sure it's removed from the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        db_accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert db_accounts.avax[0] == AVALANCHE_ACC1_AVAX_ADDR
