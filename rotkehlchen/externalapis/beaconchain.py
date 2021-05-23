import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Union, overload

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.chain.ethereum.eth2_utils import ValidatorBalance
from rotkehlchen.chain.ethereum.typing import ValidatorID, ValidatorPerformance
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.typing import ChecksumEthAddress, ExternalService
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.serialization import jsonloads_dict
from rotkehlchen.constants.timing import DEFAULT_CONNECT_TIMEOUT

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


MAX_WAIT_SECS = 60
BEACONCHAIN_READ_TIMEOUT = 75
BEACONCHAIN_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, BEACONCHAIN_READ_TIMEOUT)

logger = logging.getLogger(__name__)


class BeaconChain(ExternalServiceWithApiKey):
    """Even though the beaconchain allows for API keys we don't implement it yet.
    We do extend ExternalServiceWithApiKey though so that it becomes easier to add
    in the future.

    https://beaconcha.in/api/v1/docs
    """

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.BEACONCHAIN)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.warning_given = False
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.url = 'https://beaconcha.in/api/v1/'

    def _query(
            self,
            module: Literal['validator'],
            endpoint: Literal['balancehistory', 'performance', 'eth1'],
            encoded_args: str,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        if endpoint == 'eth1':
            query_str = f'{self.url}{module}/{endpoint}/{encoded_args}'
        else:
            query_str = f'{self.url}{module}/{encoded_args}/{endpoint}'
        api_key = self._get_api_key()
        if api_key is not None:
            query_str += f'?apikey={api_key}'
        times = QUERY_RETRY_TIMES
        backoff_in_seconds = 10

        logger.debug(f'Querying beaconcha.in API for {query_str}')
        while True:
            try:
                response = self.session.get(query_str, timeout=BEACONCHAIN_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Querying {query_str} failed due to {str(e)}') from e

            if response.status_code == 429:
                minute_rate_limit = response.headers.get('x-ratelimit-limit-minute', 'unknown')
                user_minute_rate_limit = response.headers.get('x-ratelimit-remaining-minute', 'unknown')  # noqa: E501
                daily_rate_limit = response.headers.get('x-ratelimit-limit-day', 'unknown')
                user_daily_rate_limit = response.headers.get('x-ratelimit-remaining-day', 'unknown')  # noqa: E501
                month_rate_limit = response.headers.get('x-ratelimit-limit-month', 'unknown')
                user_month_rate_limit = response.headers.get('x-ratelimit-remaining-month', 'unknown')  # noqa: E501
                if times == 0:
                    msg = (
                        f'Beaconchain API request {response.url} failed '
                        f'with HTTP status code {response.status_code} and text '
                        f'{response.text} after 5 retries'
                    )
                    logger.debug(
                        f'{msg} minute limit: {user_minute_rate_limit}/{minute_rate_limit}, '
                        f'daily limit: {user_daily_rate_limit}/{daily_rate_limit}, '
                        f'monthly limit: {user_month_rate_limit}/{month_rate_limit}',
                    )
                    raise RemoteError(msg)

                retry_after = response.headers.get('retry-after', None)
                if retry_after:
                    retry_after_secs = int(retry_after)
                    if retry_after_secs > MAX_WAIT_SECS:
                        msg = (
                            f'Beaconchain API request {response.url} got rate limited. Would '
                            f'need to wait for {retry_after} seconds which is more than the '
                            f'wait limit of {MAX_WAIT_SECS} seconds. Bailing out.'
                        )
                        logger.debug(
                            f'{msg} minute limit: {user_minute_rate_limit}/{minute_rate_limit}, '
                            f'daily limit: {user_daily_rate_limit}/{daily_rate_limit}, '
                            f'monthly limit: {user_month_rate_limit}/{month_rate_limit}',
                        )
                        raise RemoteError(msg)
                    # else
                    sleep_seconds = retry_after_secs
                else:
                    # Rate limited. Try incremental backoff since retry-after header is missing
                    sleep_seconds = backoff_in_seconds * (QUERY_RETRY_TIMES - times + 1)
                times -= 1
                logger.debug(
                    f'Beaconchain API request {response.url} got rate limited. Sleeping '
                    f'for {sleep_seconds}. We have {times} tries left.'
                    f'minute limit: {user_minute_rate_limit}/{minute_rate_limit}, '
                    f'daily limit: {user_daily_rate_limit}/{daily_rate_limit}, '
                    f'monthly limit: {user_month_rate_limit}/{month_rate_limit}',
                )
                gevent.sleep(sleep_seconds)
                continue
            # else
            break

        if response.status_code != 200:
            raise RemoteError(
                f'Beaconchain API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Beaconchain API returned invalid JSON response: {response.text}',
            ) from e

        if json_ret.get('status') != 'OK':
            raise RemoteError(f'Beaconchain API returned non-OK status. Response: {json_ret}')

        if 'data' not in json_ret:
            raise RemoteError(f'Beaconchain API did not contain a data key. Response: {json_ret}')

        return json_ret['data']

    def get_balance_history(self, validator_indices: List[int]) -> Dict[int, ValidatorBalance]:
        """Get the balance history of all the validators given from the indices list

        https://beaconcha.in/api/v1/docs/index.html#/Validator/get_api_v1_validator__indexOrPubkey__balancehistory

        Queries in chunks of 100 due to api limitations.

        NOTICE: Do not use yet. The results seem incosistent. The list can accept
        up to 100 validators, but the balance history is for the last 100 epochs
        of each validator, limited to 100 results. So it's not really useful.

        Their devs said they will have a look as this may not be desired behaviour.

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        chunks = list(get_chunks(validator_indices, n=100))
        data = []
        for chunk in chunks:
            result = self._query(
                module='validator',
                endpoint='balancehistory',
                encoded_args=','.join(str(x) for x in chunk),
            )
            if isinstance(result, list):
                data.extend(result)
            else:
                data.append(result)

        # We are only interested in last epoch, so get its value
        balances: Dict[int, ValidatorBalance] = {}
        try:
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
        except KeyError as e:
            raise RemoteError(
                f'Beaconchai.in balance response processing error. Missing key entry {str(e)}',
            ) from e

        return balances

    @overload
    def get_performance(
            self,
            indices_or_pubkeys: List[int],
    ) -> Dict[int, ValidatorPerformance]:
        ...

    @overload
    def get_performance(
            self,
            indices_or_pubkeys: List[str],
    ) -> Dict[str, ValidatorPerformance]:
        ...

    def get_performance(
            self,
            indices_or_pubkeys: Union[List[int], List[str]],
    ) -> Union[Dict[int, ValidatorPerformance], Dict[str, ValidatorPerformance]]:
        """Get the performance of all the validators given from the list of indices or pubkeys

        Queries in chunks of 100 due to api limitations

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        chunks = list(get_chunks(indices_or_pubkeys, n=100))  # type: ignore
        data = []
        for chunk in chunks:
            result = self._query(
                module='validator',
                endpoint='performance',
                encoded_args=','.join(str(x) for x in chunk),
            )
            if isinstance(result, list):
                data.extend(result)
            else:
                data.append(result)

        try:
            performance = {}
            for entry in data:
                index = entry['validatorindex']
                performance[index] = ValidatorPerformance(
                    balance=entry['balance'],
                    performance_1d=entry['performance1d'],
                    performance_1w=entry['performance7d'],
                    performance_1m=entry['performance31d'],
                    performance_1y=entry['performance365d'],
                )
        except KeyError as e:
            raise RemoteError(
                f'Beaconchai.in performance response processing error. Missing key entry {str(e)}',
            ) from e

        return performance

    def get_eth1_address_validators(self, address: ChecksumEthAddress) -> List[ValidatorID]:
        """Get a list of Validators that are associated with the given eth1 address

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        result = self._query(
            module='validator',
            endpoint='eth1',
            encoded_args=address,
        )
        if isinstance(result, list):
            data = result
        else:
            data = [result]

        try:
            validators = [
                ValidatorID(
                    validator_index=x['validatorindex'],
                    public_key=x['publickey'],
                ) for x in data
            ]
        except KeyError as e:
            raise RemoteError(
                f'Beaconchai.in eth1 response processing error. Missing key entry {str(e)}',
            ) from e
        return validators
