import json
import logging
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias

import requests

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import iso8601ts_to_timestamp
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ORDER_TYPE_CHANGE_TS: Final = Timestamp(1710806400)
CHAIN_MAPPING: Final = {
    SupportedBlockchain.ETHEREUM: 'mainnet',
    SupportedBlockchain.GNOSIS: 'xdai',
    SupportedBlockchain.ARBITRUM_ONE: 'arbitrum_one',
    SupportedBlockchain.BASE: 'base',
}
SUPPORTED_COWSWAP_BLOCKCHAIN: TypeAlias = Literal[
    SupportedBlockchain.ETHEREUM,
    SupportedBlockchain.GNOSIS,
    SupportedBlockchain.ARBITRUM_ONE,
    SupportedBlockchain.BASE,
]


class CowswapAPI:
    """This is the Cowswap API interface.

    https://api.cow.fi/docs/
    """

    def __init__(self, database: 'DBHandler', chain: SUPPORTED_COWSWAP_BLOCKCHAIN) -> None:
        self.database = database
        self.session = create_session()
        self.api_url = f'https://api.cow.fi/{CHAIN_MAPPING[chain]}/api/v1'

    def _query(self, endpoint: str) -> dict[str, Any]:
        """Query cowswap API endpoint.

        May raise:
        - RemoteError if there is a problem querying the api
        """
        query_str = f'{self.api_url}/{endpoint}'
        log.debug(f'Querying Cowswap API {query_str}')
        timeout = CachedSettings().get_timeout_tuple()
        try:
            response = self.session.get(url=query_str, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying {query_str} failed due to {e!s}') from e

        if response.status_code != 200:
            raise RemoteError(f'Cowswap API request {response.url} failed with HTTP status code {response.status_code} and text {response.text}')  # noqa: E501

        try:
            json_ret = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(f'Cowswap API returned invalid JSON response: {response.text}') from e  # noqa: E501

        return json_ret

    def get_order_data(self, order_uid: str) -> tuple[int, str]:
        """Query offchain order data either from the database
        if it already exists there or by querying the api if not.
        Returns raw_fee_amount and order_type as a tuple.

        May raise:
        - RemoteError if there is a problem querying the api
        """
        with self.database.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT order_type, raw_fee_amount FROM cowswap_orders WHERE identifier = ?',
                (order_uid,),
            ).fetchone()

        if result is not None:
            return int(result[1]), result[0]

        # else, we need to query the API
        data = self._query(f'orders/{order_uid}')
        raw_fee_amount, order_type = parse_order_data(data)

        with self.database.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR IGNORE INTO cowswap_orders(identifier, order_type, raw_fee_amount) VALUES (?, ?, ?)',  # noqa: E501
                (order_uid, order_type, str(raw_fee_amount)),  # use str() to prevent SQLite OverflowError  # noqa: E501
            )

        return raw_fee_amount, order_type


def parse_order_data(data: dict[str, Any]) -> tuple[int, str]:
    """Parses offchain order data from an api response.
    Returns raw_fee_amount and order_type as a tuple.

    May raise:
    - RemoteError if there is a problem parsing the data
    """
    try:
        if iso8601ts_to_timestamp(data['creationDate']) < ORDER_TYPE_CHANGE_TS:
            raw_fee_amount = int(data['executedFeeAmount'])
            order_type = data['class']
        else:
            raw_fee_amount = int(data.get('executedSurplusFee', data.get('executedFee', 0)))

            if (full_app_data := data.get('fullAppData')) is not None:
                metadata = json.loads(full_app_data)['metadata']
                order_type = metadata['orderClass']['orderClass'] if 'orderClass' in metadata else 'limit'  # noqa: E501
            else:
                order_type = 'limit'
    except (KeyError, json.decoder.JSONDecodeError, ValueError, DeserializationError) as e:
        log.error(f'Could not process Cowswap API response: {data} due to {e!s}')
        raise RemoteError('Invalid data from Cowswap API response') from e

    return raw_fee_amount, order_type
