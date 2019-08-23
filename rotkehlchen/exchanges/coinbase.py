import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import ApiKey, ApiSecret, FilePath, Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import cache_response_timewise
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def trade_from_coinbase(raw_trade: Dict[str, Any]) -> Trade:
    """Turns a coinbase transaction into a rotkehlchen Trade.

    If the coinbase transaction is not a trade related transaction returns None

    Throws:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entires missing an expected entry
    """

    if raw_trade['instant']:
        raw_time = raw_trade['created_at']
    else:
        raw_time = raw_trade['payout_at']
    timestamp = deserialize_timestamp_from_date(raw_time, 'iso8601', 'coinbase')
    trade_type = deserialize_trade_type(raw_trade['resource'])
    tx_amount = deserialize_asset_amount(raw_trade['amount']['amount'])
    tx_asset = Asset(raw_trade['amount']['currency'])
    native_amount = deserialize_asset_amount(raw_trade['total']['amount'])
    native_asset = Asset(raw_trade['total']['currency'])
    # in coinbase you are buying/selling tx_asset for native_asset
    pair = TradePair(f'{tx_asset.identifier}_{native_asset.identifier}')
    amount = tx_amount
    # The rate is how much you get/give in quotecurrency if you buy/sell 1 unit of base currency
    rate = tx_amount / native_amount
    fee_amount = deserialize_fee(raw_trade['fee']['amount'])
    fee_asset = Asset(raw_trade['fee']['currency'])

    return Trade(
        timestamp=timestamp,
        location='coinbase',
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
    )


class CoinbasePermissionError(Exception):
    pass


