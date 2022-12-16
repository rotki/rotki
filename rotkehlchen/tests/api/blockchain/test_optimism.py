import random

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.types import SupportedBlockchain

TEST_ADDY = '0x9531C059098e3d194fF87FebB587aB07B30B1306'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_optimism_blockchain_account(rotkehlchen_api_server):
    """Test adding an optimism account when there is none in the db
    works as expected."""
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
    account_balances = result['per_account']['OP'][TEST_ADDY]
    assert 'liabilities' in account_balances
    asset_avax = account_balances['assets']['OP']
    assert FVal(asset_avax['amount']) >= ZERO
    assert FVal(asset_avax['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_avax = result['totals']['assets']['OP']
    assert FVal(total_avax['amount']) >= ZERO
    assert FVal(total_avax['usd_value']) >= ZERO
