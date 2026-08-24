import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import (
    HistoryEvent,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import Location, TimestampMS
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KrakenFuturesHistoryEvent = HistoryEvent | SwapEvent


@dataclass(frozen=True)
class KrakenFuturesLogEntry:
    """Validated fields needed to turn a Kraken Futures account-log row into events."""

    raw: dict[str, Any]
    booking_uid: str
    entry_id: int
    timestamp: TimestampMS
    asset_symbol: str
    contract: str | None
    execution_id: str | None
    info: str
    margin_account: str
    old_balance: FVal
    new_balance: FVal
    realized_pnl: FVal
    realized_funding: FVal
    fee: FVal
    liquidation_fee: FVal


def _get_required_log_string(entry: dict[str, Any], key: str) -> str:
    """Return a required non-empty string from a Futures account-log row."""
    if not isinstance(value := entry[key], str) or value == '':
        raise DeserializationError(f'Invalid {key} in Kraken Futures account-log entry')

    return value


def _get_optional_log_string(entry: dict[str, Any], key: str) -> str | None:
    """Return an optional string from a Futures account-log row."""
    if (value := entry[key]) is None:
        return None
    if not isinstance(value, str) or value == '':
        raise DeserializationError(f'Invalid {key} in Kraken Futures account-log entry')

    return value


def _deserialize_log_amount(entry: dict[str, Any], key: str) -> FVal:
    """Deserialize an optional Futures account-log amount, treating null as zero."""
    return deserialize_fval(
        value=entry[key] if entry[key] is not None else ZERO,
        name=key,
        location='Kraken Futures account-log',
    )


def _deserialize_log_entry(entry: dict[str, Any]) -> KrakenFuturesLogEntry:
    """Validate and deserialize the fields used by the Futures history integration."""
    entry_id = entry['id']
    if not isinstance(entry_id, int) or isinstance(entry_id, bool) or entry_id < 1:
        raise DeserializationError('Invalid id in Kraken Futures account-log entry')

    return KrakenFuturesLogEntry(
        raw=entry,
        booking_uid=_get_required_log_string(entry, 'booking_uid'),
        entry_id=entry_id,
        timestamp=ts_sec_to_ms(iso8601ts_to_timestamp(
            _get_required_log_string(entry, 'date'),
        )),
        asset_symbol=_get_required_log_string(entry, 'asset'),
        contract=_get_optional_log_string(entry, 'contract'),
        execution_id=_get_optional_log_string(entry, 'execution'),
        info=_get_required_log_string(entry, 'info'),
        margin_account=_get_required_log_string(entry, 'margin_account'),
        old_balance=_deserialize_log_amount(entry, 'old_balance'),
        new_balance=_deserialize_log_amount(entry, 'new_balance'),
        realized_pnl=_deserialize_log_amount(entry, 'realized_pnl'),
        realized_funding=_deserialize_log_amount(entry, 'realized_funding'),
        fee=_deserialize_log_amount(entry, 'fee'),
        liquidation_fee=_deserialize_log_amount(entry, 'liquidation_fee'),
    )


@dataclass(frozen=True)
class KrakenFuturesAccountLogProcessor:
    """Turn Kraken Futures account-log rows into collateral history events."""

    account_uid: str
    location_label: str

    def process(
            self,
            logs: list[dict[str, Any]],
    ) -> tuple[list[KrakenFuturesHistoryEvent], list[dict[str, Any]]]:
        """Turn actual Futures collateral changes into events, retaining failures for retry."""
        entries: list[KrakenFuturesLogEntry] = []
        skipped_logs: list[dict[str, Any]] = []
        for raw_log in logs:
            try:
                entries.append(_deserialize_log_entry(raw_log))
            except (DeserializationError, KeyError) as e:
                log.error(
                    'Failed to deserialize Kraken Futures account-log row %s: %s', raw_log, e,
                )
                skipped_logs.append(raw_log)

        positions_by_execution: dict[str, list[KrakenFuturesLogEntry]] = {}
        collateral_groups: dict[str, list[KrakenFuturesLogEntry]] = {}
        for entry in entries:
            if entry.contract is not None and entry.asset_symbol == entry.contract:
                if entry.execution_id is not None:
                    positions_by_execution.setdefault(entry.execution_id, []).append(entry)
                continue  # Position size is metadata, not an asset transfer.

            group_key = (
                f'conversion:{entry.timestamp}:{entry.margin_account}'
                if entry.info == 'conversion' else entry.execution_id or entry.booking_uid
            )
            collateral_groups.setdefault(group_key, []).append(entry)

        events: list[KrakenFuturesHistoryEvent] = []
        for group_key, collateral_entries in collateral_groups.items():
            if collateral_entries[0].info == 'conversion':
                collateral_entries.sort(key=lambda item: (
                    item.new_balance >= item.old_balance,
                    item.entry_id,
                ))
            group_identifier = create_group_identifier_from_unique_id(
                location=Location.KRAKEN,
                unique_id=f'{self.account_uid}:{group_key}',
            )
            position_entries = positions_by_execution.get(group_key, [])
            group_events: list[KrakenFuturesHistoryEvent] = []
            sequence_index = 0
            for entry in collateral_entries:
                try:
                    new_events = self._process_collateral_entry(
                        entry=entry,
                        group_identifier=group_identifier,
                        position_entries=position_entries,
                        sequence_index=sequence_index,
                    )
                except (DeserializationError, UnknownAsset) as e:
                    log.error(
                        'Failed to process Kraken Futures account-log row %s: %s', entry.raw, e,
                    )
                    skipped_logs.extend(item.raw for item in collateral_entries)
                    skipped_logs.extend(item.raw for item in position_entries)
                    break

                group_events.extend(new_events)
                sequence_index += len(new_events)
            else:
                events.extend(group_events)

        events.sort(
            key=lambda event: (event.timestamp, event.group_identifier, event.sequence_index),
        )
        return events, skipped_logs

    def _process_collateral_entry(
            self,
            entry: KrakenFuturesLogEntry,
            group_identifier: str,
            position_entries: list[KrakenFuturesLogEntry],
            sequence_index: int,
    ) -> list[KrakenFuturesHistoryEvent]:
        """Create events only when their amounts reconcile to the collateral balance change."""
        actual_delta = entry.new_balance - entry.old_balance
        if entry.info == 'cross-exchange transfer':
            return []  # The spot ledger side is the canonical internal-wallet transfer event.

        asset = asset_from_kraken(entry.asset_symbol.upper())
        extra_data = self._event_extra_data(entry=entry, position_entries=position_entries)
        if entry.info == 'conversion':
            if actual_delta == ZERO:
                return []

            extra_data['component'] = 'conversion'
            return [SwapEvent(
                group_identifier=group_identifier,
                sequence_index=sequence_index,
                timestamp=entry.timestamp,
                location=Location.KRAKEN,
                event_subtype=(
                    HistoryEventSubType.RECEIVE
                    if actual_delta > ZERO else HistoryEventSubType.SPEND
                ),
                asset=asset,
                amount=abs(actual_delta),
                location_label=self.location_label,
                notes='Kraken Futures collateral conversion',
                extra_data=extra_data,
            )]

        expected_delta = (
            entry.realized_pnl +
            entry.realized_funding -
            entry.fee -
            entry.liquidation_fee
        )
        if actual_delta != expected_delta:
            raise DeserializationError(
                f'Collateral balance delta {actual_delta} does not match its components '
                f'{expected_delta} for booking {entry.booking_uid}',
            )

        events: list[KrakenFuturesHistoryEvent] = []
        for component, amount in (
            ('realized_pnl', entry.realized_pnl),
            ('realized_funding', entry.realized_funding),
            ('fee', entry.fee),
            ('liquidation_fee', entry.liquidation_fee),
        ):
            if amount == ZERO:
                continue

            event_extra_data = extra_data.copy()
            event_extra_data['component'] = component
            if component in {'realized_pnl', 'realized_funding'}:
                event_type = HistoryEventType.MARGIN
                event_subtype = (
                    HistoryEventSubType.PROFIT if amount > ZERO else HistoryEventSubType.LOSS
                )
                component_label = 'realized PnL' if component == 'realized_pnl' else 'funding'
            else:
                event_type = HistoryEventType.SPEND if amount > ZERO else HistoryEventType.RECEIVE
                event_subtype = (
                    HistoryEventSubType.FEE if amount > ZERO else HistoryEventSubType.REWARD
                )
                component_label = 'liquidation fee' if component == 'liquidation_fee' else 'fee'

            contract_suffix = f' for {entry.contract}' if entry.contract is not None else ''
            events.append(HistoryEvent(
                group_identifier=group_identifier,
                sequence_index=sequence_index + len(events),
                timestamp=entry.timestamp,
                location=Location.KRAKEN,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                amount=abs(amount),
                location_label=self.location_label,
                notes=f'Kraken Futures {component_label}{contract_suffix} ({entry.info})',
                extra_data=event_extra_data,
            ))

        return events

    def _event_extra_data(
            self,
            entry: KrakenFuturesLogEntry,
            position_entries: list[KrakenFuturesLogEntry],
    ) -> dict[str, Any]:
        """Keep the source identity and position changes without inventing contract assets."""
        extra_data: dict[str, Any] = {
            'account_uid': self.account_uid,
            'booking_uid': entry.booking_uid,
            'entry_id': entry.entry_id,
            'info': entry.info,
            'margin_account': entry.margin_account,
            'new_balance': str(entry.new_balance),
            'old_balance': str(entry.old_balance),
        }
        if entry.contract is not None:
            extra_data['contract'] = entry.contract
        if entry.execution_id is not None:
            extra_data['execution_id'] = entry.execution_id
        if position_entries:
            extra_data['position_changes'] = [{
                'booking_uid': position.booking_uid,
                'new_average_entry_price': position.raw.get('new_average_entry_price'),
                'new_size': str(position.new_balance),
                'old_average_entry_price': position.raw.get('old_average_entry_price'),
                'old_size': str(position.old_balance),
                'trade_price': position.raw.get('trade_price'),
            } for position in position_entries]

        return extra_data
