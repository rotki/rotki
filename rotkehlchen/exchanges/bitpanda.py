import json
import logging
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Optional, Tuple, Union, overload
from urllib.parse import urlencode

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_bitpanda
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, QUERY_RETRY_TIMES
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_kraken,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    Fee,
    Location,
    Timestamp,
    TradePair,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAX_PAGE_SIZE = 100


class Bitpanda(ExchangeInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.BITPANDA,
            api_key=api_key,
            secret=secret,
            database=database,
        )

        # self.uri = 'https://api.exchange.bitpanda.com/public/v1'
        self.uri = 'https://api.bitpanda.com/v1'
        self.session.headers.update({'X-API-KEY': self.api_key})
        self.msg_aggregator = msg_aggregator

    def first_connection(self) -> None:
        self.first_connection_made = True

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'X-API-KEY': self.api_key})

        return changed

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['wallets', 'fiatwallets'],
            options: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        ...

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['asset-wallets'],
            options: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        ...

    def _api_query(
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]] = None,
    ) -> Union[List[Any], Dict[str, Any]]:
        """Performs a bitpanda API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Returns a tuple of the result and optional pagination cursor.

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        """
        request_url = f'{self.uri}/{endpoint}'
        retries_left = QUERY_RETRY_TIMES
        if options is not None:
            request_url += '?' + urlencode(options)
        while retries_left > 0:
            log.debug(
                'Bitpanda API query',
                request_url=request_url,
                options=options,
            )
            try:
                response = self.session.get(request_url, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Bitpanda API request failed due to {str(e)}') from e
            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS and retries_left != 0:
                backoff_in_seconds = int(20 / retries_left)
                retries_left -= 1
                log.debug(
                    f'Got a 429 from Bitpanda query of {request_url}. Will backoff '
                    f'for {backoff_in_seconds} seconds. {retries_left} retries left',
                )
                gevent.sleep(backoff_in_seconds)
                continue

            if response.status_code != HTTPStatus.OK:
                raise RemoteError(
                    f'Bitpanda API request failed with response: {response.text} '
                    f'and status code: {response.status_code}',
                )

            # we got it, so break
            break

        try:
            decoded_json = jsonloads_dict(response.text)
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(f'Invalid JSON {response.text} in Bitpanda response. {e}') from e

        if 'data'not in decoded_json:
            raise RemoteError(f'Invalid JSON {response.text} in Bitpanda response. Expected "data" key')

        return decoded_json['data']

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            wallets = self._api_query('wallets')
            # asset_wallets = self._api_query('asset-wallets')
            fiat_wallets = self._api_query('fiatwallets')
        except RemoteError as e:
            msg = f'Failed to query Bitpanda balances. {str(e)}'
            return None, msg

        assets_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        wallets_len = len(wallets)
        for idx, entry in enumerate(wallets + fiat_wallets):

            if idx < wallets_len:
                symbol_key = 'cryptocoin_symbol'
            else:
                symbol_key = 'fiat_symbol'

            try:
                amount = deserialize_asset_amount(entry['attributes']['balance'])
                asset = asset_from_bitpanda(entry['attributes'][symbol_key])
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported/unknown Bitpanda asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing Bitpanda balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing bitpanda balance',
                    entry=entry,
                    error=msg,
                )
                continue

            if amount == ZERO:
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Bitpanda balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue
            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance), ''
