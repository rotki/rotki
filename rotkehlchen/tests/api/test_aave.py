import random
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.aave import (
    aave_mocked_current_prices,
    aave_mocked_historical_prices,
    expected_aave_test_events,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('async_query', [True, False])
def test_query_aave_balances(rotkehlchen_api_server, ethereum_accounts, async_query):
    """Check querying the aave balances endpoint works. Uses real data.

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
            "aavebalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 1
    # Assume no borrowing in this account and check that lending response has proper format
    assert result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']['borrowing'] == {}
    result = result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']['lending']
    for _, entry in result.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_aave_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "aavebalancesresource",
        ))
    assert_error_response(
        response=response,
        contained_in_msg='aave module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_aave_balances_async_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "aavebalancesresource",
        ), json={'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)

    assert outcome['result'] is None
    assert outcome['message'] == 'aave module is not activated'


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
def test_query_aave_history(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data.

    Since this actually queries real blockchain data for aave it is a very slow test
    due to the sheer amount of log queries
    """
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
            "aavehistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Timeout of 120 since this test can take a long time
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']) == 2
    events = result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']['events']
    total_earned = result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']['total_earned']
    assert len(total_earned) == 1
    assert len(total_earned['aDAI']) == 2
    assert FVal(total_earned['aDAI']['amount']) >= FVal('24.207179802347627414')
    assert FVal(total_earned['aDAI']['usd_value']) >= FVal('24.580592532348742989192')
    expected_events = process_result_list(expected_aave_test_events)
    assert len(events) >= 12
    assert events[:12] == expected_events


@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_query_aave_history_non_premium(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "aavehistoryresource",
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.CONFLICT,
    )
