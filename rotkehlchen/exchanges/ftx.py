import hmac
import logging
import time
from collections import defaultdict
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Optional, Tuple, Set
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_ftx
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    Location,
    Timestamp,
    TradePair,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def trade_from_ftx(raw_trade: Dict[str, Any]) -> Optional[Trade]:
    """Turns a FTX transaction into a rotkehlchen Trade.

    Mary raise:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entires missing an expected entry
    """

    timestamp = deserialize_timestamp_from_date(raw_trade['time'], 'iso8601', 'FTX')
    trade_type = deserialize_trade_type(raw_trade['side'])

    base_asset = asset_from_ftx(raw_trade['baseCurrency'])
    quote_asset = asset_from_ftx(raw_trade['quoteCurrency'])

    amount = deserialize_asset_amount(raw_trade['size'])
    rate = deserialize_price(raw_trade['price'])

    fee_currency = asset_from_ftx(raw_trade['feeCurrency'])
    fee = deserialize_fee(raw_trade['fee'])

    return Trade(
        timestamp=timestamp,
        location=Location.FTX,
        pair=TradePair(f'{base_asset.identifier}_{quote_asset.identifier}'),
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(raw_trade['id']),
    )


class FTX(ExchangeInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__('FTX', api_key, secret, database)
        self.apiversion = 'v2'
        self.base_uri = 'https://ftx.com/api'
        self.msg_aggregator = msg_aggregator

    def first_connection(self) -> None:
        self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the FTX API key is good for usage in Rotki"""
        try:
            self._api_query('wallet/all_balances')
        except RemoteError as e:
            error = str(e)
            if 'Not logged in' in error:
                return False, 'Bad combination of API Keys'
            raise
        return True, ''

    def _api_query(
            self,
            endpoint: str,
            start_time: int = None,
            end_time: int = None,
            limit: int = 100,
            paginate: bool = True,
    ) -> Any:
        """Performs a FTX API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.
        If this is an ongoing paginating call then provide pagination_next_uri.
        If you want just the first results then set ignore_pagination to True.
        """
        request_verb = "GET"

        request_url = f'/{endpoint}'
        options = {}
        if limit is not None:
            options['limit'] = limit
        if start_time is not None:
            options['start_time'] = start_time
        if end_time is not None:
            options['end_time'] = end_time

        if len(options.keys()):
            request_url += urlencode(options)

        timestamp = int(time.time() * 1000)
        signature_payload = f'{timestamp}{request_verb}{request_url}'.encode()

        signature = hmac.new(self.secret, signature_payload, 'sha256').hexdigest()
        log.debug('FTX API query', request_url=request_url)

        self.session.headers.update({
            'FTX-KEY': self.api_key,
            'FTX-SIGN': signature,
            'FTX-TS': str(timestamp),
        })
        full_url = self.base_uri + request_url
        try:
            response = self.session.get(full_url)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'FTX API request failed due to {str(e)}') from e

        if response.status_code == 429:
            raise RemoteError('FTX rate limit exceeded')

        if response.status_code != 200:
            raise RemoteError(
                f'FTX query {full_url} responded with error status code: '
                f'{response.status_code} and text: {response.text}',
            )

        try:
            json_ret = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(f'FTX returned invalid JSON response: {response.text}') from e

        if 'data' not in json_ret:
            raise RemoteError(f'FTX json response does not contain data: {response.text}')

        final_data = json_ret['data']

        if len(final_data) == 0:
            return final_data

        # Do the pagination if needed

        ids: Set[int] = {r['id'] for r in final_data}
        end_time = min(
            deserialize_timestamp_from_date(t['time'], 'iso8601', 'ftx')
            for t in final_data
        )

        while paginate:
            step = self._api_query(
                endpoint=endpoint,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )

            # remove possible duplicates
            deduped = [r for r in step if r['id'] not in ids]
            ids |= {r['id'] for r in deduped}
            final_data.extend(step)

            if len(step) == 0:
                break
            end_time = min(
                deserialize_timestamp_from_date(t['time'], 'iso8601', 'ftx')
                for t in step
            )
            if len(step) < limit:
                break

        return final_data

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            resp = self._api_query('wallet/all_balances', paginate=False)
        except RemoteError as e:
            msg = (
                'FTX API request failed. Could not reach ftx due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        # flatten the list that maps accounts to balances
        balances = [x for _, bal in resp.items() for x in bal]

        # extract the balances and aggregate them
        returned_balances: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for balance_info in balances:
            try:
                amount = deserialize_asset_amount(balance_info['total'])

                # ignore empty balances. FTX returns zero for some coins
                # I believe those that the user previously owned
                if amount == ZERO:
                    continue

                asset = Asset(balance_info['coin'])

                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing coinbase balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                returned_balances[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX balance result with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX balance result with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a FTX account balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a FTX balance',
                    error=msg,
                )
                continue

        return dict(returned_balances), ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:

        raw_data = self._api_query('fills', start_time=start_ts, end_time=end_ts)
        log.debug('FTX buys/sells history result', results_num=len(raw_data))

        trades = []
        for raw_trade in raw_data:
            try:
                trade = trade_from_ftx(raw_trade)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX transaction with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX trade with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a FTX trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a FTX trade',
                    trade=raw_trade,
                    error=msg,
                )
                continue

            # limit coinbase trades in the requested time range here since there
            # is no argument in the API call
            if trade and trade.timestamp >= start_ts and trade.timestamp <= end_ts:
                trades.append(trade)

        return trades

    def _deserialize_asset_movement(self, raw_data: Dict[str, Any]) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from FTX and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data['status'] not in ('complete', 'confirmed'):
                return None

            timestamp = deserialize_timestamp_from_date(raw_data['time'], 'iso8601', 'FTX')

            amount = deserialize_asset_amount_force_positive(raw_data['size'])
            asset = asset_from_ftx(raw_data['coin'])

            # Only get address/transaction id for "send" type of transactions
            address = None
            transaction_id = None
            # movement_category: Union[Literal['deposit'], Literal['withdrawal']]
            if 'address' in raw_data:
                # Then this should be a "withdrawal". In the documentation address
                # seems to be a str but from tests it is a dict
                movement_category = AssetMovementCategory.WITHDRAWAL
                fee = deserialize_fee(raw_data['fee'])

                if isinstance(raw_data['address'], str):
                    address = str(string_to_ethereum_address(raw_data['address']))
                elif isinstance(raw_data['address'], dict):
                    address = deserialize_asset_movement_address(
                        raw_data['address']['address'],
                        'address',
                        asset,
                    )
                transaction_id = raw_data['txid']
            else:
                movement_category = AssetMovementCategory.DEPOSIT

            return AssetMovement(
                location=Location.FTX,
                category=movement_category,
                address=address,
                transaction_id=transaction_id,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee_asset=asset,
                fee=fee,
                link=str(raw_data['id']),
            )
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found FTX deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found FTX deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of a FTX '
                'asset movement. Check logs for details and open a bug report.',
            )
            log.error(
                f'Unexpected data encountered during deserialization of FTX '
                f'asset_movement {raw_data}. Error was: {str(e)}',
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        # Query in a while loop until we retrieve all the data
        raw_data = self._api_query('wallet/deposits', start_time=start_ts, end_time=end_ts)
        raw_data.extend(
            self._api_query('wallet/withdrawals', start_time=start_ts, end_time=end_ts),
        )

        log.debug('FTX deposits/withdrawals history result', results_num=len(raw_data))

        movements = []
        for raw_movement in raw_data:
            movement = self._deserialize_asset_movement(raw_movement)
            if movement:
                movements.append(movement)

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for FTX
