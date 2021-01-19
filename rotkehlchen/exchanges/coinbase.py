import hashlib
import hmac
import logging
import time
from collections import defaultdict
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradePair,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def trade_from_coinbase(raw_trade: Dict[str, Any]) -> Optional[Trade]:
    """Turns a coinbase transaction into a rotkehlchen Trade.

    https://developers.coinbase.com/api/v2?python#buys
    If the coinbase transaction is not a trade related transaction returns None

    Throws:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entires missing an expected entry
    """

    if raw_trade['status'] != 'completed':
        # We only want to deal with completed trades
        return None

    if raw_trade['instant']:
        raw_time = raw_trade['created_at']
    else:
        raw_time = raw_trade['payout_at']
    timestamp = deserialize_timestamp_from_date(raw_time, 'iso8601', 'coinbase')
    trade_type = deserialize_trade_type(raw_trade['resource'])
    tx_amount = deserialize_asset_amount(raw_trade['amount']['amount'])
    tx_asset = asset_from_coinbase(raw_trade['amount']['currency'], time=timestamp)
    native_amount = deserialize_asset_amount(raw_trade['subtotal']['amount'])
    native_asset = asset_from_coinbase(raw_trade['subtotal']['currency'], time=timestamp)
    # in coinbase you are buying/selling tx_asset for native_asset
    pair = TradePair(f'{tx_asset.identifier}_{native_asset.identifier}')
    amount = tx_amount
    # The rate is how much you get/give in quotecurrency if you buy/sell 1 unit of base currency
    rate = Price(native_amount / tx_amount)
    fee_amount = deserialize_fee(raw_trade['fee']['amount'])
    fee_asset = asset_from_coinbase(raw_trade['fee']['currency'], time=timestamp)

    return Trade(
        timestamp=timestamp,
        location=Location.COINBASE,
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
        link=str(raw_trade['id']),
    )


class CoinbasePermissionError(Exception):
    pass


