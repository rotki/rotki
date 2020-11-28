from json.decoder import JSONDecodeError
from typing import Any, Dict, List, NamedTuple

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.typing import ExternalService
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.serialization import rlk_jsonloads_dict


class ValidatorBalance(NamedTuple):
    epoch: int
    balance: int  # in wei
    effective_balance: int  # in wei


class ValidatorPerformance(NamedTuple):
    balance: int  # in wei
    performance_1d: int  # in wei
    performance_7d: int  # in wei
    performance_1m: int  # in wei
    performance_1y: int  # in wei


class Beaconchain(ExternalServiceWithApiKey):
    """Even though the beaconchain allows for API keys we don't implement it yet.
    We do extend ExternalServiceWithApiKey though so that it becomes easier to add
    in the future.

    https://beaconcha.in/api/v1/docs
    """

    def __init__(self, database: DBHandler, msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.ETHERSCAN)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.warning_given = False
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.url = 'https://beaconcha.in/api/v1/'

    def _query(
            self,
            module: Literal['validator'],
            endpoint: Literal['balanceHistory', 'performance'],
            encoded_args: str,
    ) -> List[Dict[str, Any]]:
        """
        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        query_str = f'{self.url}{module}/{encoded_args}/{endpoint}'
        times = QUERY_RETRY_TIMES
        backoff_in_seconds = 10

        while True:
            try:
                response = self.session.get(query_str)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Querying {query_str} failed due to {str(e)}')

            if response.status_code == 429:
                if times == 0:
                    raise RemoteError(
                        f'Beaconchain API request {response.url} failed '
                        f'with HTTP status code {response.status_code} and text '
                        f'{response.text} after 5 retries',
                    )

                # We got rate limited. Let's try incremental backoff
                gevent.sleep(backoff_in_seconds * (QUERY_RETRY_TIMES - times + 1))
                continue
            else:
                break

        if response.status_code != 200:
            raise RemoteError(
                f'Beaconchain API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = rlk_jsonloads_dict(response.text)
        except JSONDecodeError:
            raise RemoteError(f'Beaconchain API returned invalid JSON response: {response.text}')

        if json_ret.get('status') != 'OK':
            raise RemoteError(f'Beaconchain API returned non-OK status. Response: {json_ret}')

        if 'data' not in json_ret:
            raise RemoteError(f'Beaconchain API did not contain a data key. Response: {json_ret}')

        return json_ret['data']

    def get_balance(self, validator_indices: List[int]) -> Dict[int, ValidatorBalance]:
        """Get the balance of all the validators given from the indices list

        Queries in chunks of 100 due to api limitations

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        chunks = list(get_chunks(validator_indices, n=100))
        data = []
        for chunk in chunks:
            data.extend(self._query(
                module='validator',
                endpoint='balanceHistory',
                encoded_args=','.join(str(x) for x in chunk),
            ))

        # We are only interested in last epoch, so get its value
        balances: Dict[int, ValidatorBalance] = {}
        for entry in data:
            index = entry['validatorindex']
            epoch = entry['epoch']
            if index in balances and balances[index].epoch >= epoch:
                continue

            balances[index] = ValidatorBalance(
                epoch=epoch,
                balance=entry['balance'],
                effective_balance=entry['effectivebalance'],
            )

        return balances

    def get_performance(self, validator_indices: List[int]) -> Dict[int, ValidatorPerformance]:
        """Get the performance of all the validators given from the indices list

        Queries in chunks of 100 due to api limitations

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        chunks = list(get_chunks(validator_indices, n=100))
        data = []
        for chunk in chunks:
            data.extend(self._query(
                module='validator',
                endpoint='performance',
                encoded_args=','.join(str(x) for x in chunk),
            ))

        performance = {}
        for entry in data:
            index = entry['validatorindex']
            performance[index] = ValidatorPerformance(
                balance=entry['balance'],
                performance_1d=entry['performance1d'],
                performance_7d=entry['performance7d'],
                performance_1m=entry['performance31d'],
                performance_1y=entry['performance365d'],
            )

        return performance
