from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from requests import HTTPError, Response

from rotkehlchen.chain.ethereum.graph import RETRY_STATUS_CODES, Graph, format_query_indentation
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import RemoteError

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


def test_error_response_not_retry():
    """Test failed request without a retry status code does not trigger the
    retry logic.

    The exception message raised mimics the one raised by gql v2 in the worst
    case scenario: when the response JSON does not have "data" nor "errors".
    The method `RequestsHTTPTransport.execute()` throws this exception.
    """
    graph = Graph(TEST_URL_1)
    param_types = {'$limit': 'Int!'}
    param_values = {'limit': 1}
    querystr = format_query_indentation(TEST_QUERY_1.format())

    # Mimic gql v2 error message
    client = MagicMock()
    response = Response()
    response.url = TEST_URL_1
    response.status_code = HTTPStatus.FORBIDDEN.value
    response.reason = 'whatever reason'
    error_msg = (
        f'{response.status_code} Server Error: {response.reason} for url: {response.url}'
    )
    client.execute.side_effect = HTTPError(error_msg, response=response)

    gql_client_patch = patch(
        'rotkehlchen.chain.ethereum.graph.Client',
        return_value=MagicMock(),
    )
    backoff_factor_patch = patch(
        'rotkehlchen.chain.ethereum.graph.RETRY_BACKOFF_FACTOR',
        return_value=0,
    )
    client_patch = patch.object(graph, 'client', new=client)

    with ExitStack() as stack:
        stack.enter_context(gql_client_patch)
        stack.enter_context(backoff_factor_patch)
        stack.enter_context(client_patch)
        with pytest.raises(RemoteError) as e:
            graph.query(
                querystr=querystr,
                param_types=param_types,
                param_values=param_values,
            )

    assert client.execute.call_count == 1
    assert 'Failed to query the graph for' in str(e.value)


@pytest.mark.parametrize('status_code', list(RETRY_STATUS_CODES))
def test_error_response_retry(status_code):
    """Test failed request with a retry status code triggers the retries logic.

    The exception message raised mimics the one raised by gql v2 in the worst
    case scenario: when the response JSON does not have "data" nor "errors".
    The method `RequestsHTTPTransport.execute()` is throws this exception.
    """
    graph = Graph(TEST_URL_1)
    param_types = {'$limit': 'Int!'}
    param_values = {'limit': 1}
    querystr = format_query_indentation(TEST_QUERY_1.format())

    # Mimic gql v2 error message
    client = MagicMock()
    response = Response()
    response.url = TEST_URL_1
    response.status_code = status_code.value
    response.reason = 'whatever reason'
    error_msg = (
        f'{response.status_code} Server Error: {response.reason} for url: {response.url}'
    )
    client.execute.side_effect = HTTPError(error_msg, response=response)

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
    """Test a successful response returns result as expected
    """
    expected_result = {"schema": [{"data1"}, {"data2"}]}

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
