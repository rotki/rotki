import logging
from json.decoder import JSONDecodeError
from typing import List, Optional

import gevent
import requests
from eth_utils.address import to_checksum_address

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
        super().__init__(database=database, service_name=ExternalService.ETHERSCAN)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.all_tokens = all_eth_tokens
        self.session.headers.update({'User-Agent': 'rotkehlchen'})

    def _query(self, path: str):
        query_str = f'https://api.aleth.io/v1/{path}'

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

            if response.status_codes == 429:
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
            if not data:
                errors = json_ret.get('errors', None)
                if not errors:
                    msg = 'Unexpected alethio response. Neither data nor errors in the response'
                else:
                    msg = str(errors)
                raise RemoteError(f'alethio response error: {msg}')

            return data

    def token_address_to_identifier(self, address: ChecksumEthAddress) -> Optional[str]:
        # TODO: Cache these stuff in a mapping
        for token in self.all_tokens:
            if token.address == address:
                return token.symbol

        return None

    def get_token_balances(self, account: ChecksumEthAddress):
        """Auto-detect which tokens are owned and get token balances for the account

        May raise:
        - RemoteError if there is a problem contacting aleth.io
        """
        balances = {}
        data = self._query(path=f'accounts/{account}/tokenBalances')
        for entry in data:
            entry_type = entry.get('type', None)
            if entry_type == 'TokenBalance':
                attributes = entry.get('attributes')
                balance = None
                if attributes:
                    balance = attributes.get('balance', None)
                if not balance:
                    continue

                token = entry.get('token', None)
                if not token:
                    continue
                if 'data' not in token:
                    continue
                if 'id' not in token['data']:
                    continue

                token_address = to_checksum_address(token['data']['id'])
                symbol = self.token_address_to_identifier(token_address)
                if not symbol:
                    continue
                amount = FVal(balance) / (FVal(10) ** FVal(token.decimals))
                balances[symbol] = amount

        return balances
