import json
import logging
from typing import Any, Dict, Optional, Tuple

import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from typing_extensions import Literal

from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import ChecksumEthAddress, Timestamp

log = logging.getLogger(__name__)


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
        transport = RequestsHTTPTransport(url=url)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]] = None,
            param_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: If there is a problem querying
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
            raise RemoteError(f'Failed to query the graph for {querystr} due to {str(e)}')

        log.debug('Got result from The Graph query')
        return result
