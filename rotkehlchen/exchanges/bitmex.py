import hashlib
import hmac
import json
import logging
from collections.abc import Sequence
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Location, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.asset_movement import create_asset_movement_with_fee
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Fee,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, satoshis_to_btc, ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BITMEX_PRIVATE_ENDPOINTS = (
    'user',
    'user/wallet',
    'wallet/assets',
    'user/walletHistory',
)


def bitmex_to_world(symbol: str) -> AssetWithOracles:
    if symbol == 'XBt':
        return A_BTC.resolve_to_asset_with_oracles()

    # This shouldn't happen since all the trades in bitmex are against BTC
    # as for what @lefterisjp remembers in discord.
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.BITMEX,
        symbol=(symbol_upper := symbol.upper()),
        default=symbol_upper,
    ))


def margin_trade_from_bitmex(bitmex_trade: dict) -> MarginPosition:
    """Turn a bitmex margin trade returned from bitmex trade history to our common margin trade
    history format. This only returns margin positions. May raise:

    - KeyError
    - DeserializationError
    - UnknownAsset
    """
    close_time = iso8601ts_to_timestamp(bitmex_trade['transactTime'])
    profit_loss = AssetAmount(satoshis_to_btc(deserialize_asset_amount(bitmex_trade['amount'])))
    currency = bitmex_to_world(bitmex_trade['currency'])
    fee = deserialize_fee(bitmex_trade['fee'])
    notes = bitmex_trade['address']

    log.debug(
        'Processing Bitmex Trade',
        timestamp=close_time,
        profit_loss=profit_loss,
        currency=currency,
        fee=fee,
        notes=notes,
    )

    return MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=close_time,
        profit_loss=profit_loss,
        pl_currency=currency,
        fee=fee,
        fee_currency=A_BTC,
        notes=notes,
        link=str(bitmex_trade['transactID']),
    )