class Coinbase(ExchangeInterface):

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            user_directory: FilePath,
            msg_aggregator: MessagesAggregator,
    ):
        super(Coinbase, self).__init__('coinbase', api_key, secret, user_directory)
        self.apiversion = 'v2'
        self.base_uri = 'https://api.coinbase.com'
        self.msg_aggregator = msg_aggregator

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _validate_single_api_key_action(
            self,
            method_str: str,
            ignore_pagination: bool = False,
    ) -> Tuple[Optional[List[Any]], str]:
        try:
            result = self._api_query(method_str, ignore_pagination=ignore_pagination)
        except CoinbasePermissionError as e:
            error = str(e)
            if 'transactions' in method_str:
                permission = 'wallet:transactions:read'
            elif 'accounts' in method_str:
                permission = 'wallet:accounts:read'
            elif 'buys' in method_str:
                permission = 'wallet:buys:read'
            elif 'sells' in method_str:
                permission = 'wallet:buys:read'
            else:
                raise AssertionError(
                    f'Unexpected coinbase method {method_str} at API key validation',
                )
            msg = (
                f'Provided API key needs to have {permission} permission activated. '
                f'Please log into your coinbase account and set all required permissions: '
                f'wallet:accounts:read, wallet:transactions:read, '
                f'wallet:buys:read, wallet:sells:read'
            )

            return None, msg
        except RemoteError as e:
            error = str(e)
            if 'invalid signature' in error:
                return None, 'Failed to authenticate with the Provided API key/secret'
            elif 'invalid api key' in error:
                return None, 'Provided API key is invalid'
            else:
                # any other remote error
                return None, error

        return result, ''

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Coinbase API key is good for usage in Rotkehlchen

        Makes sure that the following permissions are given to the key:
        - wallet:accounts:read
        """
        result, msg = self._validate_single_api_key_action('accounts')
        if not result:
            return False, msg

        # now get the account ids
        account_ids = self._get_account_ids(result)
        if len(account_ids) != 0:
            # and now try to get all transactions of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/transactions'
            result, msg = self._validate_single_api_key_action(method)
            if not result:
                return False, msg

            # and now try to get all buys of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/buys'
            result, msg = self._validate_single_api_key_action(method)
            if not result:
                return False, msg

            # and now try to get all sells of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/sells'
            result, msg = self._validate_single_api_key_action(method)
            if not result:
                return False, msg

        return True, ''

    def _get_account_ids(self, accounts: List[Dict[str, Any]]) -> List[str]:
        """Gets the account ids out of the accounts response"""
        account_ids = []
        for account_data in accounts:
            if 'id' not in account_data:
                self.msg_aggregator.add_error(
                    'Found coinbase account entry without an id key. Skipping it. ',
                )
                continue

            if not isinstance(account_data['id'], str):
                self.msg_aggregator.add_error(
                    f'Found coinbase account entry with a non string id: '
                    f'{account_data["id"]}. Skipping it. ',
                )
                continue

            account_ids.append(account_data['id'])

        return account_ids

    def _api_query(
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]] = None,
            pagination_next_uri: str = None,
            ignore_pagination: bool = False,
    ) -> List[Any]:
        """Performs a coinbase API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.
        If this is an ongoing paginating call then provide pagination_next_uri.
        If you want just the first results then set ignore_pagination to True.
        """
        request_verb = "GET"
        if pagination_next_uri:
            request_url = pagination_next_uri
        else:
            request_url = f'/{self.apiversion}/{endpoint}'
            if options:
                request_url += urlencode(options)

        timestamp = str(int(time.time()))
        message = timestamp + request_verb + request_url

        signature = hmac.new(
            self.secret,
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        log.debug('Coinbase API query', request_url=request_url)

        self.session.headers.update({
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key.decode(),
        })
        full_url = self.base_uri + request_url
        response = self.session.get(full_url)

        if response.status_code == 403:
            raise CoinbasePermissionError(f'API key does not have permission for {endpoint}')

        if response.status_code != 200:
            raise RemoteError(
                f'Coinbase query {full_url} responded with error status code: '
                f'{response.status_code} and text: {response.text}',
            )

        try:
            json_ret = rlk_jsonloads_dict(response.text)
        except JSONDecodeError:
            raise RemoteError(f'Coinbase returned invalid JSON response: {response.text}')

        if 'data' not in json_ret:
            raise RemoteError(f'Coinbase json response does not contain data: {response.text}')

        final_data = json_ret['data']

        # If we got pagination and this is the first query, gather all the subsequent queries
        if 'pagination' in json_ret and not pagination_next_uri and not ignore_pagination:
            while True:
                if 'next_uri' not in json_ret['pagination']:
                    raise RemoteError(f'Coinbase json response contained no "next_uri" key')

                next_uri = json_ret['pagination']['next_uri']
                if not next_uri:
                    # As per the docs: https://developers.coinbase.com/api/v2?python#pagination
                    # once we get an empty next_uri we are done
                    break

                additional_data = self._api_query(
                    endpoint=endpoint,
                    options=options,
                    pagination_next_uri=next_uri,
                )
                final_data.extend(additional_data)

        return final_data

    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[Dict[Asset, Dict[str, Any]]], str]:
        try:
            resp = self._api_query('accounts')
        except RemoteError as e:
            msg = (
                'Coinbase API request failed. Could not reach coinbase due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        returned_balances: Dict[Asset, Dict[str, Any]] = dict()
        for account in resp:
            try:
                if not account['balance']:
                    continue

                amount = deserialize_asset_amount(account['balance']['amount'])
                asset = Asset(account['balance']['currency'])

                usd_price = Inquirer().find_usd_price(asset=asset)
                if asset in returned_balances:
                    amount = returned_balances[asset]['amount'] + amount
                else:
                    returned_balances[asset] = {}

                returned_balances[asset]['amount'] = amount
                usd_value = returned_balances[asset]['amount'] * usd_price
                returned_balances[asset]['usd_value'] = usd_value

            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase balance result with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase balance result with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a coinbase account balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a coinbase account balance',
                    account_balance=account,
                    error=msg,
                )
                continue

        return returned_balances, ''

    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
    ) -> List[Trade]:
        cache = self.check_trades_cache_list(start_ts, end_at_least_ts)
        if cache is not None:
            raw_data = cache
        else:
            account_data = self._api_query('accounts')
            # now get the account ids and for each one query buys/sells
            # Looking at coinbase's API no other type of transaction
            # https://developers.coinbase.com/api/v2?python#list-transactions
            # consitutes something that Rotkehlchen would need to return in query_trade_history
            account_ids = self._get_account_ids(account_data)

            raw_data = []
            for account_id in account_ids:
                raw_data.extend(self._api_query(f'accounts/{account_id}/buys'))
                raw_data.extend(self._api_query(f'accounts/{account_id}/sells'))
            log.debug('coinbase buys/sells history result', results_num=len(raw_data))

        trades = []
        for raw_trade in raw_data:
            try:
                trade = trade_from_coinbase(raw_trade)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase transaction with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase trade with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a coinbase trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a coinbase trade',
                    trade=raw_trade,
                    error=msg,
                )
                continue

            if trade:
                trades.append(trade)

        return trades
