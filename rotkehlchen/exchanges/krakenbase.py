# Good kraken and python resource:
# https://github.com/zertrin/clikraken/tree/master/src/clikraken
import base64
import json
import logging
import typing
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Literal

import gevent
from requests import Response

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import (
    KRAKEN_BASE_URL,
    ZERO,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import (
    ExchangeInterface,
    ExchangeQueryBalances,
    ExchangeWithExtras,
)
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KRAKEN_QUERY_TRIES = 8
KRAKEN_BACKOFF_DIVIDEND = 15
MAX_CALL_COUNTER_INCREASE = 2  # Trades and Ledger produce the max increase


def _check_and_get_response(response: Response, method: str) -> str | dict:
    """Checks the kraken response and if it's successful returns the result.

    If there is recoverable error a string is returned explaining the error
    May raise:
    - RemoteError if there is an unrecoverable/unexpected remote error
    """
    if response.status_code in {520, 525, 504}:
        log.debug(f'Kraken returned status code {response.status_code}')
        return 'Usual kraken 5xx shenanigans'
    if response.status_code != 200:
        raise RemoteError(
            f'Kraken API request {response.url} for {method} failed with HTTP status '
            f'code: {response.status_code}')

    log.debug(f'got response from Kraken with content: {response.content!r}')
    try:
        decoded_json = jsonloads_dict(response.text)
    except json.decoder.JSONDecodeError as e:
        raise RemoteError(f'Invalid JSON in Kraken response. {e}') from e

    error = decoded_json.get('error', None)
    if error:
        if isinstance(error, list) and len(error) != 0:
            error = error[0]

        if 'Rate limit exceeded' in error:
            log.debug(f'Kraken: Got rate limit exceeded error: {error}')
            return 'Rate limited exceeded'

        # else
        raise RemoteError(error)

    return decoded_json


class KrakenAccountType(SerializableEnumNameMixin):
    STARTER = 0
    INTERMEDIATE = 1
    PRO = 2


DEFAULT_KRAKEN_ACCOUNT_TYPE = KrakenAccountType.STARTER


class KrakenBase(ABC, ExchangeInterface, ExchangeWithExtras, SignatureGeneratorMixin):
    def __init__(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            kraken_account_type: KrakenAccountType | None = None,
            base_uri: str = KRAKEN_BASE_URL,
    ):
        super().__init__(
            name=name,
            location=location,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        # Kraken provides base64-encoded secrets, decode it for use with mixin methods
        self.secret = ApiSecret(base64.b64decode(self.secret))
        self.base_uri = base_uri
        self.session.headers.update({'API-Key': self.api_key})
        self.set_account_type(kraken_account_type)
        self.call_counter = 0
        self.last_query_ts = 0
        self.history_events_db = DBHistoryEvents(self.db)

    def set_account_type(self, account_type: KrakenAccountType | None) -> None:
        if account_type is None:
            account_type = DEFAULT_KRAKEN_ACCOUNT_TYPE

        self.account_type = account_type
        if self.account_type == KrakenAccountType.STARTER:
            self.call_limit = 15
            self.reduction_every_secs = 3
        elif self.account_type == KrakenAccountType.INTERMEDIATE:
            self.call_limit = 20
            self.reduction_every_secs = 2
        else:  # Pro
            self.call_limit = 20
            self.reduction_every_secs = 1

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'API-Key': self.api_key})
        if changed and credentials.api_secret is not None:
            # Decode the new base64 secret
            self.secret = ApiSecret(base64.b64decode(self.secret))

        return changed

    @abstractmethod
    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Kraken API Key is good for usage in Rotkehlchen

        Makes sure that the following permission are given to the key:
        - Ability to query funds
        - Ability to query open/closed trades
        - Ability to query ledgers
        """

    def _validate_single_api_key_action(
            self,
            base_url: str,
            method_str: Literal['Balance', 'TradesHistory', 'Ledgers', 'accounts'],
            req: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        try:
            self.api_query(method_str, req)
        except (RemoteError, ValueError) as e:
            error = str(e)
            if 'Incorrect padding' in error:
                return False, 'Provided API Key or secret is invalid'
            if 'EAPI:Invalid key' in error:
                return False, 'Provided API Key is invalid'
            if 'EGeneral:Permission denied' in error:
                msg = (
                    'Provided API Key does not have appropriate permissions. Make '
                    'sure that the "Query Funds", "Query Open/Closed Order and Trades"'
                    'and "Query Ledger Entries" actions are allowed for your Kraken API Key.'
                )
                return False, msg

            # else
            log.error(f'Kraken API key validation error: {e!s}')
            msg = (
                'Unknown error at Kraken API key validation. Perhaps API Key/Secret combination invalid?'  # noqa: E501
            )
            return False, msg
        return True, ''

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _manage_call_counter(self, method: str) -> None:
        self.last_query_ts = ts_now()
        if method in {'Ledgers', 'TradesHistory'}:
            self.call_counter += 2
        else:
            self.call_counter += 1

    @abstractmethod
    def query_private_api_method(self, method: str, req: dict | None = None) -> dict | str:
        """
        Method that implements the auth and query details of the corresponding API method
        """

    def api_query(self, method: str, req: dict | None = None) -> dict:
        tries = KRAKEN_QUERY_TRIES
        while tries > 0:
            if self.call_counter + MAX_CALL_COUNTER_INCREASE > self.call_limit:
                # If we are close to the limit, check how much our call counter reduced
                # https://www.kraken.com/features/api#api-call-rate-limit
                secs_since_last_call = ts_now() - self.last_query_ts
                self.call_counter = max(
                    0,
                    self.call_counter - int(secs_since_last_call / self.reduction_every_secs),
                    )
                # If still at limit, sleep for an amount big enough for smallest tier reduction
                if self.call_counter + MAX_CALL_COUNTER_INCREASE > self.call_limit:
                    backoff_in_seconds = self.reduction_every_secs * 2
                    log.debug(
                        f'Doing a Kraken API call would now exceed our call counter limit. '
                        f'Backing off for {backoff_in_seconds} seconds',
                        call_counter=self.call_counter,
                    )
                    tries -= 1
                    gevent.sleep(backoff_in_seconds)
                    continue

            log.debug(
                'Kraken API query',
                method=method,
                data=req,
                call_counter=self.call_counter,
            )

            result = self.query_private_api_method(method, req)
            if isinstance(result, str) and result != 'success':
                # Got a recoverable error
                backoff_in_seconds = int(KRAKEN_BACKOFF_DIVIDEND / tries)
                log.debug(
                    f'Got recoverable error {result} in a Kraken query of {method}. Will backoff '
                    f'for {backoff_in_seconds} seconds',
                )
                tries -= 1
                gevent.sleep(backoff_in_seconds)
                continue

            # else success
            return typing.cast('dict', result)

        raise RemoteError(
            f'After {KRAKEN_QUERY_TRIES} kraken queries for {method} could still not be completed',
        )

    @abstractmethod
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """
        An abstract method for querying balances.

        This method should be implemented by subclasses and is responsible
        for retrieving balance information.
        """

    def query_balances_base(self, method: str) -> tuple[dict | None, str]:
        try:
            kraken_balances = self.api_query(method, req={})
            log.info(f'got kraken {self.location} balances: {kraken_balances}')
        except RemoteError as e:
            if "Missing key: 'result'" in str(e):
                # handle https://github.com/rotki/rotki/issues/946
                kraken_balances = {}
            else:
                msg = (
                    'Kraken API request failed. Could not reach kraken due '
                    f'to {e}'
                )
                log.error(msg)
                return None, msg

        return kraken_balances, ''

    def deserialize_kraken_balance(self, kraken_balances: dict) -> tuple[dict, str]:
        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for kraken_name, amount_ in kraken_balances.items():
            log.debug(f'deserializing kraken balance for {kraken_name} with amount: {amount_}')
            try:
                amount = deserialize_fval(amount_)
                if amount == ZERO:
                    continue

                our_asset = asset_from_kraken(kraken_name)
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except DeserializationError as e:
                msg = str(e)
                self.msg_aggregator.add_error(
                    f'Error processing kraken balance for {kraken_name}. Check logs '
                    f'for details. Ignoring it.',
                )
                log.error(
                    'Error processing kraken balance',
                    kraken_name=kraken_name,
                    amount=amount_,
                    error=msg,
                )
                continue

            balance = Balance(amount=amount)
            if our_asset.identifier != 'KFEE':
                # There is no price value for KFEE
                try:
                    usd_price = Inquirer.find_usd_price(our_asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing kraken balance entry due to inability to '
                        f'query USD price: {e!s}. Skipping balance entry',
                    )
                    continue

                balance.usd_value = balance.amount * usd_price

            assets_balance[our_asset] += balance
            log.debug(
                'kraken balance query result',
                currency=our_asset,
                amount=balance.amount,
                usd_value=balance.usd_value,
            )

        return dict(assets_balance), ''

    def query_until_finished(
            self,
            endpoint: Literal['Ledgers'],
            keyname: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            extra_dict: dict | None = None,
    ) -> tuple[list, bool]:
        """ Abstracting away the functionality of querying a kraken endpoint where
        you need to check the 'count' of the returned results and provide sufficient
        calls with enough offset to gather all the data of your query.
        """
        result: list = []

        with_errors = False
        log.debug(
            f'Querying Kraken {endpoint} from {start_ts} to '
            f'{end_ts} with extra_dict {extra_dict}',
        )
        response = self._query_endpoint_for_period(
            endpoint=endpoint,
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict=extra_dict,
        )
        count = response['count']
        offset = len(response[keyname])
        result.extend(response[keyname].values())

        log.debug(f'Kraken {endpoint} Query Response with count:{count}')

        while offset < count:
            log.debug(
                f'Querying Kraken {endpoint} from {start_ts} to {end_ts} '
                f'with offset {offset} and extra_dict {extra_dict}',
            )
            try:
                response = self._query_endpoint_for_period(
                    endpoint=endpoint,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    offset=offset,
                    extra_dict=extra_dict,
                )
            except RemoteError as e:
                with_errors = True
                log.error(
                    f'One of krakens queries when querying endpoint for period failed '
                    f'with {e!s}. Returning only results we have.',
                )
                break

            if count != response['count']:
                log.error(
                    f'Kraken unexpected response while querying endpoint for period. '
                    f'Original count was {count} and response returned {response["count"]}',
                )
                with_errors = True
                break

            response_length = len(response[keyname])
            offset += response_length
            if response_length == 0 and offset != count:
                # If we have provided specific filtering then this is a known
                # issue documented below, so skip the warning logging
                # https://github.com/rotki/rotki/issues/116
                if extra_dict:
                    break
                # it is possible that kraken misbehaves and either does not
                # send us enough results or thinks it has more than it really does
                log.warning(
                    f'Missing {count - offset} results when querying kraken '
                    f'endpoint {endpoint}',
                )
                with_errors = True
                break

            result.extend(response[keyname].values())

        return result, with_errors

    def _query_endpoint_for_period(
            self,
            endpoint: Literal['Ledgers'],
            start_ts: Timestamp,
            end_ts: Timestamp,
            offset: int | None = None,
            extra_dict: dict | None = None,
    ) -> dict:
        request: dict[str, Timestamp | int] = {}
        request['start'] = start_ts
        request['end'] = end_ts
        if offset is not None:
            request['ofs'] = offset
        if extra_dict is not None:
            request.update(extra_dict)
        return self.api_query(endpoint, request)

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for kraken
