import datetime
import logging
import urllib.parse
from collections import defaultdict
from http import HTTPStatus
from itertools import chain
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.api.websockets.typedefs import UserMessageFeature, UserMessageRecord
from rotkehlchen.assets.converters import asset_from_bitvavo
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.exchange import (
    ExchangeInterface,
    ExchangeQueryBalances,
    HistoryEventQueue,
)
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events_multi_fee
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_fval_or_zero
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import BadData, NetworkFailure, Unsupported
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.data_structures import MarginPosition
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BITVAVO_BASE_URL: Final = 'https://api.bitvavo.com/v2'
BITVAVO_API_PATH_PREFIX: Final = '/v2'
BITVAVO_KEY_HEADER: Final = 'Bitvavo-Access-Key'
BITVAVO_TIMESTAMP_HEADER: Final = 'Bitvavo-Access-Timestamp'
BITVAVO_SIGNATURE_HEADER: Final = 'Bitvavo-Access-Signature'
HISTORY_MAX_ITEMS: Final = 100
# rotki query ranges are in whole seconds and a new range starts one second after the previous
# one ended, while Bitvavo stamps trades in milliseconds. A row landing in the last queried
# second after the query ran would fall between two ranges, so every query reaches back this
# far before its start. Rows seen twice are deduplicated through their identifiers.
HISTORY_OVERLAP_MS: Final = 2000
BitvavoEndpoint = Literal['/balance', '/account/history', '/stakingBalance']

# GET /account/history row types that credit a single amount, mapped to the rotki event type,
# subtype and note prefix.
REWARD_LEDGER_TYPES: Final[dict[str, tuple[HistoryEventType, HistoryEventSubType, str]]] = {
    'staking': (HistoryEventType.STAKING, HistoryEventSubType.REWARD, 'Staking reward'),
    'fixed_staking': (HistoryEventType.STAKING, HistoryEventSubType.REWARD, 'Fixed staking reward'),  # noqa: E501
    'affiliate': (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, 'Affiliate reward'),
    'rebate': (HistoryEventType.RECEIVE, HistoryEventSubType.CASHBACK, 'Fee rebate'),
    'distribution': (HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, 'Distribution'),
}
# Balance corrections booked by Bitvavo, in either direction. They map to ADJUSTMENT and not to
# EXCHANGE_ADJUSTMENT, which is reserved for the asset movement matcher and is neutral for
# balance tracking, so it would leave the tracked balance uncorrected.
ADJUSTMENT_LEDGER_TYPES: Final = frozenset({'manually_assigned', 'manually_assigned_bitvavo'})


def deserialize_bitvavo_timestamp(value: Any) -> TimestampMS:
    """Deserialize a Bitvavo ISO 8601 timestamp such as 2024-03-01T10:00:00.250Z.

    Trades carry milliseconds, the other ledger rows whole seconds. Both are accepted.

    May raise DeserializationError.
    """
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError) as e:
        raise DeserializationError(f'Failed to deserialize Bitvavo timestamp from {value}') from e

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return TimestampMS((parsed - datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)) // datetime.timedelta(milliseconds=1))  # noqa: E501


