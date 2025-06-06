import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    wait_for_async_task,
    wait_for_async_tasks,
)


@pytest.mark.skipif(True, reason='This is for profiling only. Comment out to run')
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x7277F7849966426d345D8F6B9AFD1d3d89183083',  # kelsos.eth
    '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',  # yabir.eth
]])
@pytest.mark.parametrize('should_mock_price_queries', [False])
@pytest.mark.parametrize('have_decoders', [True])
def test_query_decode_history_profiling(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Profile querying transactions and decoding them for a number of addresses

    For how to see the flamegraph of this check:
    https://docs.rotki.com/contribution-guides/code-profiling.html#python
    """
    task_ids = []
    for account in ethereum_accounts:  # Query transactions
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'blockchaintransactionsresource',
            ), json={
                'async_query': True,
                'accounts': [{'address': account, 'blockchain': 'ethereum'}],
            },
        )
        task_ids.append(assert_ok_async_response(response))

    wait_for_async_tasks(rotkehlchen_api_server, task_ids=task_ids, timeout=600)

    response = requests.post(  # Decode all transactions
        api_url_for(
            rotkehlchen_api_server,
            'evmpendingtransactionsdecodingresource',
        ), json={'async_query': True},
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert outcome['message'] == ''
