import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

import gevent
import requests
from gql import Client, gql
from gql.transport.exceptions import (
    TransportAlreadyConnected,
    TransportClosed,
    TransportProtocolError,
    TransportQueryError,
    TransportServerError,
)
from gql.transport.requests import RequestsHTTPTransport
from typing_extensions import Literal

from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


GRAPH_QUERY_LIMIT = 1000
RE_MULTIPLE_WHITESPACE = re.compile(r'\s+')
RETRY_BACKOFF_FACTOR = 0.2


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
        transport = RequestsHTTPTransport(url=url)
        self.client = Client(transport=transport)

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]] = None,
            param_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: there is a server/protocol/connection problem querying
        the subgraph.

        Gql v3 exceptions handling:
          - TransportServerError: request fails with status code >= 400.
          - TransportProtocolError: request fails with status code < 400, or
          request does not fail but response doesn't have 'errors' nor 'data'.
          - TransportQueryError: request does not fail but the result returned
          by the transport (an <ExecutionResult>) has 'errors'.
        """
        prefix = ''
        if param_types is not None:
            prefix = 'query '
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
            prefix += '{'

        querystr = prefix + querystr
        log.debug(f'Querying The Graph for {querystr}')

        retries_left = QUERY_RETRY_TIMES
        while retries_left > 0:
            try:
                result = self.client.execute(gql(querystr), variable_values=param_values)
            except (
                TransportProtocolError,
                TransportQueryError,
                TransportServerError,
            ) as e:
                exc_msg = e.errors if isinstance(e, TransportQueryError) else str(e)
                data = e.data if isinstance(e, TransportQueryError) else None
                base_msg = f'The Graph query: {querystr} failed due to: {exc_msg}'

                retries_left -= 1
                if retries_left:
                    sleep_seconds = RETRY_BACKOFF_FACTOR * pow(2, QUERY_RETRY_TIMES - retries_left)
                    retry_msg = (
                        f'Retrying query after {sleep_seconds} seconds. '
                        f'Retries left: {retries_left}.'
                    )
                    log.error(f'{base_msg}. {retry_msg}', data=data)
                    gevent.sleep(sleep_seconds)
                else:
                    raise RemoteError(f'{base_msg}. No retries left.') from e

            except (
                TransportAlreadyConnected,
                TransportClosed,
                requests.exceptions.RequestException,
            ) as e:
                raise RemoteError(
                    f'The Graph query: {querystr} failed due to: {str(e)}',
                ) from e
            else:
                break

        log.debug('Got result from The Graph query')
        return result
