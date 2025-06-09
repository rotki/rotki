import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import requests
from gql import Client, gql
from gql.transport.exceptions import TransportError, TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport
from graphql.error import GraphQLError

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import APIKeyNotConfigured
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ApiKey, ExternalService
from rotkehlchen.utils.concurrency import sleep

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

RETRY_BACKOFF_FACTOR: Final = 0.2
THEGRAPH_BASE_URL: Final = 'https://gateway-arbitrum.network.thegraph.com/api/'


class Graph(ExternalServiceWithApiKey):

    def __init__(
            self,
            subgraph_id: str,
            database: 'DBHandler',
            label: str,
    ) -> None:
        """
        subgraph_id is the id that TheGraph assigns to the subgraph in their decentralized
        service. `label` is a human readable tag for the subgraph so the user knows what service
        was queried in case of error. It is used only in messages that can reach the user.

        - May raise requests.RequestException if there is a problem connecting to the subgraph
        """
        super().__init__(database=database, service_name=ExternalService.THEGRAPH)
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
        previous_key = self.api_key
        if (api_key := self._get_api_key()) is None and self.graph_label == CPT_ENS:
            api_key = ApiKey('d943ea1af415001154223fdf46b6f193')  # key created by yabir enabled for ens  # noqa: E501
            if self.warning_given is False:
                self.db.msg_aggregator.add_message(
                    message_type=WSMessageType.MISSING_API_KEY,
                    data={
                        'service': ExternalService.THEGRAPH.serialize(),
                        'location': self.graph_label,
                    },
                )
                self.warning_given = True
        elif api_key is None:  # don't bother the user and fail silently. We avoid exhausting the default key  # noqa: E501
            raise APIKeyNotConfigured(f'API key for subgraph {self.graph_label} not found')

        if self.client is not None and api_key == previous_key:
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
        prefix, result = '', None
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
                if 'malformed API key' in error_msg:
                    raise RemoteError(f'{base_msg} because the given API key is malformed') from e

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
                    sleep(sleep_seconds)
                else:
                    raise RemoteError(f'{base_msg}. No retries left.') from e

            except (GraphQLError, TransportError) as e:
                raise RemoteError(f'Failed to query the graph for {querystr} due to {e}') from e
            else:
                break

        assert result  # result will always exist here.
        log.debug(f'Got result {result} from The Graph query')
        return result
