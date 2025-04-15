import base64
import hashlib
import hmac
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlparse

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import (
    HistoryEvent,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_movement_event_type,
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_fval_or_zero,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    iso8601ts_to_timestamp,
    timestamp_to_iso8601,
    ts_now,
    ts_sec_to_ms,
)
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


PRIME_BASE_URL: Final = 'https://api.prime.coinbase.com/v1'
COMPLETED_TRANSACTION_STATUS: Final = {
    'TRANSACTION_DONE',
    'TRANSACTION_IMPORTED',
}
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _process_trade(trade_data: dict[str, Any]) -> list[SwapEvent]:
    """Process trade from coinbase prime. Returns an empty list if the order can't be processed.
    May raise:
    - DeserializationError
    """
    try:
        if trade_data['status'] != 'FILLED':
            return []

        if (
            (not isinstance((product_id := trade_data['product_id']), str)) or
            len(pair_data := product_id.split('-')) != 2
        ):
            raise DeserializationError(
                f'Invalid product id {product_id} in Coinbase Prime trade {trade_data}',
            )

        base_asset = asset_from_coinbase(pair_data[0])
        quote_asset = asset_from_coinbase(pair_data[1])
        if (order_side := trade_data['side']) == 'BUY':
            spend_asset, receive_asset, = quote_asset, base_asset
        elif order_side == 'SELL':
            spend_asset, receive_asset, = base_asset, quote_asset
        else:
            raise DeserializationError(
                f'Unknown order side {order_side} in coinbase prime trade {trade_data}',
            )

        return create_swap_events(
            timestamp=ts_sec_to_ms(iso8601ts_to_timestamp(trade_data['created_at'])),
            location=Location.COINBASEPRIME,
            spend=AssetAmount(
                asset=spend_asset,
                amount=deserialize_fval(trade_data['filled_value']),
            ),
            receive=AssetAmount(
                asset=receive_asset,
                amount=deserialize_fval(trade_data['filled_quantity']),
            ),
            fee=AssetAmount(
                asset=quote_asset,
                amount=deserialize_fval(trade_data['commission']),
            ) if len(trade_data['commission']) != 0 else None,
            unique_id=str(trade_data['id']),
        )
    except KeyError as e:
        raise DeserializationError(
            f'Missing key {e} in Coinbase Prime trade {trade_data}',
        ) from e
    except UnknownAsset as e:
        raise DeserializationError(
            f'Unknown asset {e.identifier} in Coinbase Prime trade {trade_data}',
        ) from e


def _process_deposit_withdrawal(
        exchange_name: str,
        event_data: dict[str, Any],
) -> list[AssetMovement]:
    """Process asset movement from coinbase prime.
    Returns an empty list if the event can't be processed
    May raise:
    - DeserializationError
    """
    try:
        if event_data['status'] not in COMPLETED_TRANSACTION_STATUS:
            return []

        event_type = deserialize_asset_movement_event_type(event_data['type'])
        if event_type == HistoryEventType.DEPOSIT:
            address = event_data.get('transfer_from', {}).get('value')
        else:
            address = event_data.get('transfer_to', {}).get('value')

        amount = deserialize_fval_force_positive(event_data['amount'])
        fee = deserialize_fval_or_zero(event_data['fees'])
        timestamp = iso8601ts_to_timestamp(event_data['completed_at'] or event_data['created_at'])
        try:
            fee_asset = asset_from_coinbase(event_data['fee_symbol'])
            asset = asset_from_coinbase(event_data['symbol'])
        except UnknownAsset as e:
            raise DeserializationError(
                f'Unknown asset {e.identifier} seen in coinbase prime trade',
            ) from e

        return create_asset_movement_with_fee(
            location=Location.COINBASEPRIME,
            location_label=exchange_name,
            event_type=event_type,
            timestamp=ts_sec_to_ms(timestamp),
            asset=asset,
            amount=amount,
            fee_asset=fee_asset,
            fee=fee,
            unique_id=str(event_data['id']),
            extra_data=maybe_set_transaction_extra_data(
                address=address,
                transaction_id=event_data['blockchain_ids'][0] if len(event_data['blockchain_ids']) != 0 else None,  # noqa: E501
            ),
        )
    except KeyError as e:
        raise DeserializationError(
            f'Missing key {e} in asset movement information for Coinbase Prime',
        ) from e


