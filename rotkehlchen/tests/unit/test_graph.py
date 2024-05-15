from contextlib import ExitStack
from typing import Final
from unittest.mock import MagicMock, patch

import pytest
from gql.transport.exceptions import TransportQueryError

from rotkehlchen.chain.ethereum.graph import Graph, format_query_indentation
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError

UNISWAP_GRAPH_ID: Final = 'A3Np3RQbaBA6oKJgiwDJeo5T3zrYfGHPWFYayMwtNDum'
TEST_QUERY_1: Final = (
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


def test_exception_retries(database, add_subgraph_api_key):  # pylint: disable=unused-argument
    """Test an exception raised by Client.execute() triggers the retry logic.
    """
    graph = Graph(subgraph_id=UNISWAP_GRAPH_ID, database=database, label='uniswap')
    param_types = {'$limit': 'Int!'}
    param_values = {'limit': 1}
    querystr = format_query_indentation(TEST_QUERY_1.format())

    client = MagicMock()
    client.execute.side_effect = TransportQueryError('any message')

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

    assert client.execute.call_count == CachedSettings().get_query_retry_limit()
    assert 'No retries left' in str(e.value)


def test_success_result(database, add_subgraph_api_key):  # pylint: disable=unused-argument
    """Test a successful response returns result as expected and does not
    triggers the retry logic.
    """
    expected_result = {'schema': [{'data1'}, {'data2'}]}

    graph = Graph(subgraph_id=UNISWAP_GRAPH_ID, database=database, label='uniswap')
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
