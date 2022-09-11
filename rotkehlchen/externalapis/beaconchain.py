import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    Eth2Deposit,
    ValidatorID,
    ValidatorPerformance,
)
from rotkehlchen.chain.ethereum.modules.eth2.utils import ValidatorBalance
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.timing import DEFAULT_CONNECT_TIMEOUT, QUERY_RETRY_TIMES
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    ExternalService,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_gwei, get_chunks
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


MAX_WAIT_SECS = 60
BEACONCHAIN_READ_TIMEOUT = 75
BEACONCHAIN_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, BEACONCHAIN_READ_TIMEOUT)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _calculate_query_chunks(
        indices_or_pubkeys: Union[List[int], List[Eth2PubKey]],
) -> Union[List[List[int]], List[List[Eth2PubKey]]]:
    """Create chunks of queries.

    Beaconcha.in allows up to 100 validator or public keys in one query for most calls.
    Also has a URI length limit of ~8190, so seems no more than 80 public keys can be per call.
    """
    if len(indices_or_pubkeys) == 0:
        return []  # type: ignore

    n = 100
    if isinstance(indices_or_pubkeys[0], str):
        n = 80
    return list(get_chunks(indices_or_pubkeys, n=n))  # type: ignore


class BeaconChain(ExternalServiceWithApiKey):
    """Even though the beaconchain allows for API keys we don't implement it yet.
    We do extend ExternalServiceWithApiKey though so that it becomes easier to add
    in the future.

    https://beaconcha.in/api/v1/docs/
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
            endpoint: Optional[Literal['balancehistory', 'performance', 'eth1', 'deposits']],
            encoded_args: str,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        if endpoint is None:  # for now only validator data
            query_str = f'{self.url}{module}/{encoded_args}'
        elif endpoint == 'eth1':
            query_str = f'{self.url}{module}/{endpoint}/{encoded_args}'
        else:
            query_str = f'{self.url}{module}/{encoded_args}/{endpoint}'

        api_key = self._get_api_key()
        if api_key is not None:
            query_str += f'?apikey={api_key}'
        times = QUERY_RETRY_TIMES
        backoff_in_seconds = 10

        log.debug(f'Querying beaconcha.in API for {query_str}')
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
                    log.debug(
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
                        log.debug(
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
                log.debug(
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
        chunks = _calculate_query_chunks(validator_indices)
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

    def get_performance(
            self,
            indices_or_pubkeys: Union[List[int], List[Eth2PubKey]],
    ) -> Dict[int, ValidatorPerformance]:
        """Get the performance of all the validators given from the list of indices or pubkeys

        Queries in chunks of 100 due to api limitations

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        chunks = _calculate_query_chunks(indices_or_pubkeys)
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
                f'Beaconcha.in performance response processing error. Missing key entry {str(e)}',
            ) from e

        return performance

    def get_eth1_address_validators(self, address: ChecksumEvmAddress) -> List[ValidatorID]:
        """Get a list of Validators that are associated with the given eth1 address.

        Each entry is a tuple of (optional) validator index and pubkey

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
                    index=x['validatorindex'],
                    public_key=x['publickey'],
                    ownership_proportion=ONE,
                ) for x in data
            ]
        except KeyError as e:
            raise RemoteError(
                f'Beaconcha.in eth1 response processing error. Missing key entry {str(e)}',
            ) from e
        return validators

    def get_validator_deposits(
            self,
            indices_or_pubkeys: Union[List[int], List[Eth2PubKey]],
    ) -> List[Eth2Deposit]:
        """Get the deposits of all the validators given from the list of indices or pubkeys

        Queries in chunks of 100 due to api limitations

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        chunks = _calculate_query_chunks(indices_or_pubkeys)
        data = []
        for chunk in chunks:
            result = self._query(
                module='validator',
                endpoint='deposits',
                encoded_args=','.join(str(x) for x in chunk),
            )
            if isinstance(result, list):
                data.extend(result)
            else:
                data.append(result)

        deposits = []
        for entry in data:
            try:
                amount = from_gwei(FVal(entry['amount']))
                timestamp = entry['block_ts']
                usd_price = query_usd_price_zero_if_error(
                    asset=A_ETH,
                    time=timestamp,
                    location=f'Eth2 staking deposit at time {timestamp}',
                    msg_aggregator=self.msg_aggregator,
                )
                deposits.append(Eth2Deposit(
                    from_address=deserialize_evm_address(entry['from_address']),
                    pubkey=entry['publickey'],
                    withdrawal_credentials=entry['withdrawal_credentials'],
                    value=Balance(
                        amount=amount,
                        usd_value=amount * usd_price,
                    ),
                    tx_hash=deserialize_evm_tx_hash(entry['tx_hash']),
                    tx_index=entry['tx_index'],
                    timestamp=entry['block_ts'],
                ))
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                raise RemoteError(
                    f'Beaconchai.in deposits response processing error. {msg}',
                ) from e

        return deposits