def _process_conversions(raw_data: dict[str, Any]) -> list[HistoryEvent]:
    """Process conversion from coinbase prime
    May raise:
    - KeyError
    - DeserializationError
    """
    from_asset = asset_from_coinbase(raw_data['symbol'])
    to_asset = asset_from_coinbase(raw_data['destination_symbol'])
    converted_amount = deserialize_fval(
        value=raw_data['amount'],
        name='history_event',
        location='coinbase prime',
    )
    # If `completed_at` is missing, fall back to `created_at`.
    # We found cases where `completed_at` was None, so this ensures we always have a timestamp.
    timestamp_ms = ts_sec_to_ms(iso8601ts_to_timestamp(raw_data['completed_at'] or raw_data['created_at']))  # noqa: E501

    conversion_events = [
        HistoryEvent(
            event_identifier=raw_data['id'],
            sequence_index=0,
            timestamp=timestamp_ms,
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            amount=converted_amount,
            asset=from_asset,
            notes=f'Swap {converted_amount} {from_asset.symbol} in Coinbase Prime',
        ), HistoryEvent(
            event_identifier=raw_data['id'],
            sequence_index=1,
            timestamp=timestamp_ms,
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            amount=converted_amount,
            asset=to_asset,
            notes=f'Receive {converted_amount} {to_asset.symbol} from a Coinbase Prime conversion',
        ),
    ]

    if (fee_amount := deserialize_fval(
        value=raw_data['fees'],
        name='history_event',
        location='coinbase prime',
    )) != ZERO:
        conversion_events.append(HistoryEvent(
            event_identifier=raw_data['id'],
            sequence_index=2,
            timestamp=timestamp_ms,
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            amount=fee_amount,
            asset=(fee_asset := asset_from_coinbase(raw_data['fee_symbol'])),
            notes=f'Spend {fee_amount} {fee_asset.symbol} as Coinbase Prime conversion fee',
        ))

    return conversion_events


def _process_reward(raw_data: dict[str, Any]) -> list[HistoryEvent]:
    """Process rewards from coinbase prime.
    At the moment of writing this logic we don't have any real example, only the docs
    so it might need adjustment in the future.

    May raise:
    - DeserializationError
    - KeyError
    """
    return [HistoryEvent(
        event_identifier=raw_data['id'],
        sequence_index=0,
        timestamp=ts_sec_to_ms(iso8601ts_to_timestamp(raw_data['completed_at'] or raw_data['created_at'])),  # noqa: E501
        location=Location.COINBASEPRIME,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        amount=(amount := deserialize_fval(
            value=raw_data['amount'],
            name='history_event reward',
            location='coinbase prime',
        )),
        asset=(asset := asset_from_coinbase(raw_data['symbol'])),
        notes=f'Receive {amount} {asset.symbol} as Coinbase Prime staking reward',
    )]


