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
    assert_proper_response_with_result,
)


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
def test_query_aave_balances(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "aavebalancesresource",
    ))
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
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
def test_query_aave_history(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data."""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "aavehistoryresource",
    ))
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
    assert events == expected_events


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
