import random

import pytest
import requests
from rotkehlchen.constants.assets import A_ETH

from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.types import ChainID, EvmTokenKind, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

TEST_ADDY = '0x9531C059098e3d194fF87FebB587aB07B30B1306'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_add_optimism_blockchain_account(rotkehlchen_api_server):
    """Test adding an optimism account when there is none in the db
    works as expected and that balances are returned and tokens are detected.
    """
    async_query = random.choice([False, True])
    optimism_chain_key = SupportedBlockchain.OPTIMISM.serialize()

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=optimism_chain_key,
        ),
        json={
            'accounts': [{'address': TEST_ADDY}],
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
        blockchain=optimism_chain_key,
    ))
    result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][optimism_chain_key][TEST_ADDY]
    assert 'liabilities' in account_balances
    asset_eth = account_balances['assets'][A_ETH.identifier]
    assert FVal(asset_eth['amount']) >= ZERO
    assert FVal(asset_eth['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_eth = result['totals']['assets'][A_ETH.identifier]
    assert FVal(total_eth['amount']) >= ZERO
    assert FVal(total_eth['usd_value']) >= ZERO

    now = ts_now()
    # now check that detecting tokens works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'detecttokensresource',
            blockchain=optimism_chain_key,
        ),
        json={
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(response)
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=600)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    assert result[TEST_ADDY]['last_update_timestamp'] >= now
    tokens = result[TEST_ADDY]['tokens']
    optimism_tokens = [
        evm_address_to_identifier(
            address=x,
            chain_id=ChainID.OPTIMISM,
            token_type=EvmTokenKind.ERC20,
        ) for x in [
            '0x4200000000000000000000000000000000000042',  # OP token
            '0x026B623Eb4AaDa7de37EF25256854f9235207178',  # spam token
            '0x15992f382D8c46d667B10DC8456dc36651Af1452',  # spam token
        ]
    ]
    assert set(tokens) == set(optimism_tokens)

    # and query balances again to see tokens also appear
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=optimism_chain_key,
        ),
        json={
            'ignore_cache': True,
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(response)
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=600)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][optimism_chain_key][TEST_ADDY]
    assert 'liabilities' in account_balances
    assert len(account_balances['assets']) == len(optimism_tokens) + 1
    for asset_id in (A_ETH.identifier, *optimism_tokens):
        asset = account_balances['assets'][asset_id]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    assert len(result['totals']['assets']) == len(optimism_tokens) + 1
    for asset_id in ('ETH', *optimism_tokens):
        asset = result['totals']['assets'][asset_id]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['usd_value']) >= ZERO
