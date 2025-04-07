import base64
import datetime
import hashlib
import hmac
import logging
import urllib.parse
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_htx
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import get_key_if_has_val
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_ms_from_intms,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Fee,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.data_structures import MarginPosition
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PAGINATION_LIMIT: Final = 500


def remove_fee_currency(symbol: str, fee_currency: str) -> str:
    """
    Removes the 'fee-currency' value from the 'symbol' if it appears at the beginning or
    the end of the 'symbol'.
    """
    if symbol.startswith(fee_currency):
        symbol = symbol[len(fee_currency):]
    elif symbol.endswith(fee_currency):
        symbol = symbol[:-len(fee_currency)]

    return symbol.strip()


class Htx(ExchangeInterface):
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            name=name,
            location=Location.HTX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the HTX API key is good for usage in rotki"""
        try:
            accounts = self.get_accounts()
        except RemoteError as e:
            return False, str(e)

        if len(accounts) != 0:
            return True, ''

        return False, 'API key cannot access account information'

    def _sign_request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Create signature for the provided payload.
        https://www.htx.com/en-us/opend/newApiPages/?id=419
        """
        new_params = params.copy()  # copy to avoid modifications in params if they are used later
        new_params['AccessKeyId'] = self.api_key
        new_params['SignatureVersion'] = '2'
        new_params['SignatureMethod'] = 'HmacSHA256'
        new_params['Timestamp'] = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S')

        host = urllib.parse.urlparse(url).hostname
        path = urllib.parse.urlparse(url).path
        param_str = '&'.join(  # params need to be sorted to be correctly validated
            [
                str(k) + '=' + urllib.parse.quote_plus(str(v))  # need to use the quoted string since cursors have `=` and it breaks signatures  # noqa: E501
                for k, v in sorted(new_params.items())
                if v is not None
            ],
        )
        # api describes that strings should be joined using '\n'
        payload = f'GET\n{host}\n{path}\n{param_str}'
        dig = hmac.new(
            key=self.secret,
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()
        new_params['Signature'] = base64.b64encode(dig).decode()
        return new_params

    def _query(self, absolute_path: str, options: dict[str, Any] | None = None) -> Any:
        url = f'https://api.huobi.pro{absolute_path}'
        signed_payload = self._sign_request(url=url, params=options or {})
        try:
            response = self.session.get(
                url=url,
                params=signed_payload,
                timeout=CachedSettings().get_timeout_tuple(),
            )
            res_body = response.json()
        except requests.RequestException as e:
            log.error(f'Failed to query HTX api. Exception: {e} {options}, URL: {url}')
            raise RemoteError(f'Failed to query HTX for {url}. Check log for more details') from e

        if res_body.get('status') != 'ok':
            log.error(f'Error response from HTX. URL: {url} {options}, Response: {response.text}')
            raise RemoteError(f'Failed to query HTX for {url}. Check log for more details')

        if (body := res_body.get('data')) is None:
            log.error(f'HTX endpoint missing data attribute. URL: {url} {options}, Response: {response.text}')  # noqa: E501
            raise RemoteError(f'Failed to query HTX for {url}. Check log for more details')

        return body

    def get_accounts(self) -> list[dict[str, Any]]:
        """Query the accounts to which the api key has access to"""
        return self._query(absolute_path='/v1/account/accounts')

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query balances for the accounts linked to the api key"""
        returned_balances: dict[AssetWithOracles, Balance] = {}
        for account in self.get_accounts():
            account_id = account['id']
            path = f'/v1/account/accounts/{account_id}/balance'
            try:
                data = self._query(path)
            except RemoteError as e:
                error_prefix = 'Failed to query HTX'
                log.error(f'{error_prefix} balances due to {e}')
                return returned_balances, f'{error_prefix} due to a remote error. Check logs for more details'  # noqa: E501

            if (account_balance_type := data['type']) is None:
                log.error(f'Response for balances does not contain the type key {data}. Skipping')
                continue

            if account_balance_type not in ('spot', 'otc', 'point'):
                log.debug(f'Ignored account balance type: {account_balance_type}')
                continue

            if (balances := data.get('list')) is None:
                log.error(f'Balances not found in {data} for account {account_id}. Skipping')
                continue

            for balance_info in balances:
                if (balance_type := balance_info.get('type')) not in ('trade', 'frozen'):
                    log.debug(f'Ignored balance type: {balance_type}')
                    continue

                if (amount_str := balance_info.get('balance')) is not None:
                    amount = deserialize_asset_amount(amount_str)
                else:
                    log.error(
                        f'Got HTX account with no balance value key in {balance_info}. Skipping',
                    )
                    continue

                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_htx(balance_info['currency'])
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='balance query',
                    )
                    continue

                except KeyError as e:
                    log.error(f'HTX balance does not contain the key {e}. Skipping')
                    continue

                try:
                    usd_price = Inquirer.find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing HTX balance entry due to inability to '
                        f'query USD price: {e!s}. Skipping balance entry',
                    )
                    continue

                returned_balances[asset] = Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )

        return returned_balances, ''

    def _paginated_query(
            self,
            endpoint: Literal['/v1/query/deposit-withdraw'],
            options: dict[str, Any],
            start_ts: Timestamp,
    ) -> list[dict[str, Any]]:
        """
        Query endpoints that can return paginated data. At the moment this is used for asset
        movements. For asset movements we use cursor pagination since for any time range
        the api will return a valid response and we don't know when to stop querying until
        we find a lower created-at than the start_ts(starting timestamp). The cursor pagination
        uses the id of the last object in the last query to return the results of the next page.

        May raise:
        - RemoteError: if the network request fails
        """
        result = []
        # copy since we are modifying the dict and could affect other queries using
        # the same options
        query_options = options.copy()
        while len(output := self._query(absolute_path=endpoint, options=options)) != 0:
            result.extend(output)
            try:
                query_options['from'] = output[-1]['id'] + 1  # from is inclusive, so we want after
                created_at = output[-1]['created-at']  # the results are in descending order
            except KeyError as e:
                log.error(f'Missing expected keys {e!s} while iterating for HTX deposits and withdrawals')  # noqa: E501
                break

            if len(output) < PAGINATION_LIMIT or created_at < start_ts:
                break

        return result

    def _query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            query_for: Literal['deposit', 'withdraw'],
    ) -> list[AssetMovement]:
        """
        Process deposits/withdrawals from HTX. If any asset is unknown or we fail to
        deserialize an entry the error is logged and we skip the entry.

        This logic processes all entries returned by the API, discarding those that do not fall
        within the range start_ts <= timestamp <= end_ts. Additionally, it does not terminate the
        querying process until it encounters an created_at value that is lower than the start_ts.
        """
        log.debug(f'querying HTX deposits/withdrawals with {start_ts=}-{end_ts=}')
        try:
            raw_data = self._paginated_query(
                endpoint='/v1/query/deposit-withdraw',
                options={
                    'type': query_for,
                    'size': PAGINATION_LIMIT,
                    'direct': 'next',  # sorted by descending order
                },
                start_ts=start_ts,
            )
        except RemoteError as e:
            log.error(f'Failed to query HTX api for deposits and withdrawals due to {e!s}')
            return []

        movements = []
        event_type: Final = HistoryEventType.DEPOSIT if query_for == 'deposit' else HistoryEventType.WITHDRAWAL  # noqa: E501
        for movement in raw_data:
            if (timestamp_raw := movement.get('created-at')) is not None:
                timestamp = ts_ms_to_sec(TimestampMS(int(timestamp_raw)))
                if not start_ts <= timestamp <= end_ts:
                    continue  # skip if is not in range, could come from last page
            else:
                log.error(f'Could not find timestamp for HTX movement {movement}. Skipping...')
                continue

            try:
                coin = asset_from_htx(movement['currency'])
                movements.extend(create_asset_movement_with_fee(
                    timestamp=ts_sec_to_ms(timestamp),
                    location=self.location,
                    location_label=self.name,
                    event_type=event_type,
                    asset=coin,
                    amount=deserialize_asset_amount(movement['amount']),
                    fee_asset=coin,
                    fee=deserialize_fee(movement.get('fee', '0')),
                    unique_id=str(movement['id']),
                    extra_data=maybe_set_transaction_extra_data(
                        address=get_key_if_has_val(movement, 'address'),
                        transaction_id=get_key_if_has_val(movement, 'tx-hash'),
                    ),
                ))
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key {msg}'

                log.error(f'{e} when reading movement for HTX deposit {movement}. Skipping...')
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='deposit/withdrawal',
                )
                continue

        return movements

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Query deposits and withdrawals sequentially

        This method sequentially queries for 'deposit' and 'withdrawal' types. Each type
        must be specified explicitly, as the underlying API call requires a 'type' parameter
        to distinguish between deposits and withdrawals. If the 'type' is not provided or is
        invalid, the API does not return any results and raises an error indicating that a
        required 'type' argument is missing.
        """
        events: list[AssetMovement | SwapEvent] = []
        for query_for in ('deposit', 'withdraw'):
            events.extend(self._query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                query_for=query_for,
            ))

        events.extend(self._query_trades(
            start_ts=start_ts,
            end_ts=end_ts,
        ))
        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list['MarginPosition']:
        return []  # noop for htx

    def _query_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """
        Query trades from HTX in the spot category.
        The API is limited to query trades up to 120 days into the past. We can query time ranges
        but we don't know when to stop querying into the past. What this function does is iterate
        over the 120 days period moving the queried frame in the maximum allowed time span, that is
        48 hours:
        [end ts, end ts - 48h] -> [end ts - 48h, end ts - 96h] -> ... [end ts - n*48h, start ts]

        Since we have a clear limit to stop querying what we do is use the start-time/end-time keys
        to filter the data that we need.

        https://huobiapi.github.io/docs/spot/v1/en/#search-match-results
        """
        events: list[SwapEvent] = []
        upper_ts, lower_ts = end_ts, Timestamp(end_ts - DAY_IN_SECONDS * 2)
        earliest_query_start_ts = Timestamp((ts_now() - DAY_IN_SECONDS * 120) + (15 * 60))  # margin of 15 minutes to not raise an error if the bound is reached while querying # noqa: E501

        if end_ts <= earliest_query_start_ts:  # 0... start_ts ... end_ts ... earliest_query_start
            return []  # entire query out of range. Bail

        if start_ts < earliest_query_start_ts:  # 0 ... start_ts ...  earliest_query_start ... end_ts  # noqa: E501
            start_ts = Timestamp(earliest_query_start_ts)

        while True:
            raw_data = self._query(
                absolute_path='/v1/order/matchresults',
                options={
                    'start-time': str(ts_sec_to_ms(lower_ts)),
                    'end-time': str(ts_sec_to_ms(upper_ts)),
                    'size': PAGINATION_LIMIT,
                },
            )
            for raw_trade in raw_data:
                try:
                    symbol, fee_currency = raw_trade['symbol'], raw_trade['fee-currency']
                    trade_type = raw_trade['type'].split('-')[0]
                    if trade_type not in {'buy', 'sell'}:
                        raise DeserializationError

                    # On the API page, it's mentioned transaction fee of buy order is based on
                    # base currency, transaction fee of sell order is based on quote currency
                    # https://huobiapi.github.io/docs/spot/v1/en/#search-match-results
                    base_asset, quote_asset = asset_from_htx(fee_currency), asset_from_htx(
                        remove_fee_currency(symbol=symbol, fee_currency=fee_currency),
                    )
                    fee_asset = base_asset
                    if trade_type == 'sell':
                        base_asset, quote_asset = quote_asset, base_asset
                        fee_asset = quote_asset
                except (UnknownAsset, DeserializationError) as e:
                    log.error(f'Could not read assets from HTX trade {raw_trade} due to {e!s}')
                    continue

                except UnprocessableTradePair as e:
                    log.error(f'Could not process base and quote assets from HTX trade {raw_trade} due to {e!s}')  # noqa: E501
                    continue

                except KeyError as e:
                    log.error(f'Key `{e!s}` missing from HTX trade {raw_trade}')
                    continue

                try:
                    spend_asset, spend_amount, receive_asset, receive_amount = get_swap_spend_receive(  # noqa: E501
                        raw_trade_type=trade_type,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        amount=deserialize_asset_amount(raw_trade['filled-amount']),
                        rate=deserialize_price(raw_trade['price']),
                    )
                    events.extend(create_swap_events(
                        timestamp=deserialize_timestamp_ms_from_intms(raw_trade['created-at']),
                        location=self.location,
                        spend_asset=spend_asset,
                        spend_amount=spend_amount,
                        receive_asset=receive_asset,
                        receive_amount=receive_amount,
                        fee_asset=fee_asset,
                        fee_amount=deserialize_fee(raw_trade['filled-fees']) if raw_trade['filled-fees'] else Fee(ZERO),  # noqa: E501
                        location_label=self.name,
                        unique_id=str(raw_trade['id']),
                    ))
                except DeserializationError as e:
                    log.error(f'{e} when reading rate for HTX trade {raw_trade}')
                except KeyError as e:
                    log.error(
                        f'Failed to deserialize HTX trade {raw_trade} due to missing key {e}. '
                        'Skipping...',
                    )

            upper_ts = Timestamp(upper_ts - DAY_IN_SECONDS * 2)
            lower_ts = Timestamp(lower_ts - DAY_IN_SECONDS * 2)
            if upper_ts <= start_ts:
                break

            lower_ts = max(lower_ts, start_ts)  # don't query more than we need in last iteration

        return events
