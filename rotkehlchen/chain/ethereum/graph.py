import json
import logging
import re
from http import HTTPStatus
from typing import Any

import gevent
import requests
from gql import Client, gql
from gql.transport.exceptions import TransportError, TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport
from graphql.error import GraphQLError

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


GRAPH_QUERY_LIMIT = 1000
GRAPH_QUERY_SKIP_LIMIT = 5000
RE_MULTIPLE_WHITESPACE = re.compile(r'\s+')
RETRY_BACKOFF_FACTOR = 0.2
SUBGRAPH_REMOTE_ERROR_MSG = (
    'Failed to request the {protocol} subgraph due to {error_msg}. '
    'All the deposits and withdrawals history queries are not functioning until this is fixed. '
    "Probably will get fixed with time. If not report it to rotki's support channel"
)


def format_query_indentation(querystr: str) -> str:
    """Format a triple quote and indented GraphQL query by:
    - Removing returns
    - Replacing multiple inner whitespaces with one
    - Removing leading and trailing whitespaces
    """
    return RE_MULTIPLE_WHITESPACE.sub(' ', querystr).strip()


class Graph:

    def __init__(self, url: str) -> None:
        """
        - May raise requests.RequestException if there is a problem connecting to the subgraph"""
        transport = RequestsHTTPTransport(url=url)
        try:
            self.client = Client(transport=transport, fetch_schema_from_transport=False)
        except (requests.exceptions.RequestException) as e:
            raise RemoteError(f'Failed to connect to the graph at {url} due to {e!s}') from e

    def query(
            self,
            querystr: str,
            param_types: dict[str, Any] | None = None,
            param_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: If there is a problem querying the subgraph and there
        are no retries left.
        """
        prefix = ''
        if param_types is not None:
            prefix = 'query '
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
            prefix += '{'

        querystr = prefix + querystr  # https://github.com/astral-sh/ruff/issues/10925 # noqa: E501 PLR6104
        log.debug(f'Querying The Graph for {querystr}')

        retries_left = CachedSettings().get_query_retry_limit()
        retry_limit = CachedSettings().get_query_retry_limit()
        while retries_left > 0:
            try:
                result = self.client.execute(gql(querystr), variable_values=param_values)
            except (TransportServerError, TransportQueryError) as e:
                # https://gql.readthedocs.io/en/latest/advanced/error_handling.html
                # Kind of guessing here ... these may be the only ones we can backoff for
                base_msg = f'The Graph query to {querystr} failed due to {e}'
                retries_left -= 1
                if (  # check if we should retry
                        retries_left != 0 and (
                            (isinstance(e, TransportServerError) and e.code == HTTPStatus.TOO_MANY_REQUESTS) or  # noqa: E501
                            isinstance(e, TransportQueryError)
                        )
                ):
                    sleep_seconds = RETRY_BACKOFF_FACTOR * pow(2, retry_limit - retries_left)
                    retry_msg = (
                        f'Retrying query after {sleep_seconds} seconds. '
                        f'Retries left: {retries_left}.'
                    )
                    log.error(f'{base_msg}. {retry_msg}')
                    gevent.sleep(sleep_seconds)
                else:
                    raise RemoteError(f'{base_msg}. No retries left.') from e

            except (GraphQLError, TransportError) as e:
                raise RemoteError(f'Failed to query the graph for {querystr} due to {e}') from e
            else:
                break

        log.debug('Got result from The Graph query')
        return result
