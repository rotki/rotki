import hashlib
import hmac
import logging
import time
from base64 import b64decode, b64encode
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.typing import ApiKey, ApiSecret
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.serialization import rlk_jsonloads_dict, rlk_jsonloads_list

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CoinbaseProPermissionError(Exception):
    pass


class Coinbasepro(ExchangeInterface):

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super(Coinbasepro, self).__init__('coinbasepro', api_key, secret, database)
        self.base_uri = 'https://api.pro.coinbase.com'
        self.msg_aggregator = msg_aggregator

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Coinbase Pro API key is good for usage in Rotki

        Makes sure that the following permissions are given to the key:
        - View
        """
        try:
            self._api_query('accounts')
        except CoinbaseProPermissionError:
            msg = (
                f'Provided Coinbase Pro API key needs to have "View" permission activated. '
                f'Please log into your coinbase account and create a key with '
                f'the required permissions.'
            )
            return False, msg
        except RemoteError as e:
            error = str(e)
            if 'Invalid Passphrase' in error:
                msg = (
                    'The passphrase for the given API key does not match. Please '
                    'create a key with the preset passphrase "rotki"'
                )
                return False, msg

            return False, error

        return True, ''

    def _api_query(
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]] = None,
            pagination_next_uri: str = None,
            ignore_pagination: bool = False,
    ) -> List[Any]:
        """Performs a coinbase PRO API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.
        If this is an ongoing paginating call then provide pagination_next_uri.
        If you want just the first results then set ignore_pagination to True.
        """
        request_verb = "GET"
        if pagination_next_uri:
            request_url = pagination_next_uri
        else:
            request_url = f'/{endpoint}'
            if options:
                request_url += urlencode(options)

        timestamp = str(int(time.time()))
        message = timestamp + request_verb + request_url

        signature = hmac.new(
            b64decode(self.secret),
            message.encode(),
            hashlib.sha256,
        ).digest()
        log.debug('Coinbase Pro API query', request_url=request_url)

        self.session.headers.update({
            'CB-ACCESS-SIGN': b64encode(signature).decode('utf-8'),
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            # At the moment Rotki supports only API keys with a pre-set passphrase
            'CB-ACCESS-PASSPHRASE': 'rotki',
        })
        full_url = self.base_uri + request_url
        response = self.session.get(full_url)

        if response.status_code == 403:
            raise CoinbaseProPermissionError(f'API key does not have permission for {endpoint}')

        if response.status_code != 200:
            raise RemoteError(
                f'Coinbase Pro query {full_url} responded with error status code: '
                f'{response.status_code} and text: {response.text}',
            )

        if endpoint in ('accounts'):
            loading_function = rlk_jsonloads_list
        else:
            loading_function = rlk_jsonloads_dict

        try:
            json_ret = loading_function(response.text)
        except JSONDecodeError:
            raise RemoteError(f'Coinbase Pro returned invalid JSON response: {response.text}')

        # # If we got pagination and this is the first query, gather all the subsequent queries
        # if 'pagination' in json_ret and not pagination_next_uri and not ignore_pagination:
        #     while True:
        #         if 'next_uri' not in json_ret['pagination']:
        #             raise RemoteError(f'Coinbase json response contained no "next_uri" key')

        #         next_uri = json_ret['pagination']['next_uri']
        #         if not next_uri:
        #             # As per the docs: https://developers.coinbase.com/api/v2?python#pagination
        #             # once we get an empty next_uri we are done
        #             break

        #         additional_data = self._api_query(
        #             endpoint=endpoint,
        #             options=options,
        #             pagination_next_uri=next_uri,
        #         )
        #         final_data.extend(additional_data)

        return json_ret

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[Dict[Asset, Dict[str, Any]]], str]:
        try:
            accounts = self._api_query('accounts')
        except RemoteError as e:
            msg = (
                'Coinbase Pro API request failed. Could not reach coinbase pro due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        returned_balances: Dict[Asset, Dict[str, Any]] = dict()
        for account in accounts:
            try:
                amount = deserialize_asset_amount(account['balance'])
                # ignore empty balances. Coinbase returns zero balances for everything
                # a user does not own
                if amount == ZERO:
                    continue

                asset = asset_from_coinbase(account['currency'])
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
                    f'Found coinbase pro balance result with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase pro balance result with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a coinbase pro account balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a coinbase pro account balance',
                    account_balance=account,
                    error=msg,
                )
                continue

        return returned_balances, ''
