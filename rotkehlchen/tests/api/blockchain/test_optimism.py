import random

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
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


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_optimism_blockchain_account(rotkehlchen_api_server):
    """Test adding an optimism account when there is none in the db
    works as expected and that balances are returned and tokens are detected.

    TODO: Probably should mock this at some point. Atm just using
    rotki's account in optimism
    """
    async_query = random.choice([False, True])

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.OPTIMISM.value,
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
        blockchain=SupportedBlockchain.OPTIMISM.value,
    ))
    result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account']['OPTIMISM'][TEST_ADDY]
    assert 'liabilities' in account_balances
    asset_eth = account_balances['assets']['ETH']
    assert FVal(asset_eth['amount']) >= ZERO
    assert FVal(asset_eth['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_eth = result['totals']['assets']['ETH']
    assert FVal(total_eth['amount']) >= ZERO
    assert FVal(total_eth['usd_value']) >= ZERO

    now = ts_now()
    # now check that detecting tokens works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'detecttokensresource',
            blockchain=SupportedBlockchain.OPTIMISM.value,
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
    optimism_op = evm_address_to_identifier(
        address='0x4200000000000000000000000000000000000042',
        chain_id=ChainID.OPTIMISM,
        token_type=EvmTokenKind.ERC20,
    )
    optimism_aoptusdc = evm_address_to_identifier(
        address='0x625E7708f30cA75bfd92586e17077590C60eb4cD',
        chain_id=ChainID.OPTIMISM,
        token_type=EvmTokenKind.ERC20,
    )
    assert tokens == [optimism_op, optimism_aoptusdc]

    # and query balances again to see tokens also appear
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=SupportedBlockchain.OPTIMISM.value,
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
    account_balances = result['per_account']['OPTIMISM'][TEST_ADDY]
    assert 'liabilities' in account_balances
    assert len(account_balances['assets']) == 3
    for asset_id in ('ETH', optimism_op, optimism_aoptusdc):
        asset = account_balances['assets'][asset_id]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    assert len(result['totals']['assets']) == 3
    for asset_id in ('ETH', optimism_op, optimism_aoptusdc):
        asset = result['totals']['assets'][asset_id]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['usd_value']) >= ZERO
