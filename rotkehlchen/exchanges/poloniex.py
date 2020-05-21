import csv
import hashlib
import hmac
import logging
import os
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, overload
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_poloniex
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Loan,
    Trade,
    TradeType,
    invert_pair,
    trade_pair_from_assets,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter, make_sensitive
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp,
    deserialize_timestamp_from_poloniex_date,
    deserialize_trade_type,
    get_pair_position_str,
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
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import create_timestamp, ts_now_in_ms
from rotkehlchen.utils.serialization import rlk_jsonloads_dict, rlk_jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def trade_from_poloniex(poloniex_trade: Dict[str, Any], pair: TradePair) -> Trade:
    """Turn a poloniex trade returned from poloniex trade history to our common trade
    history format

    Throws:
        - UnsupportedAsset due to asset_from_poloniex()
        - DeserializationError due to the data being in unexpected format
        - UnprocessableTradePair due to the pair data being in an unexpected format
    """

    try:
        trade_type = deserialize_trade_type(poloniex_trade['type'])
        amount = deserialize_asset_amount(poloniex_trade['amount'])
        rate = deserialize_price(poloniex_trade['rate'])
        perc_fee = deserialize_fee(poloniex_trade['fee'])
        base_currency = asset_from_poloniex(get_pair_position_str(pair, 'first'))
        quote_currency = asset_from_poloniex(get_pair_position_str(pair, 'second'))
        timestamp = deserialize_timestamp_from_poloniex_date(poloniex_trade['date'])
    except KeyError as e:
        raise DeserializationError(
            f'Poloniex trade deserialization error. Missing key entry for {str(e)} in trade dict',
        )

    cost = rate * amount
    if trade_type == TradeType.BUY:
        fee = Fee(amount * perc_fee)
        fee_currency = quote_currency
    elif trade_type == TradeType.SELL:
        fee = Fee(cost * perc_fee)
        fee_currency = base_currency
    else:
        raise DeserializationError(f'Got unexpected trade type "{trade_type}" for poloniex trade')

    if poloniex_trade['category'] == 'settlement':
        if trade_type == TradeType.BUY:
            trade_type = TradeType.SETTLEMENT_BUY
        else:
            trade_type = TradeType.SETTLEMENT_SELL

    log.debug(
        'Processing poloniex Trade',
        sensitive_log=True,
        timestamp=timestamp,
        order_type=trade_type,
        pair=pair,
        base_currency=base_currency,
        quote_currency=quote_currency,
        amount=amount,
        fee=fee,
        rate=rate,
    )

    # Use the converted assets in our pair
    pair = trade_pair_from_assets(base_currency, quote_currency)
    # Since in Poloniex the base currency is the cost currency, iow in poloniex
    # for BTC_ETH we buy ETH with BTC and sell ETH for BTC, we need to turn it
    # into the Rotkehlchen way which is following the base/quote approach.
    pair = invert_pair(pair)
    return Trade(
        timestamp=timestamp,
        location=Location.POLONIEX,
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(poloniex_trade['globalTradeID']),
    )


