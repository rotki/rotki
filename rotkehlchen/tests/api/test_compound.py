import random
import warnings as test_warnings
from contextlib import ExitStack
from typing import Any, Dict

import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances

TEST_ACC1 = '0x65304d6aff5096472519ca86a6a1fea31cb47Ced'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('async_query', [True, False])
def test_query_compound_balances(rotkehlchen_api_server, ethereum_accounts, async_query):
    """Check querying the compound balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "compoundbalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(UserWarning(f'Test account {TEST_ACC1} has no compound balances'))
        return

    lending = result[TEST_ACC1]['lending']
    for _, entry in lending.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    borrowing = result[TEST_ACC1]['borrowing']
    for _, entry in borrowing.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    rewards = result[TEST_ACC1]['rewards']
    if len(rewards) != 0:
        assert len(rewards) == 1
        assert 'COMP' in rewards


mocked_historical_prices: Dict[str, Any] = {}
mocked_current_prices: Dict[str, Any] = {}


TEST_ACC2 = '0x548B363F28234FE88a72D628c5350E37640429bC'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC2]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
def test_query_compound_history(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the compound histoy endpoint works. Uses real data"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)
    # Since this test is slow we don't run both async and sync in the same test run
    # Instead we randomly choose one. Eventually both cases will be covered.
    async_query = random.choice([True, False])

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "compoundhistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Timeout of 120 since this test can take a long time
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    # cc = json.dumps(result)
    # __import__("pdb").set_trace()
    assert len(result) == 1
