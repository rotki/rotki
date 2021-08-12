import pytest
import random

import requests

from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)

LQTY_ADDR = string_to_ethereum_address('0x063c26fF1592688B73d8e2A18BA4C23654e2792E')


@pytest.mark.parametrize('ethereum_accounts', [[LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_trove_position(
        rotkehlchen_api_server,
        inquirer,  # pylint: disable=unused-argument
):
    """Test that we can get the status of the trove and the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "liquitytroves",
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert LQTY_ADDR in result
    trove_data = result[LQTY_ADDR]['trove']
    assert 'collateral' in trove_data
    assert 'debt' in trove_data
    assert 'collateralization_ratio' in trove_data
    assert 'liquidation_price' in trove_data
    assert trove_data['active'] is True
    stake_data = result[LQTY_ADDR]['stake']
    assert 'amount' in stake_data and float(stake_data['amount']) > 0


@pytest.mark.parametrize('ethereum_accounts', [[LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_trove_events(rotkehlchen_api_server):
    """Test that Trove events and Stake events are correctly queried"""
    async_query = random.choice([True, False])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "liquitytroveshistory",
        ), json={
            'async_query': async_query,
            'from_timestamp': 0,
            'to_timestamp': 1628026696,
            'reset_db_data': False,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert LQTY_ADDR in result
    assert {'trove', 'stake'} == set(result[LQTY_ADDR].keys())
    assert len(result[LQTY_ADDR]['trove']) == 2
    assert len(result[LQTY_ADDR]['stake']) == 1
    trove_action = result[LQTY_ADDR]['trove'][0]
    tx_id = '0xc8ad6f6ec244a93e1d66e60d1eab2ff2cb9de1f3a1f45c7bb4e9d2f720254137'
    assert trove_action['tx'] == tx_id
    assert trove_action['timestamp'] == 1627818194
    assert trove_action['kind'] == 'trove'
    assert trove_action['debt_delta'] == trove_action['debt_after']
    assert trove_action['debt_delta'] == "6029.001719188487125"
    assert trove_action['trove_operation'] == 'Open Trove'
    assert trove_action['collateral_after'] == trove_action['collateral_delta']
    assert trove_action['collateral_delta'] == "3.5"
    trove_stake = result[LQTY_ADDR]['stake'][0]
    tx_id = '0xe527749c76a3af56d86c97a8f8f8ce07e191721e9e16a0f62a228f8a8ef6d295'
    assert trove_stake['tx'] == tx_id
    assert trove_stake['timestamp'] == 1627827057
    assert trove_stake['kind'] == 'stake'
    assert trove_stake['stake_after'] == trove_stake['stake_change']
    assert trove_stake['stake_after'] == "177.02"
    assert trove_stake['stake_operation'] == 'Stake Created'
