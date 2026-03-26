import json
import logging
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final, Literal, NotRequired, TypedDict, cast

import gevent
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.constants import CPT_HYPER
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
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    AssetAmount,
    ChecksumEvmAddress,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.network import create_session

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


HYPERLIQUID_MAX_HISTORY_PAGES: Final = 500


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
    def __init__(self) -> None:
        self.base_url = 'https://api.hyperliquid.xyz'
        self.session = create_session()
        self.arb_usdc = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
        self._spot_market_to_base_symbol: dict[int, str] | None = None

    def _post_info(self, payload: dict[str, Any]) -> Any:
        """Query hyperliquid info endpoint.

        May raise:
            - RemoteError
        """
        cached_settings = CachedSettings()
        retries_left = max(1, cached_settings.get_query_retry_limit())
        retries_num = retries_left
        timeout = cached_settings.get_timeout_tuple()
        backoff = 1
        while retries_left > 0:
            retries_left -= 1
            try:
                response = self.session.post(
                    url=f'{self.base_url}/info',
                    json=payload,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Failed to query hyperliquid info due to {e}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if retries_left == 0:
                    raise RemoteError(
                        f'Hyperliquid API request {response.url} failed with HTTP status code '
                        f'{response.status_code} and text {response.text} after '
                        f'{retries_num} retries '
                        f'for payload {payload}',
                    )

                retry_after_header = response.headers.get('retry-after')
                if retry_after_header is not None:
                    try:
                        sleep_seconds = max(1, int(retry_after_header))
                    except ValueError:
                        sleep_seconds = backoff
                else:
                    sleep_seconds = backoff

                log.debug(
                    f'Hyperliquid API request {response.url} got rate limited. Sleeping for '
                    f'{sleep_seconds} seconds. We have {retries_left} tries left.',
                )
                gevent.sleep(sleep_seconds)
                backoff *= 2
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

        raise AssertionError('unreachable')

    def _query(
            self,
            address: ChecksumEvmAddress,
            account_type: Literal['clearinghouseState', 'spotClearinghouseState'],
    ) -> dict[str, Any]:
        """Query hyperliquid for balances.

        May raise:
            - RemoteError
        """
        log.debug(f'Querying hyperliquid balances at {self.base_url}/info with {account_type=} and {address=}')  # noqa: E501
        if not isinstance(
            (result := self._post_info({'type': account_type, 'user': address})),
            dict,
        ):
            raise RemoteError(
                f'Hyperliquid {account_type} returned malformed response type '
                f'{type(result).__name__}: {result!s}',
            )

        return result

    def query_balances(self, address: ChecksumEvmAddress) -> dict[Asset, FVal]:
        """
        Queries both spot and perp balances since they are returned in two different endpoints.
        Hyperliquid has two `accounts` for each address, one for spot and one for perpetuals.

        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/spot#retrieve-a-users-token-balances
        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals#retrieve-users-perpetuals-account-summary
        """
        balances: defaultdict[Asset, FVal] = defaultdict(FVal)
        try:
            data = self._query(address=address, account_type='spotClearinghouseState')
        except RemoteError as e:
            log.error(f'Skipping spotClearinghouseState balances in hyperliquid of {address} due to {e}')  # noqa: E501
            data = {}

        for asset_entry in data.get('balances', []):
            try:
                if (balance := deserialize_fval(
                    value=asset_entry['total'],
                    name='spotClearinghouseState total balances',
                    location='hyperliquid',
                )) == ZERO:
                    continue

                asset = asset_from_hyperliquid(asset_entry['coin'])
            except (
                DeserializationError,
                UnknownAsset,
                WrongAssetType,
                KeyError,
                UnknownCounterpartyMapping,
            ) as e:
                log.error(f'Failed to read balance {asset_entry} from hyperliquid due to {e}. Skipping')  # noqa: E501
                continue

            if balance != ZERO:
                balances[asset] += balance

        try:
            perp_data = self._query(address=address, account_type='clearinghouseState')
        except RemoteError as e:
            log.error(f'Skipping clearinghouseState hyperliquid balances of {address=} due to {e}')
        else:
            try:
                balances[self.arb_usdc] += deserialize_fval(
                    value=perp_data.get('crossMarginSummary', {}).get('accountValue', 0),
                    name='clearinghouseState total balances',
                    location='hyperliquid',
                )
            except DeserializationError as e:
                log.error(f'Failed to read hyperliquid crossMarginSummary due to {e}')

        return balances

    @staticmethod
    def _entry_unique_id(entry: dict[str, Any]) -> str:
        return str(entry.get('hash') or entry.get('oid') or entry.get('time'))

    @staticmethod
    def _entry_group_identifier(unique_id: str) -> str:
        return create_group_identifier_from_unique_id(
            location=Location.HYPERLIQUID,
            unique_id=unique_id,
        )

    def _entry_context(
            self,
            entry: dict[str, Any],
            entry_time: int | None = None,
    ) -> EntryContext | None:
        if entry_time is None:
            try:
                entry_time = int(entry['time'])
            except (KeyError, TypeError, ValueError):
                return None

        unique_id = self._entry_unique_id(entry)
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
        return AssetMovement(
            timestamp=context.timestamp,
            location=Location.HYPERLIQUID,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            unique_id=context.unique_id,
            location_label=location_label,
        )

    def _get_spot_market_base_symbol(self, market: int) -> str | None:
        if self._spot_market_to_base_symbol is None:
            try:
                data = self._post_info({'type': 'spotMeta'})
            except RemoteError as e:
                log.error(f'Failed to query hyperliquid spot metadata due to {e}')
                return None

            if not isinstance(data, dict):
                log.error(
                    f'Hyperliquid spotMeta returned malformed response type {type(data).__name__}',
                )
                return None

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

        return self._spot_market_to_base_symbol.get(market)

    def _resolve_fill_coin(self, coin: str) -> str | None:
        if coin.startswith('@'):
            try:
                market = int(coin[1:])
            except ValueError:
                return None
            return self._get_spot_market_base_symbol(market)

        return coin

    def _deserialize_amount(self, value: str, name: str) -> FVal:
        return deserialize_fval(value=value, name=name, location='hyperliquid')

    def _iter_entries_by_time(
            self,
            query_type: Literal['userFunding', 'userNonFundingLedgerUpdates', 'userFillsByTime'],
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Iterator[EntryContext]:
        """Query time-ranged entries and walk backwards to avoid API caps."""
        start_ms = int(start_ts * 1000)
        end_ms = int(end_ts * 1000)
        cursor_end = end_ms
        page = 0
        seen: set[str] = set()

        while cursor_end >= start_ms and page < HYPERLIQUID_MAX_HISTORY_PAGES:
            page += 1
            data = self._post_info(
                {
                    'type': query_type,
                    'user': address,
                    'startTime': start_ms,
                    'endTime': cursor_end,
                },
            )
            if not isinstance(data, list):
                raise RemoteError(
                    f'Hyperliquid {query_type} returned malformed response type '
                    f'{type(data).__name__}: {data!s}',
                )

            page_entries = cast('list[dict[str, Any]]', data)
            if len(page_entries) == 0:
                break

            oldest_time = cursor_end
            for entry in page_entries:
                try:
                    entry_time = int(entry['time'])
                except (KeyError, TypeError, ValueError):
                    continue

                oldest_time = min(oldest_time, entry_time)
                if entry_time < start_ms or entry_time > end_ms:
                    continue

                if (unique_id := entry.get('hash') or entry.get('oid')) is not None:
                    dedup_key = f'{entry_time}:{unique_id}'
                else:
                    dedup_key = f'{entry_time}:{json.dumps(entry, sort_keys=True, default=str)}'

                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                if (context := self._entry_context(entry, entry_time=entry_time)) is None:
                    continue
                yield context

            if oldest_time >= cursor_end:
                break
            cursor_end = oldest_time - 1

    def _parse_funding_entry(self, context: EntryContext) -> ParsedFundingEntry | None:
        try:
            delta = cast('FundingEntry', context.entry).get('delta', {})
            amount = self._deserialize_amount(delta['usdc'], 'funding usdc')
        except (KeyError, DeserializationError) as e:
            log.error(f'Failed to parse hyperliquid funding entry {context.entry} due to {e}')
            return None

        if amount == ZERO:
            return None
        return ParsedFundingEntry(context=context, amount=amount)

    def _parse_ledger_entry(self, context: EntryContext) -> ParsedLedgerEntry | None:
        entry = cast('LedgerEntry', context.entry)
        delta = entry.get('delta', {})
        entry_type = delta.get('type')
        raw_amount = delta.get('usdc') or delta.get('amount')
        if raw_amount is None:
            return None

        try:
            amount = self._deserialize_amount(raw_amount, f'ledger {entry_type}')
            if amount == ZERO:
                return None
            asset = asset_from_hyperliquid(delta.get('coin') or 'USDC')
        except (
            DeserializationError,
            UnknownCounterpartyMapping,
            UnknownAsset,
            WrongAssetType,
        ) as e:
            log.error(f'Failed to parse hyperliquid ledger entry {context.entry} due to {e}')
            return None

        return ParsedLedgerEntry(
            context=context,
            entry_type=entry_type,
            amount=amount,
            asset=asset,
        )

    def _parse_fill_entry(self, context: EntryContext) -> ParsedFillEntry | None:
        try:
            entry = cast('FillEntry', context.entry)
            raw_coin = str(entry['coin'])
            coin = self._resolve_fill_coin(raw_coin)
            if coin is None:
                return None

            price = self._deserialize_amount(entry['px'], 'fill price')
            size = self._deserialize_amount(entry['sz'], 'fill size')
            if size == ZERO:
                return None

            is_buy = str(entry.get('side', '')).lower() in {'b', 'buy'}
            base_asset = asset_from_hyperliquid(coin)
            quote_asset = asset_from_hyperliquid('USDC')
            notional = price * size
            spend = AssetAmount(quote_asset, notional) if is_buy else AssetAmount(base_asset, size)
            receive = (
                AssetAmount(base_asset, size) if is_buy else AssetAmount(quote_asset, notional)
            )
            fee_amount = self._deserialize_amount(entry.get('fee', '0'), 'fill fee')
            fee_asset = asset_from_hyperliquid(str(entry.get('feeToken', 'USDC')))
            direction = str(entry.get('dir') or ('Buy' if is_buy else 'Sell'))
            extra_data: dict[str, Any] = {
                'market': raw_coin,
                'side': str(entry.get('side', '')).upper(),
                'direction': direction,
            }
            if 'liquidation' in entry:
                extra_data['liquidation'] = bool(entry['liquidation'])
            if (closed_pnl := entry.get('closedPnl')) is not None:
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
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryBaseEntry]:
        events: list[HistoryBaseEntry] = []
        for context in self._iter_entries_by_time(
            query_type='userFunding',
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ):
            if (parsed := self._parse_funding_entry(context)) is None:
                continue

            event_type = (
                HistoryEventType.RECEIVE if parsed.amount > ZERO else HistoryEventType.SPEND
            )
            events.append(
                self._make_history_event(
                    context=parsed.context,
                    sequence_index=0,
                    event_type=event_type,
                    event_subtype=(
                        HistoryEventSubType.INTEREST
                        if event_type == HistoryEventType.RECEIVE
                        else HistoryEventSubType.NONE
                    ),
                    asset=asset_from_hyperliquid('USDC'),
                    amount=abs(parsed.amount),
                    location_label=address,
                    notes='Hyperliquid funding payment',
                ),
            )

        return events

    def _create_ledger_events(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryBaseEntry]:
        events: list[HistoryBaseEntry] = []
        for context in self._iter_entries_by_time(
            query_type='userNonFundingLedgerUpdates',
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ):
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
                events.append(
                    self._make_history_event(
                        context=parsed.context,
                        sequence_index=0,
                        event_type=HistoryEventType.TRANSFER,
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
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryBaseEntry]:
        events: list[HistoryBaseEntry] = []
        for context in self._iter_entries_by_time(
            query_type='userFillsByTime',
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ):
            if (parsed := self._parse_fill_entry(context)) is None:
                continue

            if parsed.is_spot_fill:
                fee = None
                if parsed.fee_amount != ZERO:
                    fee = AssetAmount(parsed.fee_asset, abs(parsed.fee_amount))
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

            if parsed.fee_amount != ZERO:
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

        return events

    def query_history_events(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryBaseEntry]:
        history: list[HistoryBaseEntry] = []
        history.extend(
            self._create_ledger_events(address=address, start_ts=start_ts, end_ts=end_ts),
        )
        history.extend(
            self._create_funding_events(address=address, start_ts=start_ts, end_ts=end_ts),
        )
        history.extend(
            self._create_fill_events(address=address, start_ts=start_ts, end_ts=end_ts),
        )
        history.sort(
            key=lambda event: (event.timestamp, event.group_identifier, event.sequence_index),
        )
        return history