class Bitmex(ExchangeInterface):
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
            location=Location.BITMEX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = 'https://bitmex.com'
        self.session.headers.update({'api-key': api_key})
        self.asset_to_decimals: dict[str, int] = {}

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'api-key': credentials.api_key})
        return changed

    def first_connection(self) -> None:
        if self.first_connection_made:
            return
        try:
            self.get_assets_decimals()
        except RemoteError as e:
            log.error(f'Failed to obtain bitmex decimals due to: {e}. First connection not made')
            return

        self.first_connection_made = True

    def get_assets_decimals(self) -> None:
        """Bitmex returns balances as integers and we need to convert them to real numbers
        using the decimals provided by the exchange. Decimals are named `scale` in bitmex.
        """
        mappings = {}
        for entry in self._api_query(path='wallet/assets'):
            try:
                mappings[entry['currency']] = entry['scale']
            except KeyError as e:
                log.error(f'Missing key {e} when querying decimals in {entry}')
                raise RemoteError(f'Missing key {e} in assets response.') from e

        self.asset_to_decimals = mappings

    def validate_api_key(self) -> tuple[bool, str]:
        try:
            self._api_query('user')
        except RemoteError as e:
            error = str(e)
            if 'Invalid API Key' in error:
                return False, 'Provided API Key is invalid'
            if 'Signature not valid' in error:
                return False, 'Provided API Secret is invalid'
            # else reraise
            raise
        return True, ''

    def _generate_signature(self, verb: str, path: str, expires: int, data: str = '') -> str:
        signature = hmac.new(
            key=self.secret,
            msg=(verb.upper() + path + str(expires) + data).encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        self.session.headers.update({'api-signature': signature})
        return signature

    def _api_query(
            self,
            path: Literal[
                'user',
                'user/wallet',
                'wallet/assets',
                'user/walletHistory',
            ],
            options: dict | None = None,
    ) -> list:
        """
        Queries Bitmex with the given verb for the given path and options
        """
        # 20 seconds expiration
        expires = ts_now() + 20
        request_path_no_args = '/api/v1/' + path

        data = ''
        if not options:
            request_path = request_path_no_args
            signature_path = request_path
        else:
            request_path = request_path_no_args + '?' + urlencode(options)
            signature_path = request_path

        if path in BITMEX_PRIVATE_ENDPOINTS:
            self._generate_signature(
                verb='GET',
                path=signature_path,
                expires=expires,
                data=data,
            )

        self.session.headers.update({'api-expires': str(expires)})
        if data != '':
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        request_url = self.uri + request_path
        log.debug('Bitmex API Query', request_url=request_url)
        try:
            response = self.session.get(url=request_url, data=data)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Bitmex API request failed due to {e!s}') from e

        if response.status_code not in {200, 401}:
            raise RemoteError(
                f'Bitmex api request for {response.url} failed with HTTP '
                f'status code {response.status_code}',
            )

        try:
            json_ret: list = json.loads(response.text)
        except JSONDecodeError as e:
            raise RemoteError('Bitmex returned invalid JSON response') from e

        return json_ret

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        self.first_connection()
        returned_balances: dict[AssetWithOracles, Balance] = {}
        try:
            resp = self._api_query('user/wallet', {'currency': 'all'})
        except RemoteError as e:
            msg = f'Bitmex API request failed due to: {e!s}'
            log.error(msg)
            return None, msg

        for balance in resp:
            try:
                asset = bitmex_to_world(currency := balance['currency'])
                raw_amount = balance['amount']
            except (KeyError, UnknownAsset) as e:
                msg = str(e) if not isinstance(e, KeyError) else f'missing key {e}'
                log.error(f'Failed to process balance {balance} in bitmex due to {msg}')
                continue

            if (decimals := self.asset_to_decimals.get(currency)) is None:
                log.error(f'Unknown decimals for asset balance {balance} in bitmex. Skipping')
                continue

            amount = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=decimals,
            )

            usd_value = amount * Inquirer.find_usd_price(asset)
            returned_balances[asset] = Balance(amount=amount, usd_value=usd_value)
            log.debug(
                'Bitmex balance query result',
                currency=currency,
                amount=amount,
                usd_value=usd_value,
            )

        return returned_balances, ''

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:

        # We know user/walletHistory returns a list
        resp = self._api_query('user/walletHistory', {'currency': 'all'})
        log.debug(
            'Bitmex trade history query',
            results_num=len(resp),
            start_ts=start_ts,
            end_ts=end_ts,
        )

        margin_trades = []
        for tx in resp:
            timestamp = iso8601ts_to_timestamp(tx['timestamp']) if tx['timestamp'] is not None else None  # noqa: E501

            if (
                tx['transactType'] != 'RealisedPNL' or
                (timestamp and not start_ts <= timestamp <= end_ts)
            ):
                continue

            try:
                margin_trades.append(margin_trade_from_bitmex(tx))
            except (KeyError, UnknownAsset, DeserializationError) as e:
                msg = str(e) if not isinstance(e, KeyError) else f'missing key {e}'
                log.error(
                    f'Failed to process margin trade from bitmex {tx} due to {msg}. Skipping ...',
                )

        return margin_trades

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Sequence['HistoryBaseEntry']:
        resp = self._api_query('user/walletHistory', {'currency': 'all'})

        log.debug('Bitmex deposit/withdrawals query', results_num=len(resp))
        movements = []
        for movement in resp:
            try:
                transaction_type = movement['transactType']
                if transaction_type == 'Deposit':
                    event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL] = HistoryEventType.DEPOSIT  # noqa: E501
                elif transaction_type == 'Withdrawal':
                    event_type = HistoryEventType.WITHDRAWAL
                else:
                    continue

                timestamp = iso8601ts_to_timestamp(movement['timestamp'])
                if timestamp < start_ts:
                    continue
                if timestamp > end_ts:
                    continue

                asset = bitmex_to_world(movement['currency'])
                amount = deserialize_asset_amount_force_positive(movement['amount'])
                fee = deserialize_fee(movement.get('fee', 0))  # deposit has no fees

                if asset == A_BTC:
                    # bitmex stores amounts in satoshis
                    amount = AssetAmount(satoshis_to_btc(amount))
                    fee = Fee(satoshis_to_btc(fee))

                movements.extend(create_asset_movement_with_fee(
                    location=self.location,
                    location_label=self.name,
                    event_type=event_type,
                    timestamp=ts_sec_to_ms(timestamp),
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=fee,
                    unique_id=str(movement['transactID']),
                    extra_data=maybe_set_transaction_extra_data(
                        address=deserialize_asset_movement_address(movement, 'address', asset),
                        transaction_id=get_key_if_has_val(movement, 'tx'),
                    ),
                ))
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='deposit/withdrawal',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Unexpected data encountered during deserialization of a bitmex '
                    'asset movement. Check logs for details and open a bug report.',
                )
                log.error(
                    f'Unexpected data encountered during deserialization of bitmex '
                    f'asset_movement {movement}. Error was: {msg}',
                )
                continue
        return movements

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[Trade], tuple[Timestamp, Timestamp]]:
        return [], (start_ts, end_ts)  # noop for bitmex