class Coinbase(ExchangeInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__('coinbase', api_key, secret, database)
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
            elif 'buys' in method_str:
                permission = 'wallet:buys:read'
            elif 'sells' in method_str:
                permission = 'wallet:sells:read'
            elif 'deposits' in method_str:
                permission = 'wallet:deposits:read'
            elif 'withdrawals' in method_str:
                permission = 'wallet:withdrawals:read'
            elif 'trades' in method_str:
                permission = 'wallet:trades:read'
            # the accounts elif should be at the end since the word appears
            # in other endpoints
            elif 'accounts' in method_str:
                permission = 'wallet:accounts:read'
            else:
                raise AssertionError(
                    f'Unexpected coinbase method {method_str} at API key validation',
                ) from e
            msg = (
                f'Provided Coinbase API key needs to have {permission} permission activated. '
                f'Please log into your coinbase account and set all required permissions: '
                f'wallet:accounts:read, wallet:transactions:read, '
                f'wallet:buys:read, wallet:sells:read, wallet:withdrawals:read, '
                f'wallet:deposits:read, wallet:trades:read'
            )

            return None, msg
        except RemoteError as e:
            error = str(e)
            if 'invalid signature' in error:
                return None, 'Failed to authenticate with the Provided API key/secret'
            if 'invalid api key' in error:
                return None, 'Provided API Key is invalid'
            # else any other remote error
            return None, error

        return result, ''

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Coinbase API key is good for usage in Rotki

        Makes sure that the following permissions are given to the key:
        wallet:accounts:read, wallet:transactions:read,
        wallet:buys:read, wallet:sells:read, wallet:withdrawals:read,
        wallet:deposits:read
        """
        result, msg = self._validate_single_api_key_action('accounts')
        if result is None:
            return False, msg

        # now get the account ids
        account_ids = self._get_account_ids(result)
        if len(account_ids) != 0:
            # and now try to get all transactions of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/transactions'
            result, msg = self._validate_single_api_key_action(method)
            if result is None:
                return False, msg

            # and now try to get all buys of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/buys'
            result, msg = self._validate_single_api_key_action(method)
            if result is None:
                return False, msg

            # and now try to get all sells of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/sells'
            result, msg = self._validate_single_api_key_action(method)
            if result is None:
                return False, msg

            # and now try to get all deposits of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/deposits'
            result, msg = self._validate_single_api_key_action(method)
            if result is None:
                return False, msg

            # and now try to get all withdrawals of an account to see if that's possible
            method = f'accounts/{account_ids[0]}/withdrawals'
            result, msg = self._validate_single_api_key_action(method)
            if result is None:
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
            'CB-ACCESS-KEY': self.api_key,
            # This is needed to guarantee the up to the given date
            # API version response.
            'CB-VERSION': '2019-08-25',
        })
        full_url = self.base_uri + request_url
        try:
            response = self.session.get(full_url)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Coinbase API request failed due to {str(e)}') from e

        if response.status_code == 403:
            raise CoinbasePermissionError(f'API key does not have permission for {endpoint}')

        if response.status_code != 200:
            raise RemoteError(
                f'Coinbase query {full_url} responded with error status code: '
                f'{response.status_code} and text: {response.text}',
            )

        try:
            json_ret = rlk_jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(f'Coinbase returned invalid JSON response: {response.text}') from e

        if 'data' not in json_ret:
            raise RemoteError(f'Coinbase json response does not contain data: {response.text}')

        final_data = json_ret['data']

        # If we got pagination and this is the first query, gather all the subsequent queries
        if 'pagination' in json_ret and not pagination_next_uri and not ignore_pagination:
            if 'next_uri' not in json_ret['pagination']:
                raise RemoteError('Coinbase json response contained no "next_uri" key')

            next_uri = json_ret['pagination']['next_uri']
            if not next_uri:
                # As per the docs: https://developers.coinbase.com/api/v2?python#pagination
                # once we get an empty next_uri we are done
                return final_data

            additional_data = self._api_query(
                endpoint=endpoint,
                options=options,
                pagination_next_uri=next_uri,
            )
            final_data.extend(additional_data)

        return final_data

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            resp = self._api_query('accounts')
        except RemoteError as e:
            msg = (
                'Coinbase API request failed. Could not reach coinbase due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        returned_balances: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for account in resp:
            try:
                if not account['balance']:
                    continue

                amount = deserialize_asset_amount(account['balance']['amount'])

                # ignore empty balances. Coinbase returns zero balances for everything
                # a user does not own
                if amount == ZERO:
                    continue

                asset = asset_from_coinbase(account['balance']['currency'])

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

        return dict(returned_balances), ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
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

            # limit coinbase trades in the requested time range here since there
            # is no argument in the API call
            if trade and trade.timestamp >= start_ts and trade.timestamp <= end_ts:
                trades.append(trade)

        return trades

    def _deserialize_asset_movement(self, raw_data: Dict[str, Any]) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from coinbase and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data['status'] != 'completed':
                return None

            payout_date = raw_data.get('payout_at', None)
            if payout_date:
                timestamp = deserialize_timestamp_from_date(payout_date, 'iso8601', 'coinbase')
            else:
                timestamp = deserialize_timestamp_from_date(
                    raw_data['created_at'],
                    'iso8601',
                    'coinbase',
                )

            # Only get address/transaction id for "send" type of transactions
            address = None
            transaction_id = None
            # movement_category: Union[Literal['deposit'], Literal['withdrawal']]
            if 'type' in raw_data:
                # Then this should be a "send" which is the way Coinbase uses to send
                # crypto outside of the exchange
                # https://developers.coinbase.com/api/v2?python#transaction-resource
                msg = 'Non "send" type found in coinbase deposit/withdrawal processing'
                assert raw_data['type'] == 'send', msg
                movement_category = AssetMovementCategory.WITHDRAWAL
                # Can't see the fee being charged from the "send" resource

                amount = deserialize_asset_amount_force_positive(raw_data['amount']['amount'])
                asset = asset_from_coinbase(raw_data['amount']['currency'], time=timestamp)
                # Fees dont appear in the docs but from an experiment of sending ETH
                # to an address from coinbase there is the network fee in the response
                fee = Fee(ZERO)
                raw_network = raw_data.get('network', None)
                if raw_network:
                    raw_fee = raw_network.get('transaction_fee', None)

                if raw_fee:
                    # Since this is a withdrawal the fee should be the same as the moved asset
                    if asset != asset_from_coinbase(raw_fee['currency'], time=timestamp):
                        # If not we set ZERO fee and ignore
                        log.error(
                            f'In a coinbase withdrawal of {asset.identifier} the fee'
                            f'is denoted in {raw_fee["currency"]}',
                        )
                    else:
                        fee = deserialize_fee(raw_fee['amount'])

                if 'network' in raw_data:
                    transaction_id = get_key_if_has_val(raw_data['network'], 'hash')
                if 'to' in raw_data:
                    address = deserialize_asset_movement_address(raw_data['to'], 'address', asset)
            else:
                movement_category = deserialize_asset_movement_category(raw_data['resource'])
                amount = deserialize_asset_amount_force_positive(raw_data['amount']['amount'])
                fee = deserialize_fee(raw_data['fee']['amount'])
                asset = asset_from_coinbase(raw_data['amount']['currency'], time=timestamp)

            return AssetMovement(
                location=Location.COINBASE,
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
                f'Found coinbase deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of a coinbase '
                'asset movement. Check logs for details and open a bug report.',
            )
            log.error(
                f'Unexpected data encountered during deserialization of coinbase '
                f'asset_movement {raw_data}. Error was: {str(e)}',
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        account_data = self._api_query('accounts')
        account_ids = self._get_account_ids(account_data)
        raw_data = []
        for account_id in account_ids:
            raw_data.extend(self._api_query(f'accounts/{account_id}/deposits'))
            raw_data.extend(self._api_query(f'accounts/{account_id}/withdrawals'))
            # also get transactions to get the "sends", which in Coinbase is the
            # way to send Crypto out of the exchange
            txs = self._api_query(f'accounts/{account_id}/transactions')
            for tx in txs:
                if 'type' not in tx:
                    continue
                if tx['type'] == 'send':
                    raw_data.append(tx)

        log.debug('coinbase deposits/withdrawals history result', results_num=len(raw_data))

        movements = []
        for raw_movement in raw_data:
            movement = self._deserialize_asset_movement(raw_movement)
            # limit coinbase deposit/withdrawals in the requested time range
            #  here since there is no argument in the API call
            if movement and movement.timestamp >= start_ts and movement.timestamp <= end_ts:
                movements.append(movement)

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for coinbase
