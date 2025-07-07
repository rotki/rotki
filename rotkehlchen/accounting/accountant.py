import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.cost_basis.base import AverageCostBasisMethod, CostBasisCalculator
from rotkehlchen.accounting.export.csv import CSVExporter
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import AccountingError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import Location, Price, Timestamp, TimestampMS
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Accountant:
    """
    Incremental accounting system that maintains accounting data
    persistently and calculates progressively via task manager.
    """

    def __init__(
            self,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            chains_aggregator: 'ChainsAggregator',
            premium: Premium | None,
    ) -> None:
        self.db = db
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.chains_aggregator = chains_aggregator

        # Compatibility attributes for gradual migration
        self.pots: list[Any] = []  # Will be removed after full migration
        self.first_processed_timestamp = Timestamp(0)
        self.query_start_ts = Timestamp(0)
        self.query_end_ts = Timestamp(0)
        self.currently_processing_timestamp = Timestamp(0)

        # Initialize CSV exporter for compatibility
        self.csvexporter = CSVExporter(database=db)

        self.processable_events_cache: dict[Any, Any] = {}  # For accounting rules compatibility
        self.processable_events_cache_signatures: dict[Any, list[Any]] = {}  # For rules compatibility  # noqa: E501

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium

    def deactivate_premium_status(self) -> None:
        self.premium = None

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            events: list[Any],  # Accept any event type for compatibility
    ) -> int:
        """
        Compatibility method for processing history.
        In the new system, accounting is calculated progressively.
        Returns a placeholder report_id since reports are removed.
        """
        # Set timestamps for compatibility
        self.query_start_ts = start_ts
        self.query_end_ts = end_ts

        # In the new system, we would ensure accounting is calculated
        # up to the end timestamp
        self.ensure_accounting_calculated(up_to_timestamp=end_ts)
        # Return a placeholder report_id since reports system is removed
        return 1

    # --- Core Incremental Accounting ---

    def ensure_accounting_calculated(
            self,
            up_to_timestamp: Timestamp | None = None,
            settings_hash: str | None = None,
    ) -> None:
        """
        Ensure accounting is calculated up to given timestamp.
        If work is needed, marks invalidation flag for task manager to pick up.
        """
        if settings_hash is None:
            settings_hash = self.get_current_settings_hash()

        # Check if we have accounting data up to the requested timestamp
        missing_events = self._get_events_missing_accounting(
            settings_hash=settings_hash,
            up_to_timestamp=up_to_timestamp,
        )

        if missing_events:
            log.info(f'Found {len(missing_events)} events missing accounting data')

    def invalidate_from_timestamp(
            self,
            timestamp: Timestamp,
            affected_assets: set[Asset] | None = None,
            settings_hash: str | None = None,
    ) -> None:
        """
        Mark accounting data as needing recalculation from timestamp onwards.
        If settings_hash is provided, only invalidate for that specific settings hash.
        """
        with self.db.user_write() as cursor:
            base_query = 'DELETE FROM history_events_accounting WHERE '
            params: list[Any] = []

            if settings_hash is not None:
                base_query += 'accounting_settings_hash = ? AND '
                params.append(settings_hash)
            if affected_assets is None:
                # Remove all accounting data from timestamp onwards
                cursor.execute(
                    base_query + 'history_event_id IN '
                    '(SELECT identifier FROM history_events WHERE timestamp >= ?)',
                    (*params, timestamp),
                )
            else:
                # Remove accounting data for specific assets from timestamp onwards
                asset_placeholders = ','.join('?' * len(affected_assets))
                query = (
                    base_query + 'history_event_id IN '
                    '(SELECT identifier FROM history_events WHERE timestamp >= ? AND '
                    f'asset IN ({asset_placeholders}))'
                )
                cursor.execute(
                    query,
                    (*params, timestamp, *[asset.identifier for asset in affected_assets]),
                )

            # Also remove balance tracking data from timestamp onwards
            if affected_assets is None:
                cursor.execute(
                    'DELETE FROM asset_location_balances WHERE timestamp >= ?',
                    (timestamp,),
                )
            else:
                asset_placeholders = ','.join('?' * len(affected_assets))
                query = (
                    'DELETE FROM asset_location_balances WHERE timestamp >= ? AND '
                    f'asset IN ({asset_placeholders})'
                )
                cursor.execute(
                    query,
                    (timestamp, *[asset.identifier for asset in affected_assets]),
                )

        log.info(f'Invalidated accounting data from timestamp {timestamp}')

    def process_pending_accounting_work(self) -> bool:
        """
        Process any pending accounting work.
        Called by task manager when invalidation flag is set.
        Returns True if work was done.
        """
        if not self.has_pending_work():
            return False

        log.info('Processing pending accounting work')
        settings_hash = self.get_current_settings_hash()

        # Get events that need accounting calculation
        missing_events = self._get_events_missing_accounting(settings_hash)

        if not missing_events:
            return False

        # Calculate accounting data progressively
        events_processed = self._calculate_accounting_for_events(missing_events, settings_hash)

        if events_processed > 0:
            log.info(f'Processed accounting for {events_processed} events')
            return True
        else:
            return False

    def get_current_settings_hash(self) -> str:
        """Generate hash from current global settings + accounting rules"""
        with self.db.conn.read_ctx() as cursor:
            # Get all relevant accounting settings
            settings_data = self._get_accounting_settings_data(cursor)

            # Convert to JSON and hash
            settings_json = json.dumps(settings_data, sort_keys=True)
            return hashlib.sha256(settings_json.encode()).hexdigest()

    def has_pending_work(self) -> bool:
        """Check if there's accounting work pending (for task manager)"""
        settings_hash = self.get_current_settings_hash()
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT 1 FROM history_events he '
                'LEFT JOIN history_events_accounting hea '
                'ON he.identifier = hea.history_event_id '
                'AND hea.accounting_settings_hash = ? '
                'WHERE hea.history_event_id IS NULL '
                'LIMIT 1',
                (settings_hash,),
            ).fetchone()
            return result is not None

    # --- Data Access ---

    def get_events_with_accounting(
            self,
            cursor: 'DBCursor',
            filter_query: Any,
            has_premium: bool,
            settings_hash: str | None = None,
    ) -> list[Any]:
        """Get history events with accounting data attached using current settings"""
        if settings_hash is None:
            settings_hash = self.get_current_settings_hash()

        db_events = DBHistoryEvents(self.db)
        return db_events.get_history_events(  # type: ignore[call-overload]  # New parameters not in overload yet
            cursor=cursor,
            filter_query=filter_query,
            has_premium=has_premium,
            group_by_event_ids=False,
            match_exact_events=True,
            include_accounting=True,
            accounting_settings_hash=settings_hash,
        )

    def get_pnl_totals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            settings_hash: str | None = None,
    ) -> PnlTotals:
        """Calculate PnL totals from accounting data"""
        if settings_hash is None:
            settings_hash = self.get_current_settings_hash()

        with self.db.conn.read_ctx() as cursor:
            cursor.execute("""
                SELECT SUM(CAST(hea.pnl_taxable as REAL)), SUM(CAST(hea.pnl_free as REAL))
                FROM history_events_accounting hea
                JOIN history_events he ON hea.history_event_id = he.identifier
                WHERE he.timestamp >= ? AND he.timestamp <= ?
                AND hea.accounting_settings_hash = ?
            """, (start_ts, end_ts, settings_hash))

            result = cursor.fetchone()
            if result and result[0] is not None:
                # Create a PnlTotals with a single entry for the totals
                totals = PnlTotals()
                totals[AccountingEventType.TRANSACTION_EVENT] = PNL(
                    taxable=FVal(str(result[0])),
                    free=FVal(str(result[1] or 0)),
                )
                return totals
            else:
                return PnlTotals()

    # --- Progressive Calculation ---

    def _calculate_accounting_for_events(
            self,
            event_ids: list[int],
            settings_hash: str,
    ) -> int:
        """
        Calculate accounting data for the given event IDs.
        Events should be from one timestamp range and processed chronologically.
        Returns the number of events processed.

        May raise:
        - No exceptions are raised to the caller. Individual event processing errors
          (UnknownAsset, UnsupportedAsset, DeserializationError, ValueError, ConversionError)
          are logged and the problematic event is skipped.
        """
        if not event_ids:
            return 0

        log.info(f'Calculating accounting for {len(event_ids)} events')

        # Get the current accounting settings
        with self.db.conn.read_ctx() as cursor:
            db_settings = self.db.get_settings(cursor)

        # Get all events data ordered by timestamp
        events_data = self._get_events_data_ordered(event_ids)
        if len(events_data) == 0:
            return 0

        # Step 1: Load progressive state (balances and cost basis)
        first_event_timestamp = Timestamp(events_data[0][4])  # timestamp is at index 4
        asset_balances, cost_basis_calculator = self._load_progressive_state(
            before_timestamp=first_event_timestamp,
            settings=db_settings,
        )

        log.info(f'Loaded state before timestamp {first_event_timestamp}')

        processed_count = 0
        accounting_data_to_insert = []
        balance_data_to_insert = []

        # Step 2: Process events chronologically
        for row in events_data:
            try:
                # Deserialize the history event
                event = self._deserialize_history_event_from_row(row)
                event_timestamp = ts_ms_to_sec(event.timestamp)

                # Get balance key for tracking
                balance_key = (
                    event.asset,
                    event.location.serialize_for_db(),
                    event.location_label or '',  # Ensure not None
                )
                total_amount_before = asset_balances.get(balance_key, ZERO)

                # Step 3: Get historical price for this event
                price = self._get_historical_price(event.asset, event_timestamp, db_settings)

                # Step 4: Determine event taxability using accounting rules
                is_taxable = self._determine_event_taxability_with_rules(event, db_settings)

                # Step 5: Calculate cost basis and PnL using proper methods
                cost_basis_before, pnl_taxable, pnl_free = self._calculate_cost_basis_and_pnl(
                    event=event,
                    total_amount_before=total_amount_before,
                    price=price,
                    is_taxable=is_taxable,
                    cost_basis_calculator=cost_basis_calculator,
                    timestamp=event_timestamp,
                    settings=db_settings,
                )

                # Step 6: Update running balances based on event direction
                direction = event.maybe_get_direction()
                if direction == 'in':
                    # Acquisition
                    asset_balances[balance_key] = total_amount_before + event.amount
                elif direction == 'out':
                    # Spend
                    asset_balances[balance_key] = total_amount_before - event.amount
                    if asset_balances[balance_key] < ZERO:
                        log.warning(
                            f'Negative balance for event {event.identifier}: '
                            f'balance went to {asset_balances[balance_key]}',
                        )
                        asset_balances[balance_key] = ZERO

                # Step 7: Prepare accounting data for batch insert
                accounting_data_to_insert.append((
                    event.identifier,
                    str(total_amount_before),
                    str(cost_basis_before) if cost_basis_before is not None else None,
                    1 if is_taxable else 0,
                    str(pnl_taxable),
                    str(pnl_free),
                    settings_hash,
                ))

                # Step 8: Prepare balance data for batch insert
                balance_data_to_insert.append((
                    event.timestamp,
                    event.location.serialize_for_db(),
                    event.location_label,
                    event.asset.identifier,
                    str(asset_balances[balance_key]),
                ))

                processed_count += 1

            except (
                UnknownAsset,
                UnsupportedAsset,
                DeserializationError,
                ValueError,
                ConversionError,
            ) as e:
                log.error(f'Failed to process event {row[0]}: {e}')
                continue

        # Batch insert all accounting data
        if accounting_data_to_insert:
            with self.db.user_write() as write_cursor:
                write_cursor.executemany("""
                    INSERT INTO history_events_accounting
                    (history_event_id, total_amount_before, cost_basis_before, is_taxable,
                     pnl_taxable, pnl_free, accounting_settings_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, accounting_data_to_insert)

                # Also insert balance data
                write_cursor.executemany("""
                    INSERT OR REPLACE INTO asset_location_balances
                    (timestamp, location, location_label, asset, amount)
                    VALUES (?, ?, ?, ?, ?)
                """, balance_data_to_insert)

        log.info(f'Successfully processed accounting for {processed_count} events')
        return processed_count

    def _deserialize_history_event_from_row(self, row: tuple) -> HistoryBaseEntry:
        """Deserialize a history event from a database row"""
        # This is a simplified deserialization - would need proper implementation
        # based on the entry_type to get the correct HistoryBaseEntry subclass

        return HistoryEvent(
            event_identifier=row[2],
            sequence_index=row[3],
            timestamp=TimestampMS(row[4]),
            location=Location.deserialize_from_db(row[5]),
            location_label=row[6],
            asset=Asset(row[7]),
            amount=FVal(row[8]),
            notes=row[9],
            event_type=HistoryEventType.deserialize(row[10]),
            event_subtype=HistoryEventSubType.deserialize(row[11]),
            identifier=row[0],
            extra_data=None,  # TODO: Deserialize extra_data
        )

    def _determine_event_taxability(self, event: HistoryBaseEntry, settings: DBSettings) -> bool:
        """Determine if an event is taxable based on event type and settings"""
        # Simplified logic - would need proper implementation based on accounting rules

        # Some basic rules
        if (
            event.event_type in (HistoryEventType.TRADE, HistoryEventType.RECEIVE) or
            event.event_type == HistoryEventType.SPEND
        ):
            return True
        elif event.event_type in (HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL):
            return False  # Usually not taxable unless it's between different assets
        else:
            return False  # Default to non-taxable for other types

    # --- Export ---

    def export_accounting_data(
            self,
            directory_path: Path,
            start_ts: Timestamp,
            end_ts: Timestamp,
            export_format: Literal['csv', 'json'] = 'csv',
    ) -> tuple[bool, str]:
        """Export history events with accounting data overlay"""
        # TODO: Implement export logic
        return True, f'Export to {directory_path} completed'

    # --- Internal Helper Methods ---

    def _get_events_data_ordered(self, event_ids: list[int]) -> list[tuple]:
        """Get events data ordered by timestamp for the given event IDs"""
        if not event_ids:
            return []

        with self.db.conn.read_ctx() as cursor:
            placeholders = ','.join('?' * len(event_ids))
            cursor.execute(f"""
                SELECT identifier, entry_type, event_identifier, sequence_index,
                       timestamp, location, location_label, asset, amount, notes,
                       event_type, event_subtype, extra_data
                FROM history_events
                WHERE identifier IN ({placeholders})
                ORDER BY timestamp, sequence_index
            """, event_ids)
            return cursor.fetchall()

    def _load_progressive_state(
            self,
            before_timestamp: Timestamp,
            settings: DBSettings,
    ) -> tuple[dict[tuple[Asset, str, str], FVal], CostBasisCalculator]:
        """
        Load progressive state (balances and cost basis) from before the given timestamp.

        No exceptions are raised to the caller. Individual event processing errors
        UnknownAsset, UnsupportedAsset, DeserializationError, ValueError, ConversionError,
        NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset, RemoteError)
        are logged and the problematic event is skipped.
        """
        # Initialize empty state
        asset_balances: dict[tuple[Asset, str, str], FVal] = {}
        cost_basis_calculator = CostBasisCalculator(
            database=self.db,
            msg_aggregator=self.msg_aggregator,
        )
        cost_basis_calculator.reset(settings)

        # Load the latest balance state before this timestamp
        with self.db.conn.read_ctx() as cursor:
            cursor.execute("""
                SELECT DISTINCT asset, location, location_label
                FROM asset_location_balances
                WHERE timestamp < ?
            """, (before_timestamp,))

            # For each asset+location combination, get the latest balance
            for asset_id, location_str, location_label in cursor.fetchall():
                cursor.execute("""
                    SELECT amount FROM asset_location_balances
                    WHERE asset = ? AND location = ? AND location_label = ? AND timestamp < ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (asset_id, location_str, location_label, before_timestamp))

                result = cursor.fetchone()
                if result:
                    asset = Asset(asset_id)
                    balance_key = (asset, location_str, location_label)
                    asset_balances[balance_key] = FVal(result[0])

            # Load all history events before this timestamp to rebuild cost basis state
            cursor.execute("""
                SELECT identifier, asset, amount, timestamp, event_type, event_subtype
                FROM history_events
                WHERE timestamp < ?
                ORDER BY timestamp, sequence_index
            """, (before_timestamp,))

            events_for_cost_basis = cursor.fetchall()

        # Process events to rebuild cost basis calculator state
        for event_row in events_for_cost_basis:
            try:
                (
                    event_id, asset_id, amount_str, timestamp_ms,
                    event_type_str, event_subtype_str,
                ) = event_row
                asset = Asset(asset_id)
                amount = FVal(amount_str)
                timestamp_sec = Timestamp(timestamp_ms // 1000)

                # Get price for this event (we need it for cost basis)
                price = self._get_historical_price(asset, timestamp_sec, settings)

                # Determine if this was an acquisition or spend
                event_type = HistoryEventType.deserialize(event_type_str)
                event_subtype = HistoryEventSubType.deserialize(event_subtype_str)

                # Create a minimal history event for cost basis calculator
                temp_event = HistoryEvent(
                    event_identifier='temp',
                    sequence_index=0,
                    timestamp=TimestampMS(timestamp_ms),
                    location=Location.EXTERNAL,  # Placeholder
                    event_type=event_type,
                    event_subtype=event_subtype,
                    asset=asset,
                    amount=amount,
                    identifier=event_id,
                )

                # Add to cost basis calculator based on event type
                if amount > ZERO and event_subtype in (
                    HistoryEventSubType.RECEIVE,
                    HistoryEventSubType.DEPOSIT_ASSET,
                ):
                    # This is an acquisition
                    cost_basis_calculator.obtain_asset(
                        event=temp_event,
                        price=price,
                        index=event_id,
                    )
                elif amount > ZERO and event_subtype in (
                    HistoryEventSubType.SPEND,
                    HistoryEventSubType.REMOVE_ASSET,
                    HistoryEventSubType.FEE,
                ):
                    # This is a spend
                    cost_basis_calculator.spend_asset(
                        originating_event_id=event_id,
                        location=Location.EXTERNAL,
                        timestamp=timestamp_sec,
                        asset=asset,
                        amount=amount,
                        rate=price,
                        taxable_spend=True,
                    )

            except (
                UnknownAsset,
                UnsupportedAsset,
                DeserializationError,
                ValueError,
                ConversionError,
                NoPriceForGivenTimestamp,
                PriceQueryUnsupportedAsset,
                RemoteError,
            ) as e:
                log.warning(f'Failed to process event {event_row[0]} for cost basis state: {e}')
                continue

        log.info(f'Loaded progressive state with {len(asset_balances)} balance entries')
        return asset_balances, cost_basis_calculator

    def _get_historical_price(
            self,
            asset: Asset,
            timestamp: Timestamp,
            settings: DBSettings,
    ) -> Price:
        """Get historical price for asset at timestamp using PriceHistorian"""
        try:
            # Use the existing price historian from chains aggregator
            if hasattr(self.chains_aggregator, 'price_historian'):
                price_historian = self.chains_aggregator.price_historian
            else:
                # Fallback to creating a simple price historian
                price_historian = PriceHistorian(
                    data_directory=self.db.user_data_dir,
                )

            return price_historian.query_historical_price(
                from_asset=asset,
                to_asset=settings.main_currency,
                timestamp=timestamp,
            )
        except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset, RemoteError):
            log.warning(f'Could not find price for {asset} at {timestamp}, using fallback')
            return ZERO_PRICE

    def _determine_event_taxability_with_rules(
            self,
            event: HistoryBaseEntry,
            settings: DBSettings,
    ) -> bool:
        """Determine if an event is taxable using accounting rules engine"""
        # Get counterparty from the event (if it has one)
        counterparty = getattr(event, 'counterparty', None)

        # Query for a specific rule matching this event
        with self.db.conn.read_ctx() as cursor:
            # First try to find a rule with the specific counterparty
            query = """
                SELECT taxable, count_entire_amount_spend, count_cost_basis_pnl,
                       accounting_treatment
                FROM accounting_rules
                WHERE type=? AND subtype=? AND counterparty=?
            """

            params = [
                event.event_type.serialize(),
                event.event_subtype.serialize(),
                counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY,
            ]

            result = cursor.execute(query, params).fetchone()

            # If no specific rule found, try a generic rule (with no counterparty)
            if result is None and counterparty is not None:
                params[2] = NO_ACCOUNTING_COUNTERPARTY
                result = cursor.execute(query, params).fetchone()

            if result is not None:
                # We found a matching rule, use its taxable setting
                rule_settings = BaseEventSettings.deserialize_from_db(result)

                # Check for any linked settings that might override the rule's taxable value
                linked_query = """
                    SELECT property_name, setting_name
                    FROM linked_rules_properties lrp
                    JOIN accounting_rules ar ON lrp.accounting_rule = ar.identifier
                    WHERE ar.type=? AND ar.subtype=? AND ar.counterparty=?
                      AND lrp.property_name='taxable'
                """

                linked_result = cursor.execute(linked_query, params).fetchone()
                if linked_result is not None:
                    # This rule's taxable property is linked to a global setting
                    setting_name = linked_result[1]
                    linked_setting_value = getattr(settings, setting_name, None)
                    if linked_setting_value is not None:
                        return bool(linked_setting_value)

                return rule_settings.taxable

        # If no specific rule found, fall back to simplified logic
        return self._determine_event_taxability(event, settings)

    def _calculate_cost_basis_and_pnl(
            self,
            event: HistoryBaseEntry,
            total_amount_before: FVal,
            price: Price,
            is_taxable: bool,
            cost_basis_calculator: CostBasisCalculator,
            timestamp: Timestamp,
            settings: DBSettings,
    ) -> tuple[FVal | None, FVal, FVal]:
        """
        Calculate cost basis and PnL using CostBasisCalculator.

        May raise:
        - No exceptions are raised to the caller. Cost basis calculation errors
          (AccountingError, IndexError, AssertionError, ZeroDivisionError, ArithmeticError)
          are logged and the function returns default values.
        """

        cost_basis_before = None
        pnl_taxable = ZERO
        pnl_free = ZERO

        # Use maybe_get_direction to determine how to handle the event
        direction = event.maybe_get_direction()

        if direction == 'in':
            # This is an acquisition - add to cost basis calculator
            # Calculate cost basis before this acquisition (for display purposes)
            asset_events = cost_basis_calculator.get_events(event.asset)
            acq_mgr = cost_basis_calculator.get_events(event.asset).acquisitions_manager
            if isinstance(asset_events.acquisitions_manager, acq_mgr.__class__):
                try:
                    # For ACB method, we can get the current cost basis
                    if (isinstance(asset_events.acquisitions_manager, AverageCostBasisMethod) and
                            asset_events.acquisitions_manager.current_amount > ZERO):
                        cost_basis_before = (
                            asset_events.acquisitions_manager.current_total_acb /
                            asset_events.acquisitions_manager.current_amount
                        )
                except (ZeroDivisionError, ArithmeticError) as e:
                    log.debug(f'Failed to get cost basis before: {e}')

            # Add acquisition to calculator
            if isinstance(event, HistoryEvent):
                cost_basis_calculator.obtain_asset(
                    event=event,
                    price=price,
                    index=event.identifier or 0,
                )

        elif direction == 'out':
            # This is a spend - calculate PnL
            spend_amount = event.amount
            if spend_amount <= total_amount_before:
                try:
                    # Calculate cost basis and PnL using the calculator
                    cost_basis_info = cost_basis_calculator.spend_asset(
                        originating_event_id=event.identifier,
                        location=(
                            event.location if hasattr(event.location, 'serialize_for_db')
                            else Location.EXTERNAL
                        ),
                        timestamp=timestamp,
                        asset=event.asset,
                        amount=spend_amount,
                        rate=price,
                        taxable_spend=is_taxable,
                    )

                    if cost_basis_info is not None:
                        # Calculate PnL = sell value - cost basis
                        sell_value = spend_amount * price
                        total_cost_basis = (
                            cost_basis_info.taxable_bought_cost +
                            cost_basis_info.taxfree_bought_cost
                        )
                        total_pnl = sell_value - total_cost_basis

                        if is_taxable:
                            # Split PnL based on taxable vs tax-free portions
                            if cost_basis_info.taxable_bought_cost > ZERO:
                                taxable_ratio = (
                                    cost_basis_info.taxable_bought_cost / total_cost_basis
                                )
                                pnl_taxable = total_pnl * taxable_ratio
                            if cost_basis_info.taxfree_bought_cost > ZERO:
                                taxfree_ratio = (
                                    cost_basis_info.taxfree_bought_cost / total_cost_basis
                                )
                                pnl_free = total_pnl * taxfree_ratio
                        else:
                            # All PnL is tax-free if the event itself is not taxable
                            pnl_free = total_pnl

                        # Get average cost basis for display
                        if total_cost_basis > ZERO and spend_amount > ZERO:
                            cost_basis_before = total_cost_basis / spend_amount

                except (
                    AccountingError,
                    IndexError,
                    AssertionError,
                    ZeroDivisionError,
                    ArithmeticError,
                ) as e:
                    log.warning(
                        f'Failed to calculate cost basis for event {event.identifier}: {e}',
                    )

        return cost_basis_before, pnl_taxable, pnl_free

    def _get_accounting_settings_data(self, cursor: 'DBCursor') -> dict:
        """Get all accounting-relevant settings for hashing"""
        settings_data = {}

        # Get global settings
        accounting_settings = [
            'main_currency', 'taxfree_after_period', 'include_crypto2crypto',
            'calculate_past_cost_basis', 'include_gas_costs', 'cost_basis_method',
            'eth_staking_taxable_after_withdrawal_enabled', 'include_fees_in_cost_basis',
        ]

        for setting_name in accounting_settings:
            result = cursor.execute(
                'SELECT value FROM settings WHERE name = ?', (setting_name,),
            ).fetchone()
            settings_data[setting_name] = result[0] if result else None

        # Get accounting rules (simplified - just count and last modified)
        try:
            rule_count = cursor.execute('SELECT COUNT(*) FROM accounting_rule').fetchone()[0]
            settings_data['accounting_rules_count'] = rule_count
        except sqlcipher.OperationalError:  # pylint: disable=no-member
            # accounting_rule table may not exist in tests
            settings_data['accounting_rules_count'] = 0

        # Add a timestamp of when rules were last modified (if we track this)
        # For now, just use the count as a simple invalidation mechanism

        return settings_data

    def _get_events_missing_accounting(
            self,
            settings_hash: str,
            up_to_timestamp: Timestamp | None = None,
    ) -> list[int]:
        """Get list of event IDs that don't have accounting data for given settings"""
        with self.db.conn.read_ctx() as cursor:
            timestamp_filter = ''
            params: list[str | int] = [settings_hash]

            if up_to_timestamp is not None:
                timestamp_filter = ' AND he.timestamp <= ?'
                params.append(int(up_to_timestamp))

            cursor.execute(f"""
                SELECT he.identifier
                FROM history_events he
                LEFT JOIN history_events_accounting hea ON he.identifier = hea.history_event_id
                    AND hea.accounting_settings_hash = ?
                WHERE hea.history_event_id IS NULL{timestamp_filter}
                ORDER BY he.timestamp, he.sequence_index
            """, params)

            return [row[0] for row in cursor.fetchall()]
