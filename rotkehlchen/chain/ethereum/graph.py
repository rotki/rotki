import json
import logging
import re
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import gevent
import requests
from gql import Client, gql
from gql.transport.exceptions import TransportError, TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport
from graphql.error import GraphQLError

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import APIKeyNotConfigured
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExternalService

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


GRAPH_QUERY_LIMIT: Final = 1000
GRAPH_QUERY_SKIP_LIMIT: Final = 5000
RE_MULTIPLE_WHITESPACE: Final = re.compile(r'\s+')
RETRY_BACKOFF_FACTOR: Final = 0.2
THEGRAPH_BASE_URL: Final = 'https://gateway-arbitrum.network.thegraph.com/api/'
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


class Graph(ExternalServiceWithApiKey):

    def __init__(self, subgraph_id: str, database: 'DBHandler', label: str) -> None:
        """
        subgraph_id is the id that TheGraph assigns to the subgraph in their decentralized
        service. `label` is a human readable tag for the subgraph so the user knows what service
        was queried in case of error. It is used only in messages that can reach the user.

        - May raise requests.RequestException if there is a problem connecting to the subgraph
        """
        super().__init__(database=database, service_name=ExternalService.THEGRAPH)
        self.db = database
        self.subgraph_id = subgraph_id
        self.warning_given = False
        self.graph_label = label
        self.client: Client | None = None
        self.api_key = None

    def _maybe_create_client(self) -> Client:
        """Create/edit thegraph client taking into account that the user might have
        edited the api key.

        - May raise APIKeyNotConfigured
        """
        if (api_key := self._get_api_key()) is None:
            if self.warning_given is False:
                self.db.msg_aggregator.add_message(  # type: ignore[union-attr]  # self.db is not None here
                    message_type=WSMessageType.MISSING_API_KEY,
                    data={
                        'service': ExternalService.THEGRAPH.serialize(),
                        'location': self.graph_label,
                    },
                )
                self.warning_given = True

            raise APIKeyNotConfigured(f'API key for subgraph {self.graph_label} not found')

        if self.client is not None and self.api_key == api_key:
            return self.client

        try:
            self.client = Client(
                transport=RequestsHTTPTransport(url=f'{THEGRAPH_BASE_URL}{self.api_key}/subgraphs/id/{self.subgraph_id}'),
                fetch_schema_from_transport=False,
            )
        except (requests.exceptions.RequestException) as e:
            raise RemoteError(
                f'Failed to connect to the graph with id {self.subgraph_id} due to {e!s}',
            ) from e

        self.api_key = api_key
        return self.client

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
        - APIKeyNotConfigured
        """
        prefix = ''
        if param_types is not None:
            prefix = 'query '
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
            prefix += '{'

        querystr = prefix + querystr
        log.debug(f'Querying The Graph for {querystr}')

        retries_left = retry_limit = CachedSettings().get_query_retry_limit()
        client = self._maybe_create_client()
        while retries_left > 0:
            try:
                result = client.execute(gql(querystr), variable_values=param_values)
            except (TransportServerError, TransportQueryError) as e:
                # https://gql.readthedocs.io/en/latest/advanced/error_handling.html
                # Kind of guessing here ... these may be the only ones we can backoff for
                base_msg = f'The Graph query to {self.graph_label}({self.subgraph_id}) failed'
                error_msg = str(e)
                if 'Subgraph not authorized by user' in error_msg:
                    raise RemoteError(f'{base_msg} because subgraph is not authorized. {error_msg}') from e  # noqa: E501
                if 'invalid bearer token: invalid auth token' in error_msg:
                    raise RemoteError(f'{base_msg} because the token is not valid. {error_msg}') from e  # noqa: E501

                # we retry again
                retry_base_msg = base_msg + f' with payload {querystr} due to {error_msg}'
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
                    log.error(f'{retry_base_msg}. {retry_msg}')
                    gevent.sleep(sleep_seconds)
                else:
                    raise RemoteError(f'{base_msg}. No retries left.') from e

            except (GraphQLError, TransportError) as e:
                raise RemoteError(f'Failed to query the graph for {querystr} due to {e}') from e
            else:
                break

        log.debug('Got result from The Graph query')
        return result
