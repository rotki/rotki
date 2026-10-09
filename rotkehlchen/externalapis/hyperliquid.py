import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal, NotRequired, TypedDict

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.chain.evm.constants import ZERO_32_BYTES_HEX
from rotkehlchen.chain.hyperliquid.constants import CPT_HYPER
from rotkehlchen.concurrency import cancellable_sleep
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnknownCounterpartyMapping, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.counterparty_mappings import get_asset_id_by_counterparty
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_int_from_str,
    deserialize_timestamp_ms_from_intms,
)
from rotkehlchen.types import (
    AssetAmount,
    ChecksumEvmAddress,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_sec_to_ms
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def asset_from_hyperliquid(symbol: str) -> Asset:
    """Fetch asset from hyperliquid location

    May raise:
    - UnsupportedAsset
    - UnknownAsset
    - UnknownCounterpartyMapping
    """
    try:
        return symbol_to_asset_or_token(
            get_asset_id_by_counterparty(
                symbol=symbol,
                counterparty=CPT_HYPER,
            ),
        )
    except UnknownCounterpartyMapping:
        # Perp markets use canonical symbols (e.g. BTC/ETH/SOL) which may not have
        # explicit Hyperliquid counterparty mappings.
        return symbol_to_asset_or_token(symbol)


# Time range responses hold at most 500 entries per the docs. Observed caps are 500 for
# funding and 2000 for fills and ledger updates, so a page shorter than this was not cut off.
HYPERLIQUID_MIN_PAGE_CAP: Final = 500
# The REST weight limit is per minute, so keep retrying rate limited requests for that long.
HYPERLIQUID_RATE_LIMIT_WINDOW: Final = 60
USDC_SYMBOL: Final = 'USDC'
HistoryQueryType = Literal['userFunding', 'userNonFundingLedgerUpdates', 'userFillsByTime']


class FundingDelta(TypedDict):
    usdc: str


class FundingEntry(TypedDict, total=False):
    time: int | str
    hash: str
    oid: str
    delta: FundingDelta


class LedgerDelta(TypedDict, total=False):
    type: str
    usdc: str
    amount: str
    coin: str


class LedgerEntry(TypedDict, total=False):
    time: int | str
    hash: str
    oid: str
    delta: LedgerDelta


class FillEntry(TypedDict):
    coin: str
    px: str
    sz: str
    time: int | str
    hash: NotRequired[str]
    oid: NotRequired[str]
    fee: NotRequired[str]
    feeToken: NotRequired[str]
    side: NotRequired[str]
    dir: NotRequired[str]
    liquidation: NotRequired[bool]
    closedPnl: NotRequired[str]


@dataclass(frozen=True)
class EntryContext:
    """Normalized metadata shared by all events derived from one raw API entry."""

    entry: dict[str, Any]
    timestamp: TimestampMS
    unique_id: str
    group_identifier: str


@dataclass(frozen=True)
class ParsedFundingEntry:
    context: EntryContext
    amount: FVal


@dataclass(frozen=True)
class ParsedLedgerEntry:
    context: EntryContext
    entry_type: str | None
    amount: FVal
    asset: Asset


@dataclass(frozen=True)
class ParsedFillEntry:
    context: EntryContext
    raw_coin: str
    is_spot_fill: bool
    spend: AssetAmount
    receive: AssetAmount
    fee_amount: FVal
    fee_asset: Asset
    direction: str
    extra_data: dict[str, Any]


class HyperliquidAPI:
    """Client for Hyperliquid `info` endpoint balances and user history APIs."""

    def __init__(self) -> None:
        self.base_url = 'https://api.hyperliquid.xyz'
        self.session = create_session()
        self.arb_usdc = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
        self._spot_market_to_base_symbol: dict[int, str] | None = None
        self._discovered_dex_names: list[str] | None = None

    def _discover_available_dex_names(self) -> list[str]:
        """Discover available HIP-3 perp DEX names from Hyperliquid's `perpDexs`.

        References:
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
        - https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals
        """
        if self._discovered_dex_names is not None:
            return self._discovered_dex_names

        try:
            data = self._query_list(payload={'type': 'perpDexs'}, query_name='perpDexs')
        except RemoteError as e:
            log.debug(f'Failed to auto-discover Hyperliquid DEXs due to {e}')
            self._discovered_dex_names = []
            return self._discovered_dex_names

        discovered_names: set[str] = set()
        for entry in data:
            if isinstance((dex_name := entry.get('name')), str):
                discovered_names.add(dex_name)

        self._discovered_dex_names = sorted(discovered_names)
        if len(self._discovered_dex_names) == 0:
            log.info('Hyperliquid DEX discovery found only main DEX')
        else:
            log.info(
                f"Hyperliquid DEX discovery found main DEX and HIP-3 DEXs: "
                f"{', '.join(self._discovered_dex_names)}",
            )

        return self._discovered_dex_names

    def _post_info(self, payload: dict[str, Any], wait_for_rate_limit: bool = False) -> Any:
        """Query hyperliquid info endpoint.

        A rate limited request is retried with a growing backoff up to the configured query
        retry limit. With `wait_for_rate_limit` it keeps retrying for at least the length of
        the rate limit window, so that the queries of a long history can wait for the window
        to free up instead of failing the whole range. Paging a large account easily goes
        over the per minute weight limit, since history queries also cost per item returned.
        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits

        May raise:
            - RemoteError
        """
        cached_settings = CachedSettings()
        timeout = cached_settings.get_timeout_tuple()
        min_attempts = max(1, cached_settings.get_query_retry_limit())
        backoff = slept = attempts = 0
        while True:
            try:
                response = self.session.post(
                    url=f'{self.base_url}/info',
                    json=payload,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Failed to query hyperliquid info due to {e}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                attempts += 1
                if attempts >= min_attempts and (
                    not wait_for_rate_limit or slept >= HYPERLIQUID_RATE_LIMIT_WINDOW
                ):
                    raise RemoteError(
                        f'Hyperliquid API request {response.url} failed with HTTP status code '
                        f'{response.status_code} and text {response.text} after waiting '
                        f'{slept} seconds for the rate limit for payload {payload}',
                    )

                backoff = max(1, backoff * 2)
                try:
                    sleep_seconds = max(1, int(response.headers['retry-after']))
                except (KeyError, ValueError):
                    sleep_seconds = backoff

                log.debug(
                    f'Hyperliquid API request {response.url} got rate limited. Sleeping for '
                    f'{sleep_seconds} seconds after {slept} seconds already waited.',
                )
                cancellable_sleep(sleep_seconds)
                slept += sleep_seconds
                continue

            if response.status_code != HTTPStatus.OK:
                raise RemoteError(
                    f'Failed to query hyperliquid info with status code '
                    f'{response.status_code} and text {response.text}',
                )

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise RemoteError(
                    f'Failed to decode hyperliquid JSON response: {response.text[:200]}',
                ) from e

            return data

    def _query_dict(self, payload: dict[str, Any], query_name: str) -> dict[str, Any]:
        """Query `/info` and enforce a dictionary response.

        May raise:
            - RemoteError
        """
        if not isinstance((result := self._post_info(payload)), dict):
            raise RemoteError(
                f'Hyperliquid {query_name} returned malformed response type '
                f'{type(result).__name__}: {result!s}',
            )

        return result

    def _query_list(
            self,
            payload: dict[str, Any],
            query_name: str,
            wait_for_rate_limit: bool = False,
    ) -> list[dict[str, Any]]:
        """Query `/info` and enforce a list response of dictionaries.

        May raise:
            - RemoteError
        """
        if not isinstance(
            (result := self._post_info(payload, wait_for_rate_limit=wait_for_rate_limit)),
            list,
        ):
            raise RemoteError(
                f'Hyperliquid {query_name} returned malformed response type '
                f'{type(result).__name__}: {result!s}',
            )

        return [entry for entry in result if isinstance(entry, dict)]

    def _query(
            self,
            address: ChecksumEvmAddress,
            account_type: Literal['clearinghouseState', 'spotClearinghouseState'],
            dex_name: str | None = None,
    ) -> dict[str, Any]:
        """Query one Hyperliquid balance endpoint for a user and optional DEX context.

        May raise:
            - RemoteError
        """
        log.debug(f'Querying hyperliquid balances at {self.base_url}/info with {account_type=}, {address=} and {dex_name=}')  # noqa: E501
        payload: dict[str, Any] = {'type': account_type, 'user': address}
        if dex_name is not None:
            payload['dex'] = dex_name

        return self._query_dict(payload=payload, query_name=account_type)

    def query_balances(
            self,
            address: ChecksumEvmAddress,
            include_discovered_dexs: bool = True,
    ) -> dict[Asset, FVal]:
        """Query Hyperliquid Core balances for one user address.

        Aggregates balances from `spotClearinghouseState` and `clearinghouseState`.
        When enabled, discovered HIP-3 DEX contexts are queried as well.

        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/spot#retrieve-a-users-token-balances
        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals#retrieve-users-perpetuals-account-summary
        """
        balances: defaultdict[Asset, FVal] = defaultdict(FVal)
        self._query_balances_for_dex(
            address=address,
            dex_name=None,
            include_spot=True,
            balances=balances,
        )

        if include_discovered_dexs is True:
            # Hyperliquid spot balances are global for the user and may be repeated
            # when querying with a HIP-3 dex context. Query spot once (main context),
            # then aggregate only per-dex perp balances.
            for dex_name in self._discover_available_dex_names():
                self._query_balances_for_dex(
                    address=address,
                    dex_name=dex_name,
                    include_spot=False,
                    balances=balances,
                )

        return balances

    def _query_balances_for_dex(
            self,
            address: ChecksumEvmAddress,
            dex_name: str | None,
            include_spot: bool,
            balances: defaultdict[Asset, FVal],
    ) -> None:
        """Query spot and perp balances for one Hyperliquid DEX context."""
        dex_display = dex_name if dex_name is not None else 'main'
        spot_usdc_hold = ZERO
        if include_spot is True:
            spot_usdc_hold = self._query_spot_balances_for_dex(
                address=address,
                dex_name=dex_name,
                dex_display=dex_display,
                balances=balances,
            )

        try:
            perp_data = self._query(
                address=address,
                account_type='clearinghouseState',
                dex_name=dex_name,
            )
        except RemoteError as e:
            log.error(
                f'Skipping clearinghouseState hyperliquid balances '
                f'of {address=} and dex={dex_display} due to {e}',
            )
        else:
            try:
                perp_summary = perp_data.get('crossMarginSummary', {})
                perp_account_value = deserialize_fval(
                    value=perp_summary.get('accountValue', 0),
                    name='clearinghouseState total balances',
                    location='hyperliquid',
                )
                perp_margin_used = deserialize_fval(
                    value=perp_summary.get('totalMarginUsed', 0),
                    name='clearinghouseState total margin used',
                    location='hyperliquid',
                )
            except DeserializationError as e:
                log.error(
                    f'Failed to read hyperliquid crossMarginSummary '
                    f'for dex={dex_display} due to {e}',
                )
            else:
                if (duplicated_spot_margin := min(spot_usdc_hold, perp_margin_used)) > ZERO:
                    balances[self.arb_usdc] -= duplicated_spot_margin

                balances[self.arb_usdc] += perp_account_value

    def _query_spot_balances_for_dex(
            self,
            address: ChecksumEvmAddress,
            dex_name: str | None,
            dex_display: str,
            balances: defaultdict[Asset, FVal],
    ) -> FVal:
        """Query and aggregate spot balances for one Hyperliquid DEX context."""
        try:
            data = self._query(
                address=address,
                account_type='spotClearinghouseState',
                dex_name=dex_name,
            )
        except RemoteError as e:
            log.error(
                f'Skipping spotClearinghouseState balances in hyperliquid '
                f'for {address} and dex={dex_display} due to {e}',
            )
            return ZERO

        usdc_hold = ZERO
        for asset_entry in data.get('balances', []):
            try:
                if (
                    balance := deserialize_fval(
                        value=asset_entry['total'],
                        name='spotClearinghouseState total balances',
                        location='hyperliquid',
                    )
                ) == ZERO:
                    continue

                asset = asset_from_hyperliquid(asset_entry['coin'])
            except (
                DeserializationError,
                UnknownAsset,
                WrongAssetType,
                KeyError,
                UnknownCounterpartyMapping,
            ) as e:
                log.error(
                    f'Failed to read balance {asset_entry} from hyperliquid '
                    f'for dex={dex_display} due to {e}. Skipping',
                )
                continue

            balances[asset] += balance
            if asset == self.arb_usdc:
                try:
                    usdc_hold += deserialize_fval(
                        value=asset_entry.get('hold', 0),
                        name='spotClearinghouseState held USDC balance',
                        location='hyperliquid',
                    )
                except DeserializationError as e:
                    log.error(
                        'Failed to read held USDC balance %s from hyperliquid '
                        'for dex=%s due to %s. Skipping hold deduction',
                        asset_entry,
                        dex_display,
                        e,
                    )

        return usdc_hold

    @staticmethod
    def _entry_strict_unique_id(
            entry: dict[str, Any],
            address: ChecksumEvmAddress,
    ) -> str | None:
        """Return the identifier of an entry of the given user, or None if missing.

        Per Hyperliquid API docs:
        - Fills include a `tid` (trade id) that is unique per fill
        - Funding / non-funding-ledger entries always include a `hash`
        - `oid` (order id) is shared across partial fills of the same order,
          so it must NOT be used alone for per-fill uniqueness
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint

        Funding entries are not transactions and all have the zero hash. A
        user gets one funding payment per coin at a time, and every user gets
        them at the same times, so they are identified by the user, time and coin.

        Returns None only when the entry has none of these, which is not
        expected for the endpoints we consume.
        """
        if isinstance((tid := entry.get('tid')), int | str):
            return str(tid)
        if isinstance((entry_hash := entry.get('hash')), str) and entry_hash != ZERO_32_BYTES_HEX:
            return entry_hash
        if (
            isinstance((delta := entry.get('delta')), dict) and
            delta.get('type') == 'funding' and
            isinstance((coin := delta.get('coin')), str)
        ):
            return f'funding_{address}_{entry.get("time")}_{coin}'
        return None

    @staticmethod
    def _entry_content_id(entry: dict[str, Any]) -> str:
        """Stable identifier derived from the whole content of an entry"""
        return hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()

    @classmethod
    def _entry_unique_id(cls, entry: dict[str, Any], address: ChecksumEvmAddress) -> str:
        """Return a stable per-entry identifier for grouping.

        Uses `_entry_strict_unique_id` when the API provides one; otherwise
        falls back to the address, the entry `time` and a digest of the
        entry content so that consumers always get a non-empty string. The fallback is
        defensive and not expected in practice for the endpoints we consume. The address
        and the content are included so that distinct entries, of the same or of different
        tracked addresses, at the same time don't share a group identifier.
        """
        return cls._entry_strict_unique_id(entry=entry, address=address) or (
            f'{address}_{entry.get("time")}_{cls._entry_content_id(entry)}'
        )

    @staticmethod
    def _entry_group_identifier(unique_id: str) -> str:
        """Create the rotki group identifier used for events from one entry."""
        return create_group_identifier_from_unique_id(
            location=Location.HYPERLIQUID,
            unique_id=unique_id,
        )

    def _entry_context(
            self,
            entry: dict[str, Any],
            address: ChecksumEvmAddress,
            entry_time: int | None = None,
    ) -> EntryContext | None:
        """Build normalized context for a raw hyperliquid history entry."""
        if entry_time is None:
            try:
                entry_time = deserialize_timestamp_ms_from_intms(entry.get('time'))
            except DeserializationError:
                return None

        unique_id = self._entry_unique_id(entry=entry, address=address)
        return EntryContext(
            entry=entry,
            timestamp=TimestampMS(entry_time),
            unique_id=unique_id,
            group_identifier=self._entry_group_identifier(unique_id),
        )

    def _make_history_event(
            self,
            context: EntryContext,
            sequence_index: int,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: Asset,
            amount: FVal,
            location_label: ChecksumEvmAddress,
            notes: str,
            extra_data: dict[str, Any] | None = None,
    ) -> HistoryEvent:
        """Create a normalized history event for Hyperliquid Core activity."""
        return HistoryEvent(
            group_identifier=context.group_identifier,
            sequence_index=sequence_index,
            timestamp=context.timestamp,
            location=Location.HYPERLIQUID,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            extra_data=extra_data,
        )

    def _make_asset_movement(
            self,
            context: EntryContext,
            event_subtype: Literal[
            HistoryEventSubType.RECEIVE,
            HistoryEventSubType.SPEND,
        ],
            asset: Asset,
            amount: FVal,
            location_label: ChecksumEvmAddress,
    ) -> AssetMovement:
        """Create a deposit or withdrawal asset movement from ledger activity."""
        return AssetMovement(
            timestamp=context.timestamp,
            location=Location.HYPERLIQUID,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            unique_id=context.unique_id,
            location_label=location_label,
        )

    def _populate_spot_market_cache(self) -> None:
        """Populate the in-memory spot market id to base symbol cache from `spotMeta`.

        This stays as a lazy in-memory cache on purpose: the metadata is only needed
        when parsing spot fills, and keeping constructor setup free of API calls avoids
        network I/O when a caller only needs balances or DEX discovery.

        Nothing is cached on failure, since without it spot fills can't be resolved.

        May raise:
            - RemoteError
        """
        if self._spot_market_to_base_symbol is not None:
            return

        data = self._query_dict(payload={'type': 'spotMeta'}, query_name='spotMeta')
        token_index_to_symbol: dict[int, str] = {}
        for entry in data.get('tokens', []):
            try:
                token_index_to_symbol[int(entry['index'])] = str(entry['name'])
            except (KeyError, ValueError, TypeError) as e:
                log.error(f'Failed to read hyperliquid spot token entry {entry} due to {e}')
                continue

        market_to_base_symbol: dict[int, str] = {}
        for entry in data.get('universe', []):
            try:
                market_index = int(entry['index'])
                base_token = int(entry['tokens'][0])
            except (KeyError, ValueError, TypeError, IndexError) as e:
                log.error(f'Failed to read hyperliquid spot market entry {entry} due to {e}')
                continue

            if (base_symbol := token_index_to_symbol.get(base_token)) is not None:
                market_to_base_symbol[market_index] = base_symbol
                continue

            if isinstance((market_name := entry.get('name')), str):
                market_to_base_symbol[market_index] = market_name.split('/')[0]

        self._spot_market_to_base_symbol = market_to_base_symbol

    def _asset_from_hyperliquid_token(
            self,
            token: Any,
            prefer_spot_metadata: bool = False,
    ) -> Asset:
        """Resolve a Hyperliquid token name into a rotki asset.

        May raise if rotki does not know how to resolve this token yet. Callers should
        skip such entries instead of creating history events with unsavable assets.
        """
        token_name = str(token)
        if prefer_spot_metadata:
            try:
                return symbol_to_asset_or_token(get_asset_id_by_counterparty(
                    symbol=token_name,
                    counterparty=CPT_HYPER,
                ))
            except UnknownCounterpartyMapping:
                pass

        return asset_from_hyperliquid(token_name)

    def _get_spot_market_base_symbol(self, market: int) -> str | None:
        """Return a spot market base symbol, populating the metadata cache if needed.

        May raise:
            - RemoteError
        """
        self._populate_spot_market_cache()
        if self._spot_market_to_base_symbol is None:
            return None

        return self._spot_market_to_base_symbol.get(market)

    def _resolve_fill_coin(self, coin: str) -> str | None:
        """Resolve Hyperliquid fill market notation to the underlying asset symbol."""
        if coin.startswith('@'):
            try:
                market = deserialize_int_from_str(coin[1:], 'hyperliquid fill coin')
            except DeserializationError:
                return None
            return self._get_spot_market_base_symbol(market)

        return coin

    def _deserialize_amount(self, value: Any, name: str) -> FVal:
        """Deserialize a numeric value coming from Hyperliquid payloads."""
        return deserialize_fval(value=value, name=name, location='hyperliquid')

    def _query_history_page(
            self,
            query_type: HistoryQueryType,
            address: ChecksumEvmAddress,
            start_ms: int,
            end_ms: int,
    ) -> list[tuple[TimestampMS, dict[str, Any]]]:
        """Query one page of a user history endpoint and return its entries with their time.

        Both `startTime` and `endTime` are inclusive.

        May raise:
            - RemoteError: If the query fails, an entry is outside of the requested range, or
            an entry has an unreadable time. Skipping such an entry would shrink a capped page
            below the cap, so it would be taken for the last page and the rest of the range
            would never be queried.
        """
        page: list[tuple[TimestampMS, dict[str, Any]]] = []
        for entry in self._query_list(
            payload={'type': query_type, 'user': address, 'startTime': start_ms, 'endTime': end_ms},  # noqa: E501
            query_name=query_type,
            wait_for_rate_limit=True,
        ):
            try:
                entry_time = deserialize_timestamp_ms_from_intms(entry['time'])
            except (DeserializationError, KeyError) as e:
                raise RemoteError(
                    f'Hyperliquid {query_type} for {address} returned an entry with an '
                    f'unreadable time: {entry}',
                ) from e

            if not start_ms <= entry_time <= end_ms:
                raise RemoteError(
                    f'Hyperliquid {query_type} for {address} returned an entry at '
                    f'{entry_time} outside of the requested range {start_ms}-{end_ms}',
                )
            page.append((entry_time, entry))

        return page

    def _ensure_nothing_before_first_page(
            self,
            query_type: HistoryQueryType,
            address: ChecksumEvmAddress,
            range_start: int,
            oldest: int,
    ) -> None:
        """Check that a first page that may have been cut off holds the oldest entries.

        Paging forward relies on the API returning the oldest entries of a range. If it ever
        returned the newest ones instead, the history before the first page would be missed.

        May raise:
            - RemoteError: If there are entries in the range before the first page.
        """
        if len(self._query_history_page(
            query_type=query_type,
            address=address,
            start_ms=range_start,
            end_ms=oldest - 1,
        )) != 0:
            raise RemoteError(
                f'Hyperliquid {query_type} for {address} did not return the oldest entries '
                f'from {range_start}. Paging forward would miss history',
            )

    def _iter_entry_pages(
            self,
            query_type: HistoryQueryType,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Iterator[list[EntryContext]]:
        """Query a user history endpoint in pages and iterate the new entries of each page.

        The API caps each response and returns the oldest entries of the requested range,
        with no parameter to change the order. As the docs say, the next page starts at the
        newest timestamp of the previous one. That millisecond is queried again since the
        cap may have cut it in the middle, and the entries already seen are dropped. The
        order of the entries inside a page is not relied upon.

        A page shorter than the smallest cap was not cut off, so it is the last one and no
        further request is made. A full page that is all in one millisecond can't be paged
        further, since the API has no cursor within a millisecond. Then we move past it and
        warn that entries may be missing. Either way `startTime` grows with every page, so the
        loop ends.

        If the first page may have been cut off, check that nothing older than it exists in
        the range. That would mean the API returns the newest entries of a range, so paging
        forward would miss history.

        The range covers the whole `end_ts` second, since the next queried range starts at
        the second after it.

        A single request covers the first perp dex, all HIP-3 builder-deployed perp
        dexs, and spot: Hyperliquid's history endpoints do not accept a `dex` param
        and return mixed results (HIP-3 entries use `{dex}:{coin}` notation, spot
        uses `@{index}`). See:
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint#pagination
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint#retrieve-a-users-fills-by-time
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals#retrieve-a-users-funding-history-or-non-funding-ledger-updates

        May raise:
            - RemoteError
        """
        cursor: int = (range_start := ts_sec_to_ms(start_ts))
        end_ms = ts_sec_to_ms(Timestamp(end_ts + 1)) - 1
        # Keys of the entries already yielded. Only entries at the cursor millisecond can be
        # returned again, so the others are dropped after every page.
        seen: set[tuple[TimestampMS, str]] = set()
        while cursor <= end_ms:
            if len(page := self._query_history_page(
                query_type=query_type,
                address=address,
                start_ms=cursor,
                end_ms=end_ms,
            )) == 0:
                break

            oldest = min(entry_time for entry_time, _ in page)
            newest = max(entry_time for entry_time, _ in page)
            may_be_cut = len(page) >= HYPERLIQUID_MIN_PAGE_CAP
            if may_be_cut and cursor == range_start and oldest > range_start:
                self._ensure_nothing_before_first_page(
                    query_type=query_type,
                    address=address,
                    range_start=range_start,
                    oldest=oldest,
                )

            contexts: list[EntryContext] = []
            for entry_time, entry in page:
                # Prefer the stable per-entry identifier (tid for fills, hash otherwise) so
                # that partial fills of the same order at the same time, which share `oid`
                # but have distinct `tid`s, are not collapsed. Fall back to the whole entry
                # only when the API omits both (defensive, not expected in practice).
                key = (entry_time, self._entry_strict_unique_id(entry=entry, address=address) or self._entry_content_id(entry))  # noqa: E501
                if key in seen:
                    continue

                seen.add(key)
                if (context := self._entry_context(entry=entry, address=address, entry_time=entry_time)) is not None:  # noqa: E501
                    contexts.append(context)

            if len(contexts) != 0:
                yield contexts

            if not may_be_cut:
                break

            if newest > cursor:
                cursor = newest
            else:
                log.warning(
                    'Hyperliquid %s for %s returned a full page of entries at %sms. Some '
                    'entries at that millisecond may be missing from this sync.',
                    query_type, address, cursor,
                )
                cursor += 1

            seen = {key for key in seen if key[0] == cursor}

    def _parse_funding_entry(self, context: EntryContext) -> ParsedFundingEntry | None:
        """Parse a `userFunding` entry into a normalized funding payload."""
        try:
            delta = context.entry.get('delta', {})
            if not isinstance(delta, dict):
                return None

            amount = self._deserialize_amount(delta['usdc'], 'funding usdc')
        except (KeyError, DeserializationError) as e:
            log.error(f'Failed to parse hyperliquid funding entry {context.entry} due to {e}')
            return None

        if amount == ZERO:
            return None
        return ParsedFundingEntry(context=context, amount=amount)

    def _parse_ledger_entry(self, context: EntryContext) -> ParsedLedgerEntry | None:
        """Parse a `userNonFundingLedgerUpdates` entry into a normalized payload."""
        delta = context.entry.get('delta', {})
        if not isinstance(delta, dict):
            return None

        entry_type = delta.get('type')
        raw_amount = delta.get('usdc') or delta.get('amount')
        if raw_amount is None:
            return None

        try:
            if (amount := self._deserialize_amount(value=raw_amount, name=f'ledger {entry_type}')) == ZERO:  # noqa: E501
                return None
            if (token := delta.get('token')) is not None:
                asset = self._asset_from_hyperliquid_token(token=token, prefer_spot_metadata=True)
            else:
                asset = self._asset_from_hyperliquid_token(token=delta.get('coin') or USDC_SYMBOL)
        except UnknownAsset as e:
            log.warning(
                'Failed to parse hyperliquid ledger entry %s due to unknown asset %s. Skipping',
                context.entry,
                e.identifier,
            )
            return None
        except (
            DeserializationError,
            UnknownCounterpartyMapping,
            WrongAssetType,
        ) as e:
            log.error(f'Failed to parse hyperliquid ledger entry {context.entry} due to {e}. Skipping')  # noqa: E501
            return None

        return ParsedLedgerEntry(
            context=context,
            entry_type=entry_type,
            amount=amount,
            asset=asset,
        )

    def _parse_fill_entry(self, context: EntryContext) -> ParsedFillEntry | None:
        """Parse a `userFillsByTime` entry into swap or perp trade data."""
        try:
            if not isinstance((raw_coin := context.entry.get('coin')), str):
                return None

            dex_prefix: str | None = None
            if raw_coin.startswith('@'):
                coin = self._resolve_fill_coin(raw_coin)
            elif ':' in raw_coin:
                # HIP-3 builder-deployed perps encode the dex name in the coin
                # field as {dex}:{coin}. Extract both so we can resolve the
                # asset and surface the originating dex in extra_data.
                dex_prefix, coin = raw_coin.split(':', maxsplit=1)
            else:
                coin = raw_coin
            if coin is None:
                return None

            price = self._deserialize_amount(context.entry['px'], 'fill price')
            size = self._deserialize_amount(context.entry['sz'], 'fill size')
            if size == ZERO:
                return None

            # Per Hyperliquid API, `side` is always present on fills ("A" for
            # ask/sell, "B" for bid/buy). A missing/empty value indicates
            # malformed data we cannot interpret, so skip the entry rather than
            # silently defaulting to sell.
            # https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint#retrieve-a-users-fills-by-time
            if not isinstance((raw_side := context.entry.get('side')), str) or raw_side == '':
                log.error(
                    f'Skipping hyperliquid fill entry {context.entry} with missing side',
                )
                return None

            # `side` from Hyperliquid is always "A" (ask/sell) or "B" (bid/buy)
            # per the API spec (see Side literal in the official python SDK
            # https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/utils/types.py).
            # `.lower()` is a cheap defense against any future casing drift.
            is_buy = raw_side.lower() == 'b'
            base_asset = asset_from_hyperliquid(coin)
            quote_asset = self.arb_usdc
            notional = price * size
            if is_buy:
                spend = AssetAmount(quote_asset, notional)
                receive = AssetAmount(base_asset, size)
            else:
                spend = AssetAmount(base_asset, size)
                receive = AssetAmount(quote_asset, notional)
            fee_amount = self._deserialize_amount(context.entry.get('fee', '0'), 'fill fee')
            if (fee_token := context.entry.get('feeToken')) in (None, USDC_SYMBOL):
                fee_asset = self.arb_usdc
            else:
                fee_asset = asset_from_hyperliquid(str(fee_token))
            direction = str(context.entry.get('dir') or ('Buy' if is_buy else 'Sell'))
            extra_data: dict[str, Any] = {
                'market': raw_coin,
                'side': raw_side.upper(),
                'direction': direction,
            }
            if dex_prefix is not None:
                extra_data['dex'] = dex_prefix
            if 'liquidation' in context.entry:
                extra_data['liquidation'] = bool(context.entry['liquidation'])
            if (closed_pnl := context.entry.get('closedPnl')) is not None:
                extra_data['closed_pnl'] = str(closed_pnl)
        except (
            KeyError,
            DeserializationError,
            UnknownCounterpartyMapping,
            UnknownAsset,
            WrongAssetType,
        ) as e:
            log.error(f'Failed to parse hyperliquid fill entry {context.entry} due to {e}')
            return None

        return ParsedFillEntry(
            context=context,
            raw_coin=raw_coin,
            is_spot_fill=raw_coin.startswith('@'),
            spend=spend,
            receive=receive,
            fee_amount=fee_amount,
            fee_asset=fee_asset,
            direction=direction,
            extra_data=extra_data,
        )

    def _create_funding_events(
            self,
            address: ChecksumEvmAddress,
            contexts: list[EntryContext],
    ) -> list[HistoryBaseEntry]:
        """Convert a page of funding entries to rotki history events."""
        events: list[HistoryBaseEntry] = []
        for context in contexts:
            if (parsed := self._parse_funding_entry(context)) is None:
                continue

            event_type = HistoryEventType.RECEIVE if parsed.amount > ZERO else HistoryEventType.SPEND  # noqa: E501
            events.append(
                self._make_history_event(
                    context=parsed.context,
                    sequence_index=0,
                    event_type=event_type,
                    event_subtype=HistoryEventSubType.INTEREST if event_type == HistoryEventType.RECEIVE else HistoryEventSubType.NONE,  # noqa: E501
                    asset=self.arb_usdc,
                    amount=abs(parsed.amount),
                    location_label=address,
                    notes='Hyperliquid funding payment',
                ),
            )

        return events

    def _create_ledger_events(
            self,
            address: ChecksumEvmAddress,
            contexts: list[EntryContext],
    ) -> list[HistoryBaseEntry]:
        """Convert a page of ledger updates to rotki events."""
        events: list[HistoryBaseEntry] = []
        for context in contexts:
            if (parsed := self._parse_ledger_entry(context)) is None:
                continue

            if parsed.entry_type == 'deposit':
                events.append(
                    self._make_asset_movement(
                        context=parsed.context,
                        event_subtype=HistoryEventSubType.RECEIVE,
                        asset=parsed.asset,
                        amount=abs(parsed.amount),
                        location_label=address,
                    ),
                )
            elif parsed.entry_type == 'withdraw':
                events.append(
                    self._make_asset_movement(
                        context=parsed.context,
                        event_subtype=HistoryEventSubType.SPEND,
                        asset=parsed.asset,
                        amount=abs(parsed.amount),
                        location_label=address,
                    ),
                )
            elif parsed.entry_type in {
                'accountClassTransfer',
                'spotTransfer',
                'internalTransfer',
                'subAccountTransfer',
            }:
                delta = parsed.context.entry['delta']
                event_type = HistoryEventType.TRANSFER
                if isinstance(delta, dict) and parsed.entry_type == 'spotTransfer':
                    lower_address = address.lower()
                    if str(delta.get('destination', '')).lower() == lower_address:
                        event_type = HistoryEventType.RECEIVE
                    elif str(delta.get('user', '')).lower() == lower_address:
                        event_type = HistoryEventType.SPEND

                events.append(
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=0,
                        event_type=event_type,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=parsed.asset,
                        amount=abs(parsed.amount),
                        location_label=address,
                        notes='Hyperliquid internal transfer',
                    ),
                )
            elif parsed.entry_type == 'liquidation':
                events.append(
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=0,
                        event_type=HistoryEventType.LOSS,
                        event_subtype=HistoryEventSubType.LIQUIDATE,
                        asset=parsed.asset,
                        amount=abs(parsed.amount),
                        location_label=address,
                        notes='Hyperliquid liquidation',
                    ),
                )
            else:
                log.warning(
                    f'Unknown hyperliquid ledger event type {parsed.entry_type!r} '
                    f'in entry {parsed.context.entry}. '
                    f'Skipping. This may indicate a new event type that needs handling.',
                )

        return events

    def _create_fill_events(
            self,
            address: ChecksumEvmAddress,
            contexts: list[EntryContext],
    ) -> list[HistoryBaseEntry]:
        """Convert a page of fill entries to swap or trade events."""
        events: list[HistoryBaseEntry] = []
        for context in contexts:
            if (parsed := self._parse_fill_entry(context)) is None:
                continue

            if parsed.is_spot_fill:
                fee = None
                if parsed.fee_amount > ZERO:
                    fee = AssetAmount(parsed.fee_asset, parsed.fee_amount)
                events.extend(
                    create_swap_events(
                        timestamp=parsed.context.timestamp,
                        location=Location.HYPERLIQUID,
                        spend=parsed.spend,
                        receive=parsed.receive,
                        fee=fee,
                        group_identifier=parsed.context.group_identifier,
                        location_label=address,
                    ),
                )
                if parsed.fee_amount < ZERO:
                    # Hyperliquid fee can be negative for maker fills (rebate paid to trader).
                    # References:
                    # - https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees#maker-rebates
                    events.append(
                        self._make_history_event(
                            context=parsed.context,
                            sequence_index=2,
                            event_type=HistoryEventType.RECEIVE,
                            event_subtype=HistoryEventSubType.CASHBACK,
                            asset=parsed.fee_asset,
                            amount=abs(parsed.fee_amount),
                            location_label=address,
                            notes='Hyperliquid maker rebate',
                            extra_data=parsed.extra_data,
                        ),
                    )
                continue

            events.extend(
                [
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=0,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.SPEND,
                        asset=parsed.spend.asset,
                        amount=parsed.spend.amount,
                        location_label=address,
                        notes=f'Hyperliquid perp trade - {parsed.direction}',
                        extra_data=parsed.extra_data,
                    ),
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=1,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.RECEIVE,
                        asset=parsed.receive.asset,
                        amount=parsed.receive.amount,
                        location_label=address,
                        notes=f'Hyperliquid perp trade - {parsed.direction}',
                        extra_data=parsed.extra_data,
                    ),
                ],
            )

            if parsed.fee_amount > ZERO:
                events.append(
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=2,
                        event_type=HistoryEventType.TRADE,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=parsed.fee_asset,
                        amount=abs(parsed.fee_amount),
                        location_label=address,
                        notes='Hyperliquid trade fee',
                        extra_data=parsed.extra_data,
                    ),
                )
            elif parsed.fee_amount < ZERO:
                # Hyperliquid maker rebates are represented as negative fee amounts.
                # We map this as incoming cashback instead of outgoing fee.
                # References:
                # - https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees#maker-rebates
                events.append(
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=2,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.CASHBACK,
                        asset=parsed.fee_asset,
                        amount=abs(parsed.fee_amount),
                        location_label=address,
                        notes='Hyperliquid maker rebate',
                        extra_data=parsed.extra_data,
                    ),
                )

        return events

    def iter_history_event_batches(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Iterator[list[HistoryBaseEntry]]:
        """Query Hyperliquid Core history entries and yield the rotki events of each page.

        Includes ledger updates, funding payments, and fills. A single request
        per endpoint covers the first perp dex, all HIP-3 builder-deployed perp
        dexs, and spot — Hyperliquid's history endpoints (`userFillsByTime`,
        `userFunding`, `userNonFundingLedgerUpdates`) do not accept a `dex`
        parameter and return mixed results where HIP-3 entries use
        `{dex}:{coin}` notation and spot uses `@{index}`.

        References:
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint#retrieve-a-users-fills-by-time
        - https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals#retrieve-a-users-funding-history-or-non-funding-ledger-updates

        May raise:
            - RemoteError
        """
        query_type: HistoryQueryType
        for query_type, create_events in (
            ('userNonFundingLedgerUpdates', self._create_ledger_events),
            ('userFunding', self._create_funding_events),
            ('userFillsByTime', self._create_fill_events),
        ):
            for contexts in self._iter_entry_pages(
                query_type=query_type,
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
            ):
                yield create_events(address=address, contexts=contexts)
