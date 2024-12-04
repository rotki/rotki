import random

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result

PICKLE_ADDR = '0x5c4D8CEE7dE74E31cE69E76276d862180545c307'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[PICKLE_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['pickle_finance']])
@pytest.mark.freeze_time('2023-11-21 21:00:00 GMT')
def test_pickle_dill(rotkehlchen_api_server: APIServer) -> None:
    """Test that we can get the status of the trove and the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'pickledillresource',
    ), json={'async_query': async_query})
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert PICKLE_ADDR in result
    data = result[PICKLE_ADDR]
    assert 'locked_amount' in data
    assert 'locked_until' in data
    assert 'pending_rewards' in data
