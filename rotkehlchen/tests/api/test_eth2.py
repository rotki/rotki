import random
from contextlib import ExitStack

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
def test_query_eth2_info(rotkehlchen_api_server, ethereum_accounts):
    """This test uses real data and queries the eth2 deposit contract logs"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=[],
        original_queries=['logs', 'transactions', 'blocknobytime', 'beaconchain'],
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakedetailsresource',
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
            )
            assert outcome['message'] == ''
            details = outcome['result']
        else:
            details = assert_proper_response_with_result(response)

    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakedepositsresource',
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
            )
            assert outcome['message'] == ''
            deposits = outcome['result']
        else:
            deposits = assert_proper_response_with_result(response)

    expected_pubkey = '0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'  # noqa: E501
    assert deposits[0] == {
        'from_address': '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
        'log_index': 22,
        'pubkey': expected_pubkey,
        'timestamp': 1604506685,
        'tx_hash': '0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
        'deposit_index': 9,
        'value': {'amount': '32', 'usd_value': '32'},
        'withdrawal_credentials': '0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
    }
    assert FVal(details[0]['balance']['amount']) >= ZERO
    assert FVal(details[0]['balance']['usd_value']) >= ZERO
    assert details[0]['eth1_depositor'] == '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397'  # noqa: E501
    assert details[0]['index'] == 9
    assert details[0]['public_key'] == expected_pubkey
    for duration in ('1d', '1w', '1m', '1y'):
        performance = details[0][f'performance_{duration}']
        # Can't assert for positive since they may go offline for a day and the test will fail
        # https://twitter.com/LefterisJP/status/1361091757274972160
        assert FVal(performance['amount']) is not None
        assert FVal(performance['usd_value']) is not None
