from collections import defaultdict
import contextlib
import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.cost_basis.base import AverageCostBasisMethod, CostBasisCalculator
from rotkehlchen.accounting.export.csv import CSVExporter
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.rules import AccountingRulesManager
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import AccountingError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS, Location, Price, Timestamp, TimestampMS, serialized_location_to_key
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_ms_to_sec
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Accountant(CustomizableDateMixin):
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
        super().__init__(database=db)
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.chains_aggregator = chains_aggregator
        self.rules_manager = AccountingRulesManager(
            database=db,
            evm_aggregators=EVMAccountingAggregators([self.rotkehlchen.chains_aggregator.get_evm_manager(x).accounting_aggregator for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS]),  # noqa: E501
        )


        # Compatibility attributes for gradual migration
        self.pots: list[Any] = []  # Will be removed after full migration
        self.first_processed_timestamp = Timestamp(0)
        self.query_start_ts = Timestamp(0)
        self.query_end_ts = Timestamp(0)
        self.currently_processing_timestamp = Timestamp(0)
        with self.database.conn.read_ctx() as cursor:
            self.profit_currency = self.database.get_setting(cursor, 'main_currency')

        self.csvexporter = CSVExporter(database=db)
        self.cost_basis_calculator = CostBasisCalculator(
            database=db,
            msg_aggregator=msg_aggregator,
        )

        # Initialize PnL tracking
        self.pnl_totals = PnlTotals()

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
        with self.database.conn.read_ctx() as cursor:
            self.profit_currency = self.database.get_setting(cursor, 'main_currency')

        # In the new system, we would ensure accounting is calculated
        # up to the end timestamp
        self.ensure_accounting_calculated(up_to_timestamp=end_ts)
        # Return a placeholder report_id since reports system is removed
        return 1

    # --- Prices ---

    def get_rate_in_profit_currency(self, asset: Asset, timestamp: TimestampMS) -> Price:
        """Get the profit_currency price of asset in the given timestamp

        May raise:
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the price oracle
        """
        if asset == self.profit_currency:
            rate = Price(ONE)
        else:
            rate = PriceHistorian().query_historical_price(
                from_asset=asset,
                to_asset=self.profit_currency,
                timestamp=ts_ms_to_sec(timestamp)
            )
        return rate

    def get_prices_for_swap(
            self,
            timestamp: Timestamp,
            amount_in: FVal,
            asset_in: Asset,
            amount_out: FVal,
            asset_out: Asset,
            fee_info: tuple[FVal, Asset] | None,
    ) -> tuple[Price, Price] | None:
        """
        Calculates the prices for assets going in and out of a swap/trade.

        The algorithm is:
        1. Query oracles for prices of asset_out and asset_in.
        2.1 If either of the assets is fiat -- use its amount and price for calculations.
        2.2. If neither of the assets is fiat -- use `out_price` if `out_price` is known,
        otherwise `in_price`.
        3.1 If `fee_info` is provided and it's included in the cost basis,
        fee is included in the price of one of the assets.
        3.2. If `asset_out` is fiat -- fee is added to `calculated_in_price`.
        3.3. If `asset_in` is fiat -- fee is subtracted from `calculated_out_price`.
        3.4. Otherwise fee is added to the price of the asset that was bought.

        Returns (calculated_out_price, calculated_in_price) or None if it can't find proper prices.
        """
        if ZERO in (amount_in, amount_out):
            log.error(
                f'At get_prices_for_swap got a zero amount. {asset_in=} {amount_in=} '
                f'{asset_out=} {amount_out=}. Skipping ...')
            return None

        try:
            out_price = self.get_rate_in_profit_currency(
                asset=asset_out,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError):
            out_price = None

        try:
            in_price = self.get_rate_in_profit_currency(
                asset=asset_in,
                timestamp=timestamp,
            )
        except (PriceQueryUnsupportedAsset, RemoteError):
            in_price = None
        except NoPriceForGivenTimestamp as e:
            in_price = None
            if e.rate_limited is True and out_price is None:
                raise  # in_price = out_price = None -> notify user

        # when `self.settings.include_fees_in_cost_basis == False` we completely ignore fees in
        # this function since they are not included in the cost basis
        fee_price = None
        if fee_info is not None and self.settings.include_fees_in_cost_basis:
            with contextlib.suppress(PriceQueryUnsupportedAsset, RemoteError):
                fee_price = self.get_rate_in_profit_currency(
                    asset=fee_info[1],
                    timestamp=timestamp,
                )

        # Determine whether to use `out_price` or `in_price` for calculations
        price_to_use: Literal['in', 'out']
        if asset_out.is_fiat() and asset_out is not None:
            price_to_use = 'out'  # Use `out_price` if `asset_out` is fiat
        elif asset_in.is_fiat() and asset_in is not None:
            price_to_use = 'in'  # Use `in_price` if `asset_in` is fiat
        elif out_price is not None:
            price_to_use = 'out'  # Prefer `out_price` over `in_price`
        elif in_price is not None:
            price_to_use = 'in'
        else:  # Can't proceed if there is no price known
            return None

        if price_to_use == 'in':
            total_paid = amount_in * in_price  # type: ignore[operator]  # in_price is not None
        else:
            total_paid = amount_out * out_price  # type: ignore[operator]  # out_price is not None

        if asset_in.is_fiat():
            if fee_info is not None and fee_price is not None:
                total_paid -= fee_price * fee_info[0]  # Subtract fee from cost basis

            calculated_out_price = Price(total_paid / amount_out)

            if price_to_use == 'in':
                calculated_in_price = in_price
            else:
                calculated_in_price = Price((amount_out * out_price) / amount_in)  # type: ignore[operator]  # out_price is not None

        else:  # if asset_out is fiat or both assets are crypto or both are fiat
            if fee_info is not None and fee_price is not None:
                total_paid += fee_price * fee_info[0]  # Add fee to cost basis

            calculated_in_price = Price(total_paid / amount_in)

            if price_to_use == 'out':
                calculated_out_price = out_price  # type: ignore[assignment]  # out_price is not None
            else:
                calculated_out_price = Price((amount_in * in_price) / amount_out)  # type: ignore[operator]  # in_price is not None

        return (calculated_out_price, calculated_in_price)  # type: ignore[return-value]  # calculated_in_price is not None

    # --- Core Incremental Accounting ---

    def reset_state(self, settings: DBSettings) -> None:
        """Reset internal state when settings change."""
        self.cost_basis_calculator.reset(settings)
        self.pnl_totals.reset()
        with self.database.conn.read_ctx() as cursor:
            self.profit_currency = self.database.get_setting(cursor, 'main_currency')

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
        from_ts = self._get_earliest_timestamp_missing_accounting(
            settings_hash=settings_hash,
            up_to_timestamp=up_to_timestamp,
        )

        if from_ts is not None:
            log.info(f'Found events missing accounting data from timestamp {from_ts}')

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
        with self.database.user_write() as cursor:
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

    def on_new_history_event(self, event: HistoryBaseEntry) -> None:
        """Called when a new history event is added to invalidate accounting data."""
        event_timestamp = Timestamp(ts_ms_to_sec(event.timestamp))

        # Invalidate accounting data from this event's timestamp onwards
        # This ensures that any new events inserted will trigger recalculation
        self.invalidate_from_timestamp(
            timestamp=event_timestamp,
            affected_assets={event.asset} if hasattr(event, 'asset') else None,
        )

    def process_pending_accounting_work(self, max_events: int = 1000) -> bool:
        """
        Process any pending accounting work.
        Called by task manager when invalidation flag is set.
        Returns True if work was done.

        Args:
            max_events: Maximum number of events to process in one batch
        """
        if not self.has_pending_work():
            return False

        settings_hash = self.get_current_settings_hash()
        log.info(f'Processing pending accounting work for settings hash: {settings_hash}')
        # Get the earliest timestamp that needs accounting calculation
        if (from_ts := self._get_earliest_timestamp_missing_accounting(settings_hash)) is None:
            return False

        # Get current settings for state reset
        with self.database.conn.read_ctx() as cursor:
            settings = self.database.get_settings(cursor)

        # Reset state before processing
        self.reset_state(settings)

        # Calculate accounting data progressively
        events_processed = self._calculate_accounting_for_events(from_ts, settings_hash)

        if events_processed > 0:
            log.info(f'Processed accounting for {events_processed} events')
            return True
        else:
            return False

    def get_current_settings_hash(self) -> str:
        """Generate hash from current global settings + accounting rules"""
        with self.database.conn.read_ctx() as cursor:
            # Get all relevant accounting settings
            settings_data = self._get_accounting_settings_data(cursor)

            # Convert to JSON and hash
            settings_json = json.dumps(settings_data, sort_keys=True)
            return hashlib.sha256(settings_json.encode()).hexdigest()

    def has_pending_work(self) -> bool:
        """Check if there's accounting work pending"""
        settings_hash = self.get_current_settings_hash()
        with self.database.conn.read_ctx() as cursor:
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

        db_events = DBHistoryEvents(self.database)
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

        with self.database.conn.read_ctx() as cursor:
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

    def get_current_pnl_totals(self) -> PnlTotals:
        """Get the current PnL totals from internal tracking."""
        return self.pnl_totals

    # --- Progressive Calculation ---

    def _calculate_accounting_for_events(
            self,
            from_ts: Timestamp,
            settings_hash: str,
    ) -> int:
        """
        Calculate accounting data for events from the given timestamp onwards.
        Events are processed chronologically.
        Returns the number of events processed.

        May raise:
        - No exceptions are raised to the caller. Individual event processing errors
          (UnknownAsset, UnsupportedAsset, DeserializationError, ValueError, ConversionError)
          are logged and the problematic event is skipped.
        """
        log.info(f'Calculating accounting for events from timestamp {from_ts}')

        # Get all events from the timestamp onwards using DBHistoryEvents
        history_events_db = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            events = history_events_db.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(from_ts=from_ts),
                has_premium=True,  # ignore limits for accounting
            )

        if len(events) == 0:
            return 0

        # Step 1: Load progressive state (balances and cost basis)
        first_event_timestamp = Timestamp(ts_ms_to_sec(events[0].timestamp))
        asset_balances = self._load_progressive_state(
            before_timestamp=first_event_timestamp,
        )
        processed_count = 0
        accounting_data_to_insert = []
        balance_data_to_insert = []

        # Step 2: Process events chronologically
        for event in events:
            if (direction := event.maybe_get_direction()) in (EventDirection.NEUTRAL, None):
                log.debug(
                    f'Found event {event} with {direction=} during accounting. Skipping.',
                )
                continue

            # Get balance key for tracking
            total_amount_before = asset_balances[event.get_location_key()][event.asset.identifier]

            # Step 3: Get historical price for this event
            try:
                price = self.get_rate_in_profit_currency(event.asset, event_timestamp)
            except NoPriceForGivenTimestamp:
                # TODO: Add the missing price message for users
                continue

            # Step 4: Determine event taxability using accounting rules
            event_settings, event_callback = self.rules_manager.get_event_settings(event)

            # Step 5: Calculate cost basis and PnL using proper methods
            cost_basis_before, pnl_taxable, pnl_free = self._calculate_cost_basis_and_pnl(
                event=event,
                total_amount_before=total_amount_before,
                price=price,
                is_taxable=is_taxable,
                cost_basis_calculator=self.cost_basis_calculator,
                timestamp=event.timestamp
            )

            # Step 6: Update running balances based on event direction
            if (direction := event.maybe_get_direction()) == EventDirection.IN:
                asset_balances[balance_key] = total_amount_before + event.amount
            elif direction == EventDirection.OUT:  # spend
                asset_balances[balance_key] = total_amount_before - event.amount
                if asset_balances[balance_key] < ZERO:
                    log.warning(
                        f'Negative balance for event {event.identifier}: '
                        f'balance went to {asset_balances[balance_key]}',
                    )
                    asset_balances[balance_key] = ZERO
            else:
                log.debug(
                    f'Found event {event} with neutral direction during accounting. Skipping.',
                )
                continue

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

            # Track PnL for this event
            if pnl_taxable != ZERO or pnl_free != ZERO:
                self.pnl_totals[AccountingEventType.TRANSACTION_EVENT] += PNL(
                    taxable=pnl_taxable,
                    free=pnl_free,
                )

            processed_count += 1


        # Batch insert all accounting data
        if accounting_data_to_insert:
            with self.database.user_write() as write_cursor:
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


    # --- Internal Helper Methods ---

    def _load_progressive_state(
            self,
            before_timestamp: Timestamp,
    ) -> dict[str, dict[Asset, FVal]]:
        """Load progressive state (balances and cost basis) from before the given timestamp.

        Returns the location balances mapping.
        """
        # Initialize empty state and reset internal calculator
        asset_balances: dict[str, dict[Asset, FVal]] = defaultdict(
            lambda: defaultdict(lambda: ZERO)
        )
        self.cost_basis_calculator.reset(self.settings)

        # Load the latest balance state before this timestamp
        with self.database.conn.read_ctx() as cursor:
            cursor.execute("""
                SELECT DISTINCT asset, location, location_label
                FROM asset_location_balances
                WHERE timestamp < ?
            """, (before_timestamp,))

            # For each asset+location combination, get the latest balance
            for asset_id, location_str, location_label in cursor:
                cursor.execute("""
                    SELECT amount FROM asset_location_balances
                    WHERE asset = ? AND location = ? AND location_label = ? AND timestamp < ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (asset_id, location_str, location_label, before_timestamp))

                if (result := cursor.fetchone()):
                    location_key = serialized_location_to_key(location_str, location_label)
                    asset_balances[location_key][asset_id] = FVal(result[0])

        # Load all history events before this timestamp to rebuild cost basis state
        history_events_db = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            events_for_cost_basis = history_events_db.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    to_ts=Timestamp(before_timestamp - 1),  # Exclude the timestamp itself
                ),
                has_premium=True,  # ignore limits for accounting
            )

        # Process events to rebuild cost basis calculator state
        for event in events_for_cost_basis:
            try:
                timestamp_sec = ts_ms_to_sec(event.timestamp)

                # Get price for this event (we need it for cost basis)
                price = self.get_rate_in_profit_currency(event.asset, timestamp_sec)
                # Add to cost basis calculator based on direction
                if (direction := event.maybe_get_direction()) == EventDirection.IN:
                    # This is an acquisition
                    if isinstance(event, HistoryEvent):
                        self.cost_basis_calculator.obtain_asset(
                            event=event,
                            price=price,
                            index=event.identifier or 0,
                        )
                elif direction == EventDirection.OUT:
                    # This is a spend
                    self.cost_basis_calculator.spend_asset(
                        originating_event_id=event.identifier,
                        location=event.location,
                        timestamp=timestamp_sec,
                        asset=event.asset,
                        amount=event.amount,
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
                log.warning(
                    f'Failed to process event {event.identifier} for cost basis state: {e}',
                )
                continue

        return asset_balances

    def _calculate_cost_basis_and_pnl(
            self,
            event: HistoryBaseEntry,
            direction: Literal[EventDirection.IN, EventDirection.OUT],
            total_amount_before: FVal,
            price: Price,
            is_taxable: bool,
            cost_basis_calculator: CostBasisCalculator,
            timestamp: Timestamp,
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
        if direction == EventDirection.IN:
            # This is an acquisition - add to cost basis calculator
            # Calculate cost basis before this acquisition (for display purposes)
            asset_events = cost_basis_calculator.get_events(event.asset)
            acq_mgr = asset_events.get_acquisitions_manager(event.location)
            if isinstance(acq_mgr, AverageCostBasisMethod):
                try:
                    # For ACB method, we can get the current cost basis
                    if acq_mgr.current_amount > ZERO:
                        cost_basis_before = (
                            acq_mgr.current_total_acb /
                            acq_mgr.current_amount
                        )
                except (ZeroDivisionError, ArithmeticError) as e:
                    log.debug(f'Failed to get cost basis before: {e}')

            cost_basis_calculator.obtain_asset(
                event=event,
                price=price,
                index=event.identifier or 0,
            )

        elif direction == EventDirection.OUT:
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
            'cost_basis_by_location',
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

    def _get_earliest_timestamp_missing_accounting(
            self,
            settings_hash: str,
            up_to_timestamp: Timestamp | None = None,
    ) -> Timestamp | None:
        """
        Get the earliest timestamp of events that don't have accounting data for given settings
        """
        with self.database.conn.read_ctx() as cursor:
            timestamp_filter = ''
            params: list[str | int] = [settings_hash]

            if up_to_timestamp is not None:
                timestamp_filter = ' AND he.timestamp <= ?'
                params.append(int(up_to_timestamp))

            cursor.execute(f"""
                SELECT MIN(he.timestamp)
                FROM history_events he
                LEFT JOIN history_events_accounting hea ON he.identifier = hea.history_event_id
                    AND hea.accounting_settings_hash = ?
                WHERE hea.history_event_id IS NULL{timestamp_filter}
            """, params)

            result = cursor.fetchone()
            if result and result[0] is not None:
                return Timestamp(ts_ms_to_sec(result[0]))
            return None
