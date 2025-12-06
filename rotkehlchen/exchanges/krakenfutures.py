"""
Module specific to Kraken's futures platform
"""
import hashlib
import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants import (
    KRAKEN_FUTURES_API_VERSION,
)
from rotkehlchen.constants.misc import KRAKEN_FUTURES_BASE_URL, ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.exchange import ExchangeQueryBalances
from rotkehlchen.exchanges.krakenbase import KrakenAccountType, KrakenBase, _check_and_get_response
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Location,
)
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Krakenfutures(KrakenBase):
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            kraken_account_type: KrakenAccountType | None = None,
            base_uri: str = KRAKEN_FUTURES_BASE_URL,
    ):
        super().__init__(
            name=name,
            location=Location.KRAKENFUTURES,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
            base_uri=base_uri,
            kraken_account_type=kraken_account_type,
        )

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Kraken API Key is good for usage in Rotkehlchen

        Makes sure that the following permission are given to the key:
        - Ability to query funds
        - Ability to query open/closed trades
        - Ability to query ledgers
        """
        valid, msg = self._validate_single_api_key_action(self.base_uri, 'accounts')
        if not valid:
            return False, msg

        return True, ''

    def edit_exchange_extras(self, extras: dict) -> tuple[bool, str]:
        return True, ''  # do nothing

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        raw_balances, msg = self.query_balances_base('accounts')
        log.debug(f'got Kraken Futures raw balances = {raw_balances}')
        if raw_balances is None:
            return raw_balances, msg

        accounts: dict = self._get_inner_dict(raw_balances, 'accounts')
        cash: dict = self._get_inner_dict(accounts, 'cash')
        cash_balances: dict = self._get_inner_dict(cash, 'balances')
        flex: dict = self._get_inner_dict(accounts, 'flex')
        flex_currencies: dict = self._get_inner_dict(flex, 'currencies')
        log.debug(f'Kraken Futures cash balances = {cash_balances}')
        log.debug(f'Kraken Futures flex currencies = {flex_currencies}')

        self._add_single_collateral_futures_margin_to_cash_balances(accounts, cash_balances)

        upper_kraken_names = defaultdict(Any, {k.upper(): v for k, v in cash_balances.items()})
        cash_and_single_deserialized, msg = self.deserialize_kraken_balance(upper_kraken_names)
        if msg:
            return None, msg

        flex_balances = self._parse_multi_collateral_futures_margin(flex_currencies)
        flex_deserialized, msg = self.deserialize_kraken_balance(flex_balances)
        if msg:
            return None, msg

        log.debug(f'deserialized Kraken Futures flex margin = {flex_deserialized}')
        total_futures_balances = {
            currency:
                Balance(
                    cash_and_single_deserialized.get(currency, Balance(ZERO, ZERO)).amount
                        + flex_deserialized.get(currency, Balance(ZERO, ZERO)).amount,
                    cash_and_single_deserialized.get(currency, Balance(ZERO, ZERO)).usd_value
                        + flex_deserialized.get(currency, Balance(ZERO, ZERO)).usd_value,
                )
            for currency in cash_and_single_deserialized.keys() | flex_deserialized.keys()
        }

        log.debug(f'total Kraken Futures balances = {flex_deserialized}')
        return total_futures_balances, ''

    def query_private_api_method(self, method: str, req: dict | None = None) -> dict | str:
        """API queries that require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})

        """
        if req is None:
            req = {}

        urlpath: str = '/derivatives/api/' + KRAKEN_FUTURES_API_VERSION + '/' + method if method is not None else ''  # noqa: E501
        urlpath_without_prefix = urlpath.removeprefix('/derivatives')
        req['nonce'] = str(int(1000 * time.time()))
        post_data = ''

        # any unicode strings must be turned to bytes
        hashable = (post_data + req['nonce'] + urlpath_without_prefix).encode()
        message = hashlib.sha256(hashable).digest()
        signature = self.generate_hmac_b64_signature(
            message=message,
            digest_algorithm=hashlib.sha512,
        )
        self.session.headers.update({
            'APIKey': self.api_key,
            'Nonce': req['nonce'],
            'Authent': signature,
        })
        try:
            full_url = self.base_uri + urlpath
            log.debug(f'Querying Kraken for {method} with {req} at URL: {full_url}')
            response = self.session.get(
                full_url,
                timeout=CachedSettings().get_timeout_tuple(),
            )
            log.debug(f'raw response from kraken for API method {method} = {response}')
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {e!s}') from e
        self._manage_call_counter(method)

        return _check_and_get_response(response, method)

    @staticmethod
    def _get_inner_dict(dictionary: dict, inner_dict_keyname: str) -> dict:
        result: dict | None = dictionary.get(inner_dict_keyname)
        if result is None:
            raise RemoteError('Missing result in kraken futures response for accounts')

        return result

    def _parse_multi_collateral_futures_margin(
            self, flex_currencies: dict,
    ) -> defaultdict[Any, float]:
        newdict: defaultdict = defaultdict(float)
        for currency, flex_collateral in flex_currencies.items():
            try:
                newdict[currency] += flex_collateral.get('quantity', 0)
            except KeyError as e:
                log.error(
                    f'kraken multi collateral asset name {currency} does not match rotki name')
                self.send_unknown_asset_message(
                    asset_identifier=str(e),
                    details='balance query',
                )
                continue

        return newdict

    @staticmethod
    def _add_single_collateral_futures_margin_to_cash_balances(accounts: dict[str, dict], cash_balances: dict) -> None:  # noqa: E501
        for account, collateral_dict in accounts.items():
            if account.startswith('fi_'):
                currency = collateral_dict.get('currency')
                cash_balances[currency] += collateral_dict['balances'].get(currency)
