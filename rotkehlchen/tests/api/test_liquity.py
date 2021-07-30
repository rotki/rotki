import pytest
import random

import requests

from rotkehlchen.chain.ethereum.modules.liquity.trove import Liquity
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.tests.utils.api import api_url_for, assert_ok_async_response

LQTY_ADDR = string_to_ethereum_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')

@pytest.mark.parametrize('ethereum_accounts', [[LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_trove_position(
        rotkehlchen_api_server,
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
):
    """Test DSR history is correctly queried

    This (and the async version) is a very hard to maintain test due to mocking
    everything.

    TODO: Perhaps change it to querying etherscan/chain until a given block for a
    given DSR account and check that until then all data match.
    """
    async_query = random.choice([False])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "liquitytroves",
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        print(response.text)

    assert False

@pytest.mark.parametrize('ethereum_accounts', [[LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_trove_events(
        rotkehlchen_api_server,
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
):
    """Test DSR history is correctly queried

    This (and the async version) is a very hard to maintain test due to mocking
    everything.

    TODO: Perhaps change it to querying etherscan/chain until a given block for a
    given DSR account and check that until then all data match.
    """
    async_query = random.choice([False])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "liquitytroveshistory",
    ), json={'async_query': async_query, 'from_timestamp': 0, 'to_timestamp': 1628026696, 'reset_db_data': False})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        print(response.text)

    assert False