def process_polo_loans(
        msg_aggregator: MessagesAggregator,
        data: List[Dict],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[Loan]:
    """Takes in the list of loans from poloniex as returned by the return_lending_history
    api call, processes it and returns it into our loan format
    """
    new_data = []

    for loan in reversed(data):
        log.debug('processing poloniex loan', **make_sensitive(loan))
        try:
            close_time = deserialize_timestamp_from_poloniex_date(loan['close'])
            open_time = deserialize_timestamp_from_poloniex_date(loan['open'])
            if open_time < start_ts:
                continue
            if close_time > end_ts:
                continue

            our_loan = Loan(
                location=Location.POLONIEX,
                open_time=open_time,
                close_time=close_time,
                currency=asset_from_poloniex(loan['currency']),
                fee=deserialize_fee(loan['fee']),
                earned=deserialize_asset_amount(loan['earned']),
                amount_lent=deserialize_asset_amount(loan['amount']),
            )
        except UnsupportedAsset as e:
            msg_aggregator.add_warning(
                f'Found poloniex loan with unsupported asset'
                f' {e.asset_name}. Ignoring it.',
            )
            continue
        except UnknownAsset as e:
            msg_aggregator.add_warning(
                f'Found poloniex loan with unknown asset'
                f' {e.asset_name}. Ignoring it.',
            )
            continue
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            msg_aggregator.add_error(
                'Deserialization error while reading a poloniex loan. Check '
                'logs for more details. Ignoring it.',
            )
            log.error(
                'Deserialization error while reading a poloniex loan',
                loan=loan,
                error=msg,
            )
            continue

        new_data.append(our_loan)

    new_data.sort(key=lambda loan: loan.open_time)
    return new_data


def _post_process(before: Dict) -> Dict:
    """Poloniex uses datetimes so turn them into timestamps here"""
    after = before
    if('return' in after):
        if(isinstance(after['return'], list)):
            for x in range(0, len(after['return'])):
                if(isinstance(after['return'][x], dict)):
                    if('datetime' in after['return'][x] and
                       'timestamp' not in after['return'][x]):
                        after['return'][x]['timestamp'] = float(
                            create_timestamp(after['return'][x]['datetime']),
                        )

    return after


class Poloniex(ExchangeInterface):

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super(Poloniex, self).__init__('poloniex', api_key, secret, database)

        self.uri = 'https://poloniex.com/'
        self.public_uri = self.uri + 'public?command='
        self.session.headers.update({
            'Key': self.api_key,
        })
        self.msg_aggregator = msg_aggregator
        self.nonce_lock = Semaphore()

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self.return_fee_info()
        except RemoteError as e:
            error = str(e)
            if 'Invalid API key' in error:
                return False, 'Provided API Key or secret is invalid'
            else:
                raise
        return True, ''

    def api_query_dict(self, command: str, req: Optional[Dict] = None) -> Dict:
        result = self._api_query(command, req)
        assert isinstance(result, Dict)
        return result

    def api_query_list(self, command: str, req: Optional[Dict] = None) -> List:
        result = self._api_query(command, req)
        assert isinstance(result, List)
        return result

    def _single_query(self, command: str, req: Dict[str, Any]) -> Optional[requests.Response]:
        """A single api query for poloniex

        Returns the response if all went well or None if a recoverable poloniex
        error occured such as a 504.

        Can raise:
         - RemoteError if there is a problem with the response
         - ConnectionError if there is a problem connecting to poloniex.
        """
        if command == 'returnTicker' or command == 'returnCurrencies':
            log.debug(f'Querying poloniex for {command}')
            response = self.session.get(self.public_uri + command)
        else:
            req['command'] = command
            with self.nonce_lock:
                # Protect this region with a lock since poloniex will reject
                # non-increasing nonces. So if two greenlets come in here at
                # the same time one of them will fail
                req['nonce'] = ts_now_in_ms()
                post_data = str.encode(urlencode(req))

                sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
                self.session.headers.update({'Sign': sign})
                response = self.session.post('https://poloniex.com/tradingApi', req)

        if response.status_code == 504:
            # backoff and repeat
            return None
        elif response.status_code != 200:
            raise RemoteError(
                f'Poloniex query responded with error status code: {response.status_code}'
                f' and text: {response.text}',
            )

        # else all is good
        return response

    def _api_query(self, command: str, req: Optional[Dict] = None) -> Union[Dict, List]:
        """An api query to poloniex. May make multiple requests

        Can raise:
         - RemoteError if there is a problem reaching poloniex or with the returned response
        """
        if req is None:
            req = {}
        log.debug(
            'Poloniex API query',
            command=command,
            post_data=req,
        )

        tries = QUERY_RETRY_TIMES
        while tries >= 0:
            try:
                response = self._single_query(command, req)
            except requests.exceptions.ConnectionError as e:
                raise RemoteError(f'Poloniex API request failed due to {str(e)}')

            if response is None:
                if tries >= 1:
                    backoff_seconds = 20 / tries
                    log.debug(
                        f'Got a recoverable poloniex error. '
                        f'Backing off for {backoff_seconds}',
                    )
                    gevent.sleep(backoff_seconds)
                    tries -= 1
                    continue
            else:
                break

        if response is None:
            raise RemoteError(
                f'Got a recoverable poloniex error and did not manage to get a '
                f'request through even after {QUERY_RETRY_TIMES} '
                f'incremental backoff retries',
            )

        result: Union[Dict, List]
        try:
            if command == 'returnLendingHistory':
                result = rlk_jsonloads_list(response.text)
            else:
                # For some reason poloniex can also return [] for an empty trades result
                if response.text == '[]':
                    result = {}
                else:
                    result = rlk_jsonloads_dict(response.text)
                    result = _post_process(result)
        except JSONDecodeError:
            raise RemoteError(f'Poloniex returned invalid JSON response: {response.text}')

        if isinstance(result, dict) and 'error' in result:
            raise RemoteError(
                'Poloniex query for "{}" returned error: {}'.format(
                    command,
                    result['error'],
                ))

        return result

    def return_currencies(self) -> Dict:
        response = self.api_query_dict('returnCurrencies')
        return response

    def return_fee_info(self) -> Dict:
        response = self.api_query_dict('returnFeeInfo')
        return response

    def return_lending_history(
            self,
            start_ts: Optional[Timestamp] = None,
            end_ts: Optional[Timestamp] = None,
            limit: Optional[int] = None,
    ) -> List:
        """Default limit for this endpoint seems to be 500 when I tried.
        So to be sure all your loans are included put a very high limit per call
        and also check if the limit was reached after each call.

        Also maximum limit seems to be 12660
        """
        req: Dict[str, Union[int, Timestamp]] = {}
        if start_ts is not None:
            req['start'] = start_ts
        if end_ts is not None:
            req['end'] = end_ts
        if limit is not None:
            req['limit'] = limit

        response = self.api_query_list('returnLendingHistory', req)
        return response

    @overload
    def return_trade_history(  # pylint: disable=unused-argument, no-self-use
            self,
            currency_pair: Literal['all'],
            start: Timestamp,
            end: Timestamp,
    ) -> Dict:
        ...

    @overload  # noqa: F811
    def return_trade_history(   # noqa: F811  # pylint: disable=unused-argument, no-self-use
            self,
            currency_pair: Union[TradePair, str],
            start: Timestamp,
            end: Timestamp,
    ) -> Union[Dict, List]:
        ...

    # TODO: As soon as a pyflakes release is made including
    # https://github.com/PyCQA/pyflakes/pull/435 then remove the noqa from here,
    # above and from other place in codebase where overload is used likethis
    def return_trade_history(  # noqa: F811
            self,
            currency_pair: Union[TradePair, str],
            start: Timestamp,
            end: Timestamp,
    ) -> Union[Dict, List]:
        """If `currency_pair` is all, then it returns a dictionary with each key
        being a pair and each value a list of trades. If `currency_pair` is a specific
        pair then a list is returned"""
        return self._api_query('returnTradeHistory', {
            'currencyPair': currency_pair,
            'start': start,
            'end': end,
            'limit': 10000,
        })

    def return_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Dict:
        response = self.api_query_dict(
            'returnDepositsWithdrawals',
            {'start': start_ts, 'end': end_ts},
        )
        return response

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[Dict[Asset, Dict[str, Any]]], str]:
        try:
            resp = self.api_query_dict('returnCompleteBalances', {"account": "all"})
        except RemoteError as e:
            msg = (
                'Poloniex API request failed. Could not reach poloniex due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        balances = {}
        for poloniex_asset, v in resp.items():
            available = FVal(v['available'])
            on_orders = FVal(v['onOrders'])
            if (available != FVal(0) or on_orders != FVal(0)):
                try:
                    asset = asset_from_poloniex(poloniex_asset)
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unsupported poloniex asset {e.asset_name}. '
                        f' Ignoring its balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown poloniex asset {e.asset_name}. '
                        f' Ignoring its balance query.',
                    )
                    continue
                except DeserializationError:
                    log.error(
                        f'Unexpected poloniex asset type. Expected string '
                        f' but got {type(poloniex_asset)}',
                    )
                    self.msg_aggregator.add_error(
                        'Found poloniex asset entry with non-string type. '
                        ' Ignoring its balance query.',
                    )
                    continue

                entry = {}
                entry['amount'] = available + on_orders
                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing poloniex balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                usd_value = entry['amount'] * usd_price
                entry['usd_value'] = usd_value
                balances[asset] = entry

                log.debug(
                    'Poloniex balance query',
                    sensitive_log=True,
                    currency=asset,
                    amount=entry['amount'],
                    usd_value=usd_value,
                )

        return balances, ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        raw_data = self.return_trade_history(
            currency_pair='all',
            start=start_ts,
            end=end_ts,
        )

        results_length = 0
        for _, v in raw_data.items():
            results_length += len(v)

        log.debug('Poloniex trade history query', results_num=results_length)

        if results_length >= 10000:
            raise ValueError(
                'Poloniex api has a 10k limit to trade history. Have not implemented'
                ' a solution for more than 10k trades at the moment',
            )

        our_trades = []
        for pair, trades in raw_data.items():
            for trade in trades:
                category = trade.get('category', None)
                try:
                    if category == 'exchange' or category == 'settlement':
                        timestamp = deserialize_timestamp_from_poloniex_date(trade['date'])
                        if timestamp < start_ts or timestamp > end_ts:
                            continue
                        our_trades.append(trade_from_poloniex(trade, TradePair(pair)))
                    elif category == 'marginTrade':
                        # We don't take poloniex margin trades into account at the moment
                        continue
                    else:
                        self.msg_aggregator.add_error(
                            f'Error deserializing a poloniex trade. Unknown trade '
                            f'category {category} found.',
                        )
                        continue
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found poloniex trade with unsupported asset'
                        f' {e.asset_name}. Ignoring it.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found poloniex trade with unknown asset'
                        f' {e.asset_name}. Ignoring it.',
                    )
                    continue
                except (UnprocessableTradePair, DeserializationError) as e:
                    self.msg_aggregator.add_error(
                        'Error deserializing a poloniex trade. Check the logs '
                        'and open a bug report.',
                    )
                    log.error(
                        'Error deserializing poloniex trade',
                        trade=trade,
                        error=str(e),
                    )
                    continue

        return our_trades

    def parse_loan_csv(self) -> List:
        """Parses (if existing) the lendingHistory.csv and returns the history in a list

        It can throw OSError, IOError if the file does not exist and csv.Error if
        the file is not proper CSV"""
        # the default filename, and should be (if at all) inside the data directory
        path = os.path.join(self.db.user_data_dir, "lendingHistory.csv")
        lending_history = []
        with open(path, 'r') as csvfile:
            history = csv.reader(csvfile, delimiter=',', quotechar='|')
            next(history)  # skip header row
            for row in history:
                try:
                    lending_history.append({
                        'currency': asset_from_poloniex(row[0]),
                        'earned': FVal(row[6]),
                        'amount': FVal(row[2]),
                        'fee': FVal(row[5]),
                        'open': row[7],
                        'close': row[8],
                    })
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found loan with asset {e.asset_name}. Ignoring it.',
                    )
                    continue

        return lending_history

    def query_loan_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            from_csv: Optional[bool] = False,
    ) -> List:
        """
        WARNING: Querying from returnLendingHistory endpoint instead of reading from
        the CSV file can potentially return unexpected/wrong results.

        That is because the `returnLendingHistory` endpoint has a hidden limit
        of 12660 results. In our code we use the limit of 12000 but poloniex may change
        the endpoint to have a lower limit at which case this code will break.

        To be safe compare results of both CSV and endpoint to make sure they agree!
        """
        try:
            if from_csv:
                return self.parse_loan_csv()
        except (OSError, csv.Error):
            pass

        loans_query_return_limit = 12000
        result = self.return_lending_history(
            start_ts=start_ts,
            end_ts=end_ts,
            limit=loans_query_return_limit,
        )
        data = list(result)
        log.debug('Poloniex loan history query', results_num=len(data))

        # since I don't think we have any guarantees about order of results
        # using a set of loan ids is one way to make sure we get no duplicates
        # if poloniex can guarantee me that the order is going to be ascending/descending
        # per open/close time then this can be improved
        id_set = set()

        while len(result) == loans_query_return_limit:
            # Find earliest timestamp to re-query the next batch
            min_ts = end_ts
            for loan in result:
                ts = deserialize_timestamp_from_poloniex_date(loan['close'])
                min_ts = min(min_ts, ts)
                id_set.add(loan['id'])

            result = self.return_lending_history(
                start_ts=start_ts,
                end_ts=min_ts,
                limit=loans_query_return_limit,
            )
            log.debug('Poloniex loan history query', results_num=len(result))
            for loan in result:
                if loan['id'] not in id_set:
                    data.append(loan)

        return data

    def query_exchange_specific_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Optional[Any]:
        """The exchange specific history for poloniex is its loans"""
        return self.query_loan_history(
            start_ts=start_ts,
            end_ts=end_ts,
            from_csv=True,  # TODO: Change this and make them queriable
        )

    def _deserialize_asset_movement(
            self,
            movement_type: AssetMovementCategory,
            movement_data: Dict[str, Any],
    ) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from polo and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if movement_type == AssetMovementCategory.DEPOSIT:
                fee = Fee(ZERO)
                uid_key = 'depositNumber'
            else:
                fee = deserialize_fee(movement_data['fee'])
                uid_key = 'withdrawalNumber'
            asset = asset_from_poloniex(movement_data['currency'])
            return AssetMovement(
                location=Location.POLONIEX,
                category=movement_type,
                timestamp=deserialize_timestamp(movement_data['timestamp']),
                asset=asset,
                amount=deserialize_asset_amount(movement_data['amount']),
                fee_asset=asset,
                fee=fee,
                link=str(movement_data[uid_key]),
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(movement_type)} of unsupported poloniex asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(movement_type)} of unknown poloniex asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of a poloniex '
                'asset movement. Check logs for details and open a bug report.',
            )
            log.error(
                f'Unexpected data encountered during deserialization of poloniex '
                f'{str(movement_type)}: {movement_data}. Error was: {str(e)}',
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        result = self.return_deposits_withdrawals(start_ts, end_ts)
        log.debug(
            'Poloniex deposits/withdrawal query',
            results_num=len(result['withdrawals']) + len(result['deposits']),
        )

        movements = []
        for withdrawal in result['withdrawals']:
            asset_movement = self._deserialize_asset_movement(
                movement_type=AssetMovementCategory.WITHDRAWAL,
                movement_data=withdrawal,
            )
            if asset_movement:
                movements.append(asset_movement)

        for deposit in result['deposits']:
            asset_movement = self._deserialize_asset_movement(
                movement_type=AssetMovementCategory.DEPOSIT,
                movement_data=deposit,
            )
            if asset_movement:
                movements.append(asset_movement)

        return movements
