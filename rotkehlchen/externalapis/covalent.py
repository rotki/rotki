import logging
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple

import requests

from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.externalapis.utils import read_integer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, CovalentTransaction, ExternalService, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import create_timestamp, ts_now

COVALENT_QUERY_LIMIT = 1000
CONST_RETRY = 1
DATE_FORMAT_COVALENT = '%Y-%m-%dT%H:%M:%SZ'
DEFAULT_API = 'covalent'
KEY = 'ckey_cb70cd52c833489ea522f104e1a'
PAGESIZE = 8000

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

chains_id = {
    "ethereum": 1,
    "rsk": 30,
    "binance_chain": 56,
    "matic": 137,
    "fantom_opera": 250,
    "arbitrum": 42161,
    "avalanche": 43114,
    "palm": 11297108109,
}


def convert_transaction_from_covalent(
        data: Dict[str, Any],
) -> CovalentTransaction:
    """Reads dict data of a transaction from Covalent and deserializes it

    Can raise DeserializationError if something is wrong
    """
    try:
        timestamp = create_timestamp(
            datestr=data['block_signed_at'],
            formatstr=DATE_FORMAT_COVALENT,
        )
        # TODO input and nonce is decoded in Covalent api, encoded in future
        return CovalentTransaction(
            timestamp=timestamp,
            block_number=data['block_height'],
            tx_hash=data['tx_hash'],
            from_address=data['from_address'],
            to_address=data['to_address'],
            value=read_integer(data, 'value', DEFAULT_API),
            gas=read_integer(data, 'gas_offered', DEFAULT_API),
            gas_price=read_integer(data, 'gas_price', DEFAULT_API),
            gas_used=read_integer(data, 'gas_spent', DEFAULT_API),
            input_data='0x',
            nonce=0,
        )
    except KeyError as e:
        raise DeserializationError(
            f'Covalent avalanche transaction missing expected key {str(e)}',
        ) from e


class Covalent(ExternalServiceWithApiKey):
    def __init__(
            self,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            chain_id: int,
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.COVALENT)
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.msg_aggregator = msg_aggregator
        self.chain_id = chain_id

    def _query(
            self,
            module: str,
            action: str,
            address: str = None,
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Queries Covalent

        May raise:
        - RemoteError if there are any problems with reaching Covalent or if
        an unexpected response is returned
        """
        query_str = f'https://api.covalenthq.com/v1/{self.chain_id}/{action}'
        if address:
            query_str += f'/{address}'
        query_str += f'/{module}/'

        own_key = self._get_api_key()
        query_str += f'?key={own_key if own_key else KEY}'

        if options:
            for name, value in options.items():
                query_str += f'&{name}={value}'

        retry = 0
        while retry <= CONST_RETRY:
            log.debug(f'Querying covalent: {query_str}')  # noqa: E501 lgtm [py/clear-text-logging-sensitive-data]
            try:
                response = self.session.get(query_str, timeout=timeout if timeout else DEFAULT_TIMEOUT_TUPLE)  # noqa: E501
            except requests.exceptions.RequestException as e:
                # In timeout retry
                if isinstance(e, requests.exceptions.Timeout):
                    if retry == CONST_RETRY:
                        return None
                    retry += 1
                    continue
                raise RemoteError(f'Covalent API request failed due to {str(e)}') from e

            try:
                result = response.json()
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Covalent API request {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            if response.status_code != 200:
                if 'error_message' in result:
                    error_message = result['error_message']
                else:
                    error_message = None
                raise RemoteError(
                    f'Covalent API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and '
                    f'Error message: {error_message} and text',
                    f'{response.text}',
                )

            # success, break out of the loop and return result
            break
        return result

    def get_transactions(
            self,
            account: ChecksumEvmAddress,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Optional[List[CovalentTransaction]]:
        """Gets a list of transactions for account.
        - account is address for wallet.
        - to_ts is latest date.
        - from_ts is oldest date.
        May raise:
        - RemoteError due to self._query(). Also if the returned result
        is not in the expected format
        """

        if from_ts is None:
            from_ts = Timestamp(0)
        if to_ts is None:
            to_ts = ts_now()

        result_master = []
        i = 0
        options = {'page-number': i, 'page-size': PAGESIZE}
        while True:
            result = self._query(
                module='transactions_v2',
                address=account,
                action='address',
                options=options,
            )
            if result is None:
                return result

            try:
                result_master += result['data']['items']
                if result['data']['pagination']['has_more'] is False:
                    break
                if len(result['data']['items']) < PAGESIZE:
                    break
                date_str = result['data']['items'][-1]['block_signed_at']
                last_timestamp = create_timestamp(
                    datestr=date_str,
                    formatstr=DATE_FORMAT_COVALENT,
                )
            except KeyError:
                return None

            if last_timestamp <= from_ts:
                break
            i += 1
            options = {'page-number': i, 'page-size': PAGESIZE}

        def between_date(value: Dict) -> bool:
            try:
                v_timestamp = create_timestamp(
                    datestr=value['block_signed_at'],
                    formatstr=DATE_FORMAT_COVALENT,
                )
                return from_ts <= v_timestamp <= to_ts  # type: ignore
            except KeyError:
                return False

        list_transactions = list(filter(between_date, result_master))
        transactions = []
        for transaction in list_transactions:
            try:
                tx = convert_transaction_from_covalent(transaction)
            except DeserializationError as e:
                self.msg_aggregator.add_warning(f'{str(e)}. Skipping transaction')
                continue
            transactions.append(tx)

        return transactions

    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Gets the receipt for the given transaction hash

        May raise:
        - RemoteError due to self._query().
        """
        result = self._query(
            module=tx_hash,
            action='transaction_v2',
        )
        if result is None:
            return result

        try:
            transaction_receipt = result['data']['items'][0]
            transaction_receipt['timestamp'] = create_timestamp(
                datestr=transaction_receipt['block_signed_at'],
                formatstr=DATE_FORMAT_COVALENT,
            )
            return transaction_receipt
        except KeyError:
            return None

    def get_token_balances_address(
            self,
            address: ChecksumEvmAddress,
    ) -> Optional[List[Dict[str, Any]]]:
        options = {'limit': COVALENT_QUERY_LIMIT, 'page-size': PAGESIZE}
        result = self._query(
            module='balances_v2',
            address=address,
            action='address',
            options=options,
        )
        if result is None:
            return result
        try:
            return result['data']['items']
        except KeyError:
            return None
