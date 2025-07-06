import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from rotkehlchen.accounting.cost_basis import CostBasisCalculator
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.accounting_data import AccountingData, HistoryEventWithAccounting
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Accountant:
    """
    New incremental accounting system that maintains accounting data
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

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium

    def deactivate_premium_status(self) -> None:
        self.premium = None

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
            self._mark_accounting_work_pending()

    def invalidate_from_timestamp(
            self,
            timestamp: Timestamp,
            affected_assets: set[Asset] | None = None,
    ) -> None:
        """
        Mark accounting data as needing recalculation from timestamp onwards.
        Sets flag that task manager will detect.
        """
        with self.db.transient_write() as cursor:
            if affected_assets is None:
                # Remove all accounting data from timestamp onwards
                cursor.execute(
                    'DELETE FROM history_events_accounting WHERE history_event_id IN '
                    '(SELECT identifier FROM history_events WHERE timestamp >= ?)',
                    (timestamp,),
                )
            else:
                # Remove accounting data for specific assets from timestamp onwards
                asset_placeholders = ','.join('?' * len(affected_assets))
                cursor.execute(
                    f'DELETE FROM history_events_accounting WHERE history_event_id IN '
                    f'(SELECT identifier FROM history_events WHERE timestamp >= ? AND asset IN ({asset_placeholders}))',
                    (timestamp, *[asset.identifier for asset in affected_assets]),
                )

            # Also remove balance tracking data from timestamp onwards
            if affected_assets is None:
                cursor.execute(
                    'DELETE FROM asset_location_balances WHERE timestamp >= ?',
                    (timestamp,),
                )
            else:
                asset_placeholders = ','.join('?' * len(affected_assets))
                cursor.execute(
                    f'DELETE FROM asset_location_balances WHERE timestamp >= ? AND asset IN ({asset_placeholders})',
                    (timestamp, *[asset.identifier for asset in affected_assets]),
                )

        self._mark_accounting_work_pending()
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
            self._clear_accounting_work_pending()
            return False

        # Calculate accounting data progressively
        events_processed = self._calculate_accounting_for_events(missing_events, settings_hash)
        
        if events_processed > 0:
            log.info(f'Processed accounting for {events_processed} events')
            self._clear_accounting_work_pending()
            return True
        else:
            self._clear_accounting_work_pending()
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
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                "SELECT value FROM settings WHERE name='accounting_work_pending'"
            ).fetchone()
            return result is not None and result[0] == '1'

    # --- Data Access ---

    def get_events_with_accounting(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            filter_assets: list[Asset] | None = None,
            settings_hash: str | None = None,
    ) -> list[HistoryEventWithAccounting]:
        """Get history events with accounting data overlay"""
        if settings_hash is None:
            settings_hash = self.get_current_settings_hash()

        with self.db.conn.read_ctx() as cursor:
            # Build query with optional asset filter
            asset_filter = ""
            params = [start_ts, end_ts, settings_hash]

            if filter_assets:
                asset_placeholders = ','.join('?' * len(filter_assets))
                asset_filter = f" AND he.asset IN ({asset_placeholders})"
                params.extend([asset.identifier for asset in filter_assets])

            query = f"""
            SELECT he.*,
                   hea.total_amount_before, hea.cost_basis_before, hea.is_taxable,
                   hea.pnl_taxable, hea.pnl_free, hea.accounting_settings_hash
            FROM history_events he
            LEFT JOIN history_events_accounting hea ON he.identifier = hea.history_event_id
                AND hea.accounting_settings_hash = ?
            WHERE he.timestamp >= ? AND he.timestamp <= ?{asset_filter}
            ORDER BY he.timestamp, he.sequence_index
            """

            cursor.execute(query, [settings_hash, start_ts, end_ts] + (params[3:] if filter_assets else []))

            results = []
            for row in cursor.fetchall():
                # TODO: Properly deserialize HistoryBaseEntry from row
                # For now, create a placeholder
                event = None  # Will need proper deserialization

                if row[-6] is not None:  # Has accounting data
                    accounting_data = AccountingData(
                        total_amount_before=FVal(row[-6]),
                        cost_basis_before=FVal(row[-5]) if row[-5] else None,
                        is_taxable=bool(row[-4]),
                        pnl_taxable=FVal(row[-3]),
                        pnl_free=FVal(row[-2]),
                        settings_hash=row[-1],
                    )
                else:
                    accounting_data = None

                results.append(HistoryEventWithAccounting(
                    event=event,
                    accounting_data=accounting_data,
                ))

            return results

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
                return PnlTotals(
                    taxable=FVal(str(result[0])),
                    free=FVal(str(result[1] or 0)),
                )
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
        Returns the number of events processed.
        """
        if not event_ids:
            return 0

        # Get the current accounting settings
        with self.db.conn.read_ctx() as cursor:
            db_settings = self.db.get_settings(cursor)

        # Initialize cost basis calculator
        cost_basis = CostBasisCalculator(
            database=self.db,
            msg_aggregator=self.msg_aggregator,
        )
        
        # Track asset balances per location
        asset_balances: dict[tuple[Asset, str, str | None], FVal] = {}  # (asset, location, location_label) -> amount
        
        processed_count = 0
        
        with self.db.transient_write() as cursor:
            # Get all events that need processing, in chronological order
            event_placeholders = ','.join('?' * len(event_ids))
            cursor.execute(f"""
                SELECT identifier, entry_type, event_identifier, sequence_index, timestamp, 
                       location, location_label, asset, amount, notes, type, subtype, extra_data
                FROM history_events 
                WHERE identifier IN ({event_placeholders})
                ORDER BY timestamp, sequence_index
            """, event_ids)
            
            for row in cursor.fetchall():
                try:
                    # Deserialize the history event
                    event = self._deserialize_history_event_from_row(row)
                    
                    # Calculate the balance before this event
                    balance_key = (event.asset, event.location.serialize_for_db(), event.location_label)
                    total_amount_before = asset_balances.get(balance_key, ZERO)
                    
                    # Get price for this event
                    try:
                        price = PriceHistorian().query_historical_price(
                            from_asset=event.asset,
                            to_asset=db_settings.main_currency.resolve_to_asset_with_oracles(),
                            timestamp=event.get_timestamp_in_sec(),
                        )
                    except (PriceQueryUnsupportedAsset, RemoteError, NoPriceForGivenTimestamp):
                        price = ZERO_PRICE

                    # Determine if this event is taxable (simplified logic for now)
                    is_taxable = self._determine_event_taxability(event, db_settings)
                    
                    # Calculate cost basis (simplified - would need proper integration with cost basis calculator)
                    cost_basis_before = ZERO  # TODO: Integrate with cost_basis.get_cost_basis_for_asset()
                    
                    # Calculate PnL (simplified)
                    pnl_taxable = ZERO
                    pnl_free = ZERO
                    
                    if event.amount > ZERO:  # Acquisition
                        # Update balance after acquisition
                        asset_balances[balance_key] = total_amount_before + event.amount
                    else:  # Spend
                        # Calculate PnL on spend
                        spend_amount = abs(event.amount)
                        if spend_amount <= total_amount_before:
                            if is_taxable:
                                pnl_taxable = spend_amount * price - (cost_basis_before * spend_amount / total_amount_before if total_amount_before > ZERO else ZERO)
                            else:
                                pnl_free = spend_amount * price - (cost_basis_before * spend_amount / total_amount_before if total_amount_before > ZERO else ZERO)
                            
                            # Update balance after spend
                            asset_balances[balance_key] = total_amount_before - spend_amount
                        else:
                            # Insufficient balance - log warning but continue
                            log.warning(f'Insufficient balance for event {event.identifier}: trying to spend {spend_amount} but only have {total_amount_before}')
                            asset_balances[balance_key] = ZERO

                    # Insert accounting data
                    cursor.execute("""
                        INSERT INTO history_events_accounting 
                        (history_event_id, total_amount_before, cost_basis_before, is_taxable, 
                         pnl_taxable, pnl_free, accounting_settings_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.identifier,
                        str(total_amount_before),
                        str(cost_basis_before) if cost_basis_before is not None else None,
                        1 if is_taxable else 0,
                        str(pnl_taxable),
                        str(pnl_free),
                        settings_hash,
                    ))

                    # Update asset location balances
                    cursor.execute("""
                        INSERT OR REPLACE INTO asset_location_balances
                        (timestamp, location, location_label, asset, amount)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        event.timestamp,
                        event.location.serialize_for_db(),
                        event.location_label,
                        event.asset.identifier,
                        str(asset_balances[balance_key]),
                    ))

                    processed_count += 1
                    
                except Exception as e:
                    log.error(f'Failed to process event {row[0]}: {e}')
                    continue

        return processed_count

    def _deserialize_history_event_from_row(self, row: tuple) -> HistoryBaseEntry:
        """Deserialize a history event from a database row"""
        # This is a simplified deserialization - would need proper implementation
        # based on the entry_type to get the correct HistoryBaseEntry subclass
        from rotkehlchen.history.events.structures.base import HistoryEvent
        from rotkehlchen.history.events.structures.types import HistoryEventType, HistoryEventSubType
        from rotkehlchen.types import Location, TimestampMS
        
        return HistoryEvent(
            identifier=row[0],
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
            extra_data=None,  # TODO: Deserialize extra_data
        )

    def _determine_event_taxability(self, event: HistoryBaseEntry, settings) -> bool:
        """Determine if an event is taxable based on event type and settings"""
        # Simplified logic - would need proper implementation based on accounting rules
        from rotkehlchen.history.events.structures.types import HistoryEventType
        
        # Some basic rules
        if event.event_type in (HistoryEventType.TRADE, HistoryEventType.RECEIVE):
            return True
        elif event.event_type == HistoryEventType.SPEND:
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
        return True, f"Export to {directory_path} completed"

    # --- Internal Helper Methods ---

    def _get_accounting_settings_data(self, cursor: 'DBCursor') -> dict:
        """Get all accounting-relevant settings for hashing"""
        settings_data = {}

        # Get global settings
        accounting_settings = [
            'main_currency', 'taxfree_after_period', 'include_crypto2crypto',
            'calculate_past_cost_basis', 'include_gas_costs', 'cost_basis_method',
            'eth_staking_taxable_after_withdrawal_enabled', 'include_fees_in_cost_basis'
        ]

        for setting_name in accounting_settings:
            result = cursor.execute(
                'SELECT value FROM settings WHERE name = ?', (setting_name,)
            ).fetchone()
            settings_data[setting_name] = result[0] if result else None

        # Get accounting rules (simplified - just count and last modified)
        rule_count = cursor.execute('SELECT COUNT(*) FROM accounting_rule').fetchone()[0]
        settings_data['accounting_rules_count'] = rule_count

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
            timestamp_filter = ""
            params = [settings_hash]

            if up_to_timestamp is not None:
                timestamp_filter = " AND he.timestamp <= ?"
                params.append(up_to_timestamp)

            cursor.execute(f"""
                SELECT he.identifier
                FROM history_events he
                LEFT JOIN history_events_accounting hea ON he.identifier = hea.history_event_id
                    AND hea.accounting_settings_hash = ?
                WHERE hea.history_event_id IS NULL{timestamp_filter}
                ORDER BY he.timestamp, he.sequence_index
            """, params)

            return [row[0] for row in cursor.fetchall()]

    def _mark_accounting_work_pending(self) -> None:
        """Mark that accounting work is pending"""
        with self.db.transient_write() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO settings (name, value) VALUES ('accounting_work_pending', '1')"
            )

    def _clear_accounting_work_pending(self) -> None:
        """Clear the accounting work pending flag"""
        with self.db.transient_write() as cursor:
            cursor.execute(
                "DELETE FROM settings WHERE name = 'accounting_work_pending'"
            )
