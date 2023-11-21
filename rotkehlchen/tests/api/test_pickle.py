import random

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)

PICKLE_ADDR = '0x5c4D8CEE7dE74E31cE69E76276d862180545c307'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[PICKLE_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['pickle_finance']])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.freeze_time('2023-11-21 21:00:00 GMT')
def test_pickle_dill(
        rotkehlchen_api_server,
        inquirer,  # pylint: disable=unused-argument
):
    """Test that we can get the status of the trove and the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'pickledillresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert PICKLE_ADDR in result
    data = result[PICKLE_ADDR]
    assert 'locked_amount' in data
    assert 'locked_until' in data
    assert 'pending_rewards' in data
