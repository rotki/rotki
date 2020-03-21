import hashlib
import hmac
import json
import logging
import time
from base64 import b64encode
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple, Union

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import ApiKey, ApiSecret, Fee, Location, Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_now
from rotkehlchen.utils.serialization import rlk_jsonloads_list

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GeminiPermissionError(Exception):
    pass


class Gemini(ExchangeInterface):

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            base_uri='https://api.gemini.com',
    ):
        super(Gemini, self).__init__('gemini', api_key, secret, database)
        self.base_uri = base_uri
        self.msg_aggregator = msg_aggregator

        self.session.headers.update({
            'Content-Type': 'text/plain',
            'X-GEMINI-APIKEY': self.api_key,
            'Cache-Control': 'no-cache',
            'Content-Length': '0',
        })

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Gemini API key is good for usage in Rotki

        Makes sure that the following permissions are given to the key:
        - Auditor
        """
        try:
            self._api_query('balances')
        except GeminiPermissionError:
            msg = (
                f'Provided Gemini API key needs to have "Auditor" permission activated. '
                f'Please log into your gemini account and create a key with '
                f'the required permissions.'
            )
            return False, msg
        except RemoteError as e:
            error = str(e)
            return False, error

        return True, ''

    def _api_query(  # noqa: F811
            self,
            endpoint: str,
            request_method: Literal['GET', 'POST'] = 'GET',
            options: Optional[Dict[str, Any]] = None,
    ) -> Union[List[Any], Dict[str, Any]]:
        """Performs a Gemini API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        Raises GeminiPermissionError if the API Key does not have sufficient
        permissions for the endpoint
        """

        endpoint = f'/v1/{endpoint}'
        url = f'{self.base_uri}/{endpoint}'

        timestamp = str(int(time.time()) * 1000)
        payload = {'request': endpoint, 'nonce': timestamp}
        encoded_payload = json.dumps(payload).encode()
        b64 = b64encode(encoded_payload)
        signature = hmac.new(self.secret, b64, hashlib.sha384).hexdigest()
        self.session.headers.update({
            'X-GEMINI-PAYLOAD': b64,
            'X-GEMINI-SIGNATURE': signature,
        })
        response = requests.post(url)

        retries_left = QUERY_RETRY_TIMES
        while retries_left > 0:
            try:
                response = self.session.post(url)
            except requests.exceptions.ConnectionError as e:
                raise RemoteError(f'Gemini query at {url} connection error: {str(e)}')

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                # Backoff a bit by sleeping. Sleep more, the more retries have been made
                gevent.sleep(QUERY_RETRY_TIMES / retries_left)
                retries_left -= 1
            else:
                # get out of the retry loop, we did not get 429 complaint
                break

        json_ret: Union[List[Any], Dict[str, Any]]
        if response.status_code == HTTPStatus.FORBIDDEN:
            raise GeminiPermissionError(
                f'API key does not have permission for {endpoint}',
            )
        elif response.status_code == HTTPStatus.BAD_REQUEST:
            if 'InvalidSignature' in response.text:
                raise GeminiPermissionError('Invalid API Key or API secret')
            # else let it be handled by the generic non-200 code error below

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Gemini query at {url} responded with error '
                f'status code: {response.status_code} and text: {response.text}',
            )

        try:
            json_ret = rlk_jsonloads_list(response.text)
        except JSONDecodeError:
            raise RemoteError(
                f'Gemini {request_method} query at {url} '
                f'returned invalid JSON response: {response.text}',
            )

        return json_ret

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[Dict[Asset, Dict[str, Any]]], str]:
        try:
            balances = self._api_query('balances')
        except (GeminiPermissionError, RemoteError) as e:
            msg = f'Gemini API request failed. {str(e)}'
            log.error(msg)
            return None, msg

        returned_balances: Dict[Asset, Dict[str, Any]] = {}
        for entry in balances:
            try:
                amount = deserialize_asset_amount(entry['amount'])
                # ignore empty balances
                if amount == ZERO:
                    continue

                asset = asset_from_coinbase(entry['currency'])
                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing gemini balance result due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue
                returned_balances[asset] = {
                    'amount': amount,
                    'usd_value': amount * usd_price,
                }

            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found gemini balance result with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found gemini balance result with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a gemini balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a gemini balance',
                    error=msg,
                )
                continue

        return returned_balances, ''
