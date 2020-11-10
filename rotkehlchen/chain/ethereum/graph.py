import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from typing_extensions import Literal

from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import ChecksumEthAddress, Timestamp

log = logging.getLogger(__name__)


GRAPH_QUERY_LIMIT = 1000
RE_MULTIPLE_WHITESPACE = re.compile(r'\s+')


def format_query_indentation(querystr: str) -> str:
    """Format a triple quote and indented GraphQL query by:
    - Removing returns
    - Replacing multiple inner whitespaces with one
    - Removing leading and trailing whitespaces
    """
    return RE_MULTIPLE_WHITESPACE.sub(' ', querystr).strip()


def get_common_params(
        from_ts: Timestamp,
        to_ts: Timestamp,
        address: ChecksumEthAddress,
        address_type: Literal['Bytes!', 'String!'] = 'Bytes!',
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    param_types = {
        '$start_ts': 'Int!',
        '$end_ts': 'Int!',
        '$address': address_type,
    }
    param_values = {
        'start_ts': from_ts,
        'end_ts': to_ts,
        'address': address.lower(),
    }
    return param_types, param_values


class Graph():

    def __init__(self, url: str) -> None:
        """
        - May raise requests.RequestException if there is a problem connecting to the subgraph"""
        transport = RequestsHTTPTransport(url=url)
        try:
            self.client = Client(transport=transport, fetch_schema_from_transport=True)
        except (requests.exceptions.RequestException) as e:
            raise RemoteError(f'Failed to connect to the graph at {url} due to {str(e)}') from e

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]] = None,
            param_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: If there is a problem querying the subgraph
        """
        prefix = ''
        if param_types is not None:
            prefix = 'query '
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
            prefix += '{'

        querystr = prefix + querystr
        log.debug(f'Querying The Graph for {querystr}')
        try:
            result = self.client.execute(gql(querystr), variable_values=param_values)
        except (requests.exceptions.RequestException, Exception) as e:
            raise RemoteError(f'Failed to query the graph for {querystr} due to {str(e)}') from e

        log.debug('Got result from The Graph query')
        return result
