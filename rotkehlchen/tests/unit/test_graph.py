from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.ethereum.graph import Graph, format_query_indentation
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors.misc import RemoteError

TEST_URL_1 = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2'
TEST_QUERY_1 = (
    """
    tokenDayDatas
    (
        first: $limit,
    ) {{
        date
        token {{
            id
        }}
        priceUSD
    }}}}
    """
)


def test_exception_retries():
    """Test an exception raised by Client.execute() triggers the retry logic.
    """
    graph = Graph(TEST_URL_1)
    param_types = {'$limit': 'Int!'}
    param_values = {'limit': 1}
    querystr = format_query_indentation(TEST_QUERY_1.format())

    client = MagicMock()
    client.execute.side_effect = Exception('any message')

    backoff_factor_patch = patch(
        'rotkehlchen.chain.ethereum.graph.RETRY_BACKOFF_FACTOR',
        new=0,
    )
    client_patch = patch.object(graph, 'client', new=client)

    with ExitStack() as stack:
        stack.enter_context(backoff_factor_patch)
        stack.enter_context(client_patch)
        with pytest.raises(RemoteError) as e:
            graph.query(
                querystr=querystr,
                param_types=param_types,
                param_values=param_values,
            )

    assert client.execute.call_count == QUERY_RETRY_TIMES
    assert 'No retries left' in str(e.value)


def test_success_result():
    """Test a successful response returns result as expected and does not
    triggers the retry logic.
    """
    expected_result = {'schema': [{'data1'}, {'data2'}]}

    graph = Graph(TEST_URL_1)
    param_types = {'$limit': 'Int!'}
    param_values = {'limit': 1}
    querystr = format_query_indentation(TEST_QUERY_1.format())

    client = MagicMock()
    client.execute.return_value = expected_result

    backoff_factor_patch = patch(
        'rotkehlchen.chain.ethereum.graph.RETRY_BACKOFF_FACTOR',
        return_value=0,
    )
    client_patch = patch.object(graph, 'client', new=client)

    with ExitStack() as stack:
        stack.enter_context(backoff_factor_patch)
        stack.enter_context(client_patch)
        result = graph.query(
            querystr=querystr,
            param_types=param_types,
            param_values=param_values,
        )

    assert client.execute.call_count == 1
    assert result == expected_result