class Bitvavo(ExchangeInterface, SignatureGeneratorMixin):
    """Bitvavo exchange API docs: https://docs.bitvavo.com/docs/rest-api/introduction/

    Authenticated requests carry the API key, a millisecond timestamp and an HMAC-SHA256
    signature of ``timestamp + method + path + body`` in the request headers, where the
    path includes the ``/v2`` prefix and the query string, and the body is empty for GET.

    The "Read-only" key permission is enough. Bitvavo's dedicated order and trade endpoints
    additionally need "Trade digital assets", but the account history ledger used here
    returns trades to a Read-only key.

    History comes from GET /account/history, a single paginated ledger of trades, deposits,
    withdrawals, rewards and corrections, which makes the separate trade, deposit and
    withdrawal history endpoints unnecessary. Without an explicit date range it returns only
    the last 30 days, contrary to its documentation, so a range is always sent.
    """

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.BITVAVO,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = BITVAVO_BASE_URL
        self.session.headers.update({BITVAVO_KEY_HEADER: self.api_key})
        self.reported_unhandled_ledger_types: set[str] = set()

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if changed is True:
            self.session.headers.update({BITVAVO_KEY_HEADER: self.api_key})

        return changed

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _generate_signature(
            self,
            method: Literal['GET', 'POST'],
            request_path: str,
            timestamp: str,
            body: str = '',
    ) -> str:
        return self.generate_hmac_signature(message=f'{timestamp}{method}{request_path}{body}')

    def _api_query(
            self,
            endpoint: BitvavoEndpoint,
            options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Request a Bitvavo API endpoint and return the decoded JSON body.

        Bitvavo answers errors with a non-2xx status and a body of the form
        ``{"errorCode": 305, "error": "Your API key is not active."}``.

        May raise RemoteError.
        """
        options = options or {}
        request_path = f'{BITVAVO_API_PATH_PREFIX}{endpoint}'
        if len(query_string := urllib.parse.urlencode(options)) != 0:
            request_path = f'{request_path}?{query_string}'

        request_url = f'{self.base_uri}{endpoint}'
        log.debug('Bitvavo API request', request_url=request_url, options=options)
        try:
            response = self.session.get(
                url=request_url,
                params=options,
                headers={  # the api key is always present in the session headers
                    BITVAVO_TIMESTAMP_HEADER: (timestamp := str(ts_now_in_ms())),
                    BITVAVO_SIGNATURE_HEADER: self._generate_signature(
                        method='GET',
                        request_path=request_path,
                        timestamp=timestamp,
                    ),
                },
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Bitvavo request at {request_url} connection error: {e!s}.') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise RemoteError(
                f'Bitvavo request at {request_url} failed due to rate limiting. '
                f'Bitvavo blocks the key or IP for a minute after the weight limit is exceeded.',
            )

        try:
            response_data = response.json()
        except JSONDecodeError as e:
            raise RemoteError(
                f'Bitvavo request at {request_url} returned invalid JSON with '
                f'HTTP status {response.status_code}: {response.text}',
            ) from e

        if response.status_code != HTTPStatus.OK:
            if isinstance(response_data, dict) and 'errorCode' in response_data:
                raise RemoteError(
                    f'Bitvavo request at {request_url} failed with error code '
                    f'{response_data["errorCode"]}: {response_data.get("error")}',
                )
            raise RemoteError(
                f'Bitvavo request at {request_url} responded with HTTP status '
                f'{response.status_code}: {response.text}',
            )

        return response_data

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bitvavo API key can read account balances."""
        try:
            self._api_query(endpoint='/balance')
        except RemoteError as e:
            return False, str(e)
        return True, ''

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query the balances of the account, tradeable and locked.

        GET /balance splits each tradeable balance into what is free (``available``) and
        what is reserved by open orders (``inOrder``). GET /stakingBalance reports the
        ``amount`` locked in Fixed Staking, which /balance leaves out because it cannot be
        traded. All three belong to the user, so they are summed per asset.

        A failure of either query fails the whole balance query, so that a temporarily
        unreachable staking endpoint cannot make the locked assets silently disappear
        from the user's net worth.
        """
        try:
            balances = self._api_query(endpoint='/balance')
            staked = self._api_query(endpoint='/stakingBalance')
        except RemoteError as e:
            log.error('Failed to query Bitvavo balances due to %s', e)
            return None, f'Failed to query Bitvavo balances due to a remote error: {e!s}'

        if not isinstance(balances, list) or not isinstance(staked, list):
            msg = f'Bitvavo balance query returned unexpected data: {balances} {staked}'
            log.error(msg)
            return None, msg

        amounts: defaultdict[AssetWithOracles, FVal] = defaultdict(FVal)
        for balance, amount_keys in chain(
                ((entry, ('available', 'inOrder')) for entry in balances),
                ((entry, ('amount',)) for entry in staked),
        ):
            try:
                if (amount := sum(
                    (deserialize_fval(balance[key]) for key in amount_keys),
                    start=ZERO,
                )) == ZERO:
                    continue

                asset = asset_from_bitvavo(balance['symbol'])
            except (DeserializationError, KeyError) as e:
                log.error('Failed to deserialize Bitvavo balance %s. %s', balance, e)
                self.add_classified_error(
                    'Failed to deserialize a Bitvavo balance entry. '
                    'Check logs for details. Ignoring it.',
                    BadData(record=UserMessageRecord.BALANCE, error=str(e)),
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue

            amounts[asset] += amount

        return dict(self.balances_from_amounts(amounts)), ''

    @staticmethod
    def _ledger_fee(entry: dict[str, Any]) -> AssetAmount | None:
        """Return the fee of a ledger row, or None when the row has no fee.

        Fiat deposits carry a zero fee and some withdrawals omit the fee fields entirely.

        May raise DeserializationError, KeyError, UnknownAsset.
        """
        if (fee_amount := deserialize_fval_or_zero(entry.get('feesAmount'))) == ZERO:
            return None
        return AssetAmount(asset=asset_from_bitvavo(entry['feesCurrency']), amount=fee_amount)

    def _deserialize_trade(self, entry: dict[str, Any]) -> list[SwapEvent]:
        """Deserialize a buy or sell ledger row into swap events.

        The sent and received amounts are gross: the fee is charged on top of them in the
        quote currency, so it becomes a separate fee event.

        May raise DeserializationError, KeyError, UnknownAsset.
        """
        return create_swap_events_multi_fee(
            timestamp=deserialize_bitvavo_timestamp(entry['executedAt']),
            location=self.location,
            spend=AssetAmount(
                asset=asset_from_bitvavo(entry['sentCurrency']),
                amount=deserialize_fval(entry['sentAmount']),
            ),
            receive=AssetAmount(
                asset=asset_from_bitvavo(entry['receivedCurrency']),
                amount=deserialize_fval(entry['receivedAmount']),
            ),
            fees=[(fee, None, None)] if (fee := self._ledger_fee(entry)) is not None else None,
            location_label=self.name,
            group_identifier=create_group_identifier_from_unique_id(
                location=self.location,
                unique_id=entry['transactionId'],
            ),
        )

    def _deserialize_asset_movement(
            self,
            entry: dict[str, Any],
            is_deposit: bool,
    ) -> list[AssetMovement]:
        """Deserialize a deposit or withdrawal ledger row into asset movement events.

        Deposits carry the received side, withdrawals the sent side net of the fee. Crypto
        withdrawals carry the destination address, fiat movements a masked IBAN.

        May raise DeserializationError, KeyError, UnknownAsset.
        """
        side = 'received' if is_deposit else 'sent'
        return create_asset_movement_with_fee(
            timestamp=deserialize_bitvavo_timestamp(entry['executedAt']),
            location=self.location,
            location_label=self.name,
            event_subtype=(
                HistoryEventSubType.RECEIVE if is_deposit else HistoryEventSubType.SPEND
            ),
            asset=asset_from_bitvavo(entry[f'{side}Currency']),
            amount=deserialize_fval(entry[f'{side}Amount']),
            fee=self._ledger_fee(entry),
            unique_id=entry['transactionId'],
            extra_data=maybe_set_transaction_extra_data(
                address=entry.get('address'),
                transaction_id=None,
            ),
        )

    def _deserialize_single_event(
            self,
            entry: dict[str, Any],
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            notes_prefix: str,
            side: Literal['received', 'sent'],
    ) -> HistoryEvent:
        """Deserialize a ledger row that moves a single amount in one direction.

        May raise DeserializationError, KeyError, UnknownAsset.
        """
        amount = deserialize_fval(entry[f'{side}Amount'])
        symbol = entry[f'{side}Currency']
        return HistoryEvent(
            group_identifier=create_group_identifier_from_unique_id(
                location=self.location,
                unique_id=entry['transactionId'],
            ),
            sequence_index=0,
            timestamp=deserialize_bitvavo_timestamp(entry['executedAt']),
            location=self.location,
            location_label=self.name,
            asset=asset_from_bitvavo(symbol),
            amount=amount,
            event_type=event_type,
            event_subtype=event_subtype,
            notes=f'{notes_prefix} of {amount} {symbol} at Bitvavo',
        )

    def _deserialize_ledger_entry(self, entry: dict[str, Any]) -> Sequence[HistoryBaseEntry]:
        """Turn one GET /account/history row into rotki history events.

        Returns an empty sequence for row types that are not handled, and reports each
        such type to the user once. A type is never dropped silently, since one that
        changes the balance would then leave the tracked balance wrong without a trace.
        Repeated warnings fold into one notification that shows only the newest text,
        so the warning names every unhandled type seen so far.

        May raise DeserializationError, KeyError, UnknownAsset.
        """
        ledger_type = entry['type']
        if ledger_type in ('buy', 'sell'):
            return self._deserialize_trade(entry)
        if ledger_type in ('deposit', 'withdrawal'):
            return self._deserialize_asset_movement(entry, is_deposit=ledger_type == 'deposit')
        if (reward := REWARD_LEDGER_TYPES.get(ledger_type)) is not None:
            return [self._deserialize_single_event(entry, *reward, side='received')]
        if ledger_type in ADJUSTMENT_LEDGER_TYPES:
            is_receive = entry.get('receivedAmount') is not None
            return [self._deserialize_single_event(
                entry=entry,
                event_type=HistoryEventType.ADJUSTMENT,
                event_subtype=(
                    HistoryEventSubType.RECEIVE if is_receive else HistoryEventSubType.SPEND
                ),
                notes_prefix='Balance correction',
                side='received' if is_receive else 'sent',
            )]
        if ledger_type not in self.reported_unhandled_ledger_types:
            self.reported_unhandled_ledger_types.add(ledger_type)
            log.warning('Unhandled Bitvavo ledger type %s in entry %s', ledger_type, entry)
            self.add_classified_warning(
                f'Skipped Bitvavo history entries of type '
                f'{", ".join(sorted(self.reported_unhandled_ledger_types))}, which rotki '
                f'does not handle yet. Check logs for details and report it to rotki.',
                Unsupported(feature=UserMessageFeature.LEDGER_ENTRY_TYPE),
            )
        return []

    def _query_ledger(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue | None = None,
    ) -> list[HistoryBaseEntry]:
        """Walk the pages of GET /account/history for the given range.

        With an event queue each page is persisted as soon as it is deserialized and the
        returned list stays empty. Without one all events are returned.

        May raise RemoteError.
        """
        events: list[HistoryBaseEntry] = []
        options = {
            'fromDate': max(0, ts_sec_to_ms(start_ts) - HISTORY_OVERLAP_MS),
            'toDate': ts_sec_to_ms(end_ts),
            'maxItems': HISTORY_MAX_ITEMS,
        }
        page = 1
        while True:
            try:
                response = self._api_query(
                    endpoint='/account/history',
                    options=options | {'page': page},
                )
            except RemoteError as e:
                log.error('Bitvavo history query failed due to a remote error: %s', e)
                self.add_classified_error(
                    f'Got remote error while querying Bitvavo history: {e!s}',
                    NetworkFailure(record=UserMessageRecord.HISTORY_EVENT, error=str(e)),
                )
                raise

            if (
                    not isinstance(response, dict) or
                    not isinstance(items := response.get('items'), list)
            ):
                msg = f'Bitvavo history query returned unexpected data: {response}'
                log.error(msg)
                self.add_classified_error(
                    f'{msg}. Check logs for details.',
                    BadData(record=UserMessageRecord.HISTORY_EVENT, error=msg),
                )
                raise RemoteError(msg)

            page_events: list[HistoryBaseEntry] = []
            for entry in items:
                try:
                    page_events.extend(self._deserialize_ledger_entry(entry))
                except (DeserializationError, KeyError) as e:
                    msg = f'Missing key {e}' if isinstance(e, KeyError) else str(e)
                    log.error('Failed to deserialize Bitvavo history entry %s: %s', entry, msg)
                    self.add_classified_error(
                        f'Failed to deserialize a Bitvavo history entry: {msg}. '
                        f'Check logs for details. Ignoring it.',
                        BadData(record=UserMessageRecord.HISTORY_EVENT, error=msg),
                    )
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='history query',
                    )

            if event_queue is None:
                events.extend(page_events)
            else:
                event_queue.events.extend(page_events)
                event_queue.flush()

            if isinstance(total_pages := response.get('totalPages'), int):
                is_last_page = page >= total_pages
            else:  # without a usable page count only a page that is not full ends the walk
                is_last_page = len(items) < HISTORY_MAX_ITEMS

            if len(items) == 0 or is_last_page:
                break

            page += 1

        return events

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
            event_queue: HistoryEventQueue | None = None,
    ) -> tuple[Sequence[HistoryBaseEntry], Timestamp]:
        return self._query_ledger(
            start_ts=start_ts,
            end_ts=end_ts,
            event_queue=event_queue,
        ), end_ts

    def query_online_history_events_into_queue(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
    ) -> Timestamp:
        events, actual_end_ts = self.query_online_history_events(
            start_ts=start_ts,
            end_ts=end_ts,
            event_queue=event_queue,
        )
        event_queue.events.extend(events)
        return actual_end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> list[MarginPosition]:
        """Bitvavo margin trading is not exposed over its API yet."""
        return []