class Coinbaseprime(ExchangeInterface):

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            passphrase: str,
    ):
        super().__init__(
            name=name,
            location=Location.COINBASEPRIME,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.api_passphrase = passphrase
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-CB-ACCESS-KEY': self.api_key,
            'X-CB-ACCESS-PASSPHRASE': self.api_passphrase,
        })

    def validate_api_key(self) -> tuple[bool, str]:
        try:
            self._get_portfolio_ids()
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def edit_exchange_credentials(self, credentials: 'ExchangeAuthCredentials') -> bool:
        if super().edit_exchange_credentials(credentials) is False:
            return False

        if credentials.api_key is not None:
            self.session.headers.update({'X-CB-ACCESS-KEY': self.api_key})
        if credentials.passphrase is not None:
            self.api_passphrase = credentials.passphrase

        return True

    def sign(self, timestamp: Timestamp, url_path: str) -> bytes:
        """Sign requests for coinbase prime"""
        message = f'{timestamp}GET{url_path}'
        hmac_message = hmac.digest(self.secret, message.encode(), hashlib.sha256)
        return base64.b64encode(hmac_message)

    def _api_query(
            self,
            module: Literal['portfolios'],
            path: str = '',
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        uri = f'{PRIME_BASE_URL}/{module}'
        if path != '':
            uri += f'/{path}'

        url_path = urlparse(uri).path
        self.session.headers.update({
            'X-CB-ACCESS-TIMESTAMP': str(timestamp := ts_now()),
            'X-CB-ACCESS-SIGNATURE': self.sign(timestamp, url_path),
        })
        log.debug(f'Querying coinbase prime module {module}/{path} with {params=}')
        try:
            response = self.session.get(url=uri, params=params)
        except requests.RequestException as e:
            raise RemoteError(f'Coinbase Prime API request failed due to {e}') from e

        try:
            data = response.json()
        except requests.JSONDecodeError as e:
            raise RemoteError(f'Coinbase Prime returned invalid json {response.text}') from e

        return data

    def _decode_history_events(
            self,
            raw_data: dict[str, Any],
    ) -> Sequence[HistoryEvent | AssetMovement]:
        """Process transaction as history events from coinbase prime
        May raise:
        - DeserializationError
        """
        try:
            if (tx_type := raw_data['type']) == 'CONVERSION':
                return _process_conversions(raw_data)
            elif tx_type == 'REWARD':
                return _process_reward(raw_data)
            elif tx_type in ['DEPOSIT', 'WITHDRAWAL', 'COINBASE_DEPOSIT']:
                return _process_deposit_withdrawal(exchange_name=self.name, event_data=raw_data)
        except KeyError as e:
            log.error(f'Missing key {e} when processing history events at coinbase prime')
            raise DeserializationError(
                'Unexpected format in coinbase prime event. Check logs for more details',
            ) from e

        log.error(f'Unknown tx_type in {raw_data} at coinbase prime')
        raise DeserializationError(f'Unknown transaction type in coinbase prime {tx_type}')

    def _query_paginated_endpoint(
            self,
            query_params: dict[str, Any],
            portfolio_id: str,
            method: Literal['orders', 'transactions'],
            decoding_logic: Callable[[dict[str, Any]], Sequence[HistoryEvent | AssetMovement | SwapEvent]],  # noqa: E501
    ) -> Sequence[HistoryEvent | AssetMovement | SwapEvent]:
        """Abstraction to consume all the events in the selected queries.
        It uses the `decoding_logic` to process the different events and returns a list
        whose contents depend on the function's called arguments.

        This function may raise:
        - RemoteError
        """
        result: list[HistoryEvent | AssetMovement | SwapEvent] = []
        while True:
            response = self._api_query(
                module='portfolios',
                path=f'{portfolio_id}/{method}',
                params=query_params,
            )

            for raw_event in response[method]:
                try:
                    if len(events := decoding_logic(raw_event)) == 0:
                        log.warning(
                            f'Wont process event {raw_event} from coinbase prime. Skipping',
                        )
                    else:
                        result.extend(events)
                except DeserializationError as e:
                    self.msg_aggregator.add_error(
                        f'Failed to process coinbase prime event due to {e}. Skipping entry...',
                    )

            if (
                response['pagination']['has_next'] is True and
                (new_cursor := response['pagination'].get('next_cursor', '')) != ''
            ):
                query_params['cursor'] = new_cursor
            else:
                break

        return result

    def _get_portfolio_ids(self) -> list[str]:
        """
        Get id of the different portfolios linked to the api keys.
        May raise: RemoteError
        """
        data: dict[str, list] = self._api_query(module='portfolios')
        try:
            ids = [portfolio['id'] for portfolio in data['portfolios']]
        except KeyError as e:
            log.error(
                f'Malformed portfolios response from coinbase prime {data}. Missing key {e}',
            )
            raise RemoteError(
                'Malformed porfolios ids response in coinbase prime. Check logs for more details',
            ) from e

        return ids

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            portfolio_ids = self._get_portfolio_ids()
        except RemoteError as e:
            msg_prefix = 'Coinbase Prime API request failed.'
            msg = (
                'Coinbase Prime API request failed. Could not reach coinbase due '
                f'to {e}'
            )
            log.error(f'{msg_prefix} Could not reach coinbase due to {e}')
            return None, f'{msg_prefix} Check logs for more details'

        returned_balances: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for account_id in portfolio_ids:
            try:
                balances_query: dict[str, list[dict[str, Any]]] = self._api_query(
                    module='portfolios',
                    path=f'{account_id}/balances',
                )
            except RemoteError as e:
                log.error(f'Failed to query CoinbasePrime balances due to {e}')
                return None, 'Request to CoinbasePrime failed to fetch balances'

            for balance_entry in balances_query['balances']:
                try:
                    total_balance = ZERO
                    for balance_key in (
                        'amount',  # The `amount` field includes the amount in the `holds` field
                        'bonded_amount',
                        'reserved_amount'  # Amount that must remain in the wallet due to the protocol, in whole units  # noqa: E501
                        'unbonding_amount',
                        'unvested_amount',
                        'pending_rewards_amount',
                    ):
                        total_balance += deserialize_fval(balance_entry.get(balance_key, ZERO))

                    # ignore empty balances. Coinbase returns zero balances for everything
                    # a user does not own
                    if total_balance == ZERO:
                        continue

                    asset = asset_from_coinbase(balance_entry['symbol'])
                    try:
                        usd_price = Inquirer.find_usd_price(asset=asset)
                    except RemoteError as e:
                        log.error(
                            f'Error processing coinbase balance entry due to inability to '
                            f'query USD price: {e!s}. Skipping balance entry',
                        )
                        continue

                    returned_balances[asset] += Balance(
                        amount=total_balance,
                        usd_value=total_balance * usd_price,
                    )
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='balance query',
                    )
                except UnsupportedAsset as e:
                    log.warning(
                        f'Found coinbase prime balance result with unsupported asset '
                        f'{e.identifier}. Ignoring it.',
                    )
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    log.error(
                        'Error processing a coinbase prime account balance',
                        account_balance=account_id,
                        error=msg,
                    )

        return dict(returned_balances), ''

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        events: list[HistoryEvent | AssetMovement | SwapEvent] = []
        for portfolio_id in self._get_portfolio_ids():
            events.extend(self._query_paginated_endpoint(
                query_params={
                    'sort_direction': 'ASC',
                    'start_time': timestamp_to_iso8601(start_ts),
                    'end_time': timestamp_to_iso8601(end_ts),
                    'types': ['CONVERSION', 'REWARD', 'DEPOSIT', 'WITHDRAWAL', 'COINBASE_DEPOSIT'],
                },
                portfolio_id=portfolio_id,
                method='transactions',
                decoding_logic=self._decode_history_events,
            ))
            events.extend(self._query_paginated_endpoint(
                query_params={
                    'sort_direction': 'ASC',
                    'order_statuses': ['FILLED'],
                    'start_date': timestamp_to_iso8601(start_ts),
                    'end_date': timestamp_to_iso8601(end_ts),
                },
                portfolio_id=portfolio_id,
                method='orders',
                decoding_logic=_process_trade,
            ))

        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []
