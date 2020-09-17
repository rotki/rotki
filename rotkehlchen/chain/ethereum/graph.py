import json
import logging
from typing import Any, Dict, Optional

import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from rotkehlchen.errors import RemoteError

log = logging.getLogger(__name__)


class Graph():

    def __init__(self, url: str) -> None:
        transport = RequestsHTTPTransport(url=url)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]],
            param_values: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: If there is a problem querying
        """
        prefix = 'query '
        if param_types is not None:
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
        prefix += '{'
        log.debug(f'Querying The Graph for {querystr}')
        try:
            result = self.client.execute(gql(prefix + querystr), variable_values=param_values)
        except (requests.exceptions.RequestException, Exception) as e:
            raise RemoteError(f'Failed to query the graph for {querystr} due to {str(e)}')

        log.debug('Got result from The Graph query')
        return result
