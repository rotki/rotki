import logging
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Union, overload

import gevent
import requests
from eth_utils.address import to_checksum_address
from typing_extensions import Literal

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthTokenInfo, ExternalService
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Alethio(ExternalServiceWithApiKey):

    def __init__(
            self,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            all_eth_tokens: List[EthTokenInfo],
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.ALETHIO)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.all_tokens = all_eth_tokens
        self.session.headers.update({'User-Agent': 'rotkehlchen'})

    @overload  # noqa: F811
    def _query(  # pylint: disable=no-self-use
            self,
            root_endpoint: Literal['accounts'],
            path: str,
            full_query_str: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @overload  # noqa: F811
    def _query(  # pylint: disable=no-self-use
            self,
            root_endpoint: Literal['foo'],
            path: str,
            full_query_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...

    def _query(  # noqa: F811
            self,
            root_endpoint: str,
            path: str,
            full_query_str: Optional[str] = None,
    ) -> Union[Dict[str, Any], List]:  # noqa: F811
        if full_query_str:
            # If this is a pagination call
            query_str = full_query_str
        else:
            query_str = f'https://api.aleth.io/v1/{root_endpoint}/{path}'
        log.debug(f'Querying alethio for {query_str}')

        api_key = self._get_api_key()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

        backoff = 1
        backoff_limit = 13
        while backoff < backoff_limit:
            try:
                response = self.session.get(query_str)
            except requests.exceptions.ConnectionError as e:
                if 'Max retries exceeded with url' in str(e):
                    log.debug(
                        f'Got max retries exceeded from alethio. Will '
                        f'backoff for {backoff} seconds.',
                    )
                    gevent.sleep(backoff)
                    backoff = backoff * 2
                    if backoff >= backoff_limit:
                        raise RemoteError(
                            'Getting alethio max connections error even '
                            'after we incrementally backed off',
                        )
                    continue

                raise RemoteError(f'Alethio API request failed due to {str(e)}')

            if response.status_code == 429:
                log.debug(
                    f'Got response: {response.text} from alethio. Will '
                    f'backoff for {backoff} seconds.',
                )
                gevent.sleep(backoff)
                backoff = backoff * 2
                if backoff >= backoff_limit:
                    raise RemoteError(
                        'Alethio keeps returning rate limit errors even '
                        'after we incrementally backed off',
                    )
                continue

            if response.status_code != 200:
                raise RemoteError(
                    f'Alethio API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            try:
                json_ret = rlk_jsonloads_dict(response.text)
            except JSONDecodeError:
                raise RemoteError(f'alethio returned invalid JSON response: {response.text}')

            data = json_ret.get('data', None)
            if data is None:
                errors = json_ret.get('errors', None)
                if errors is None:
                    msg = f'Unexpected alethio response: {response.text}'
                else:
                    msg = str(errors)
                raise RemoteError(f'alethio response error: {msg}')

            has_next = False
            try:
                has_next = json_ret['meta']['page']['hasNext']
            except KeyError:
                raise RemoteError(
                    f'Alethio response does not contain pagination information: {response.text}',
                )

            if has_next:
                try:
                    link = json_ret['links']['next']
                except KeyError:
                    raise RemoteError(
                        f'Alethio response does not contain next page link: {response.text}',
                    )

                next_data = self._query(  # type: ignore
                    root_endpoint=root_endpoint,
                    path=path,
                    full_query_str=link,
                )
                if root_endpoint == 'accounts':
                    data.extend(next_data)
                else:
                    raise AssertionError(
                        'Have not yet implemented alethio endpoints returning non lists',
                    )

            # if we got here we should return
            break

        return data

    def token_address_to_identifier(self, address: ChecksumEthAddress) -> Optional[EthTokenInfo]:
        # TODO: Cache these stuff in a mapping
        for token in self.all_tokens:
            if token.address == address:
                return token

        return None

    def get_token_balances(self, account: ChecksumEthAddress) -> Dict[EthereumToken, FVal]:
        """Auto-detect which tokens are owned and get token balances for the account

        The returned balance is already normalized for the token's decimals.

        May raise:
        - RemoteError if there is a problem contacting aleth.io
        """
        balances = {}
        data = self._query(root_endpoint='accounts', path=f'{account}/tokenBalances')
        for entry in data:
            entry_type = entry.get('type', None)
            if entry_type == 'TokenBalance':

                attributes = entry.get('attributes', None)
                balance = None
                if attributes is not None:
                    balance = attributes.get('balance', None)
                if balance is None:
                    continue

                relationships = entry.get('relationships', None)
                if relationships is None:
                    continue
                token = relationships.get('token', None)
                if token is None:
                    continue
                if 'data' not in token:
                    continue
                if 'id' not in token['data']:
                    continue

                token_address = to_checksum_address(token['data']['id'])
                token_info = self.token_address_to_identifier(token_address)
                if token_info is None:
                    continue

                amount = FVal(balance) / (FVal(10) ** FVal(token_info.decimal))
                balances[EthereumToken(token_info.symbol)] = amount

        return balances
