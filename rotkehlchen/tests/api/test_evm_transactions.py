import json
import random
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xb8553D9ee35dd23BB96fbd679E651B929821969B',
]])
@pytest.mark.parametrize('optimism_accounts', [[
    '0xb8553D9ee35dd23BB96fbd679E651B929821969B',
]])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.5)])
def test_query_transactions(rotkehlchen_api_server: 'APIServer'):
    """Test that querying the evm transactions endpoint for an address with
    transactions in multiple chains works fine.

    This test uses real data.

    TODO: Mock network here. Need to mock transaction query for both mainnet and optimism etherscan
    """
    async_query = random.choice([False, True])
    # Ask for all evm transactions (test addy has both optimism and mainnet)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    expected_file = Path(__file__).resolve().parent.parent / 'data' / 'expected' / 'test_evm_transactions-test_query_transactions.json'  # noqa: E501
    with open(expected_file) as f:
        expected_data = json.load(f)

    assert result == expected_data
