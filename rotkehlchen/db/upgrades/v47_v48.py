import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import AssetAmount, Location, Price
from rotkehlchen.utils.misc import ts_sec_to_ms
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def upgrade_trade_to_swap_events(
        row: tuple[Any, ...],
        kraken_ids_to_labels: dict[str, str],
        kraken_adjustments_data: dict[str, tuple[str, str, str]],
        kraken_ids_to_delete: set[str],
) -> list[SwapEvent]:
    """Convert a raw Trade db row into a list of SwapEvents.

    Kraken trades get special treatment using data from history events:
    - location_label is set from `kraken_ids_to_labels` and `kraken_adjustments_data`
    - adjustment trade amounts are set from `kraken_adjustments_data` since adjustment trade rates
      were calculated incorrectly previously.
    - adjustment events associated with a trade are added to `kraken_ids_to_delete`

    May raise:
    - DeserializationError
    - ValueError
    """
    spend, receive = get_swap_spend_receive(
        raw_trade_type='buy' if row[4] in {'A', 'C'} else 'sell',  # A,C = buy, settlement buy; B,D = sell, settlement sell  # noqa: E501
        base_asset=Asset(row[2]),
        quote_asset=Asset(row[3]),
        amount=FVal(row[5]),
        rate=Price(FVal(row[6])),
    )

    # Special Kraken logic
    link, location_label = row[9], None
    if (
        (location := Location.deserialize_from_db(row[1])) == Location.KRAKEN and
        link is not None and
        len(link) > 10  # Coincidentally both normal and adjustment trade links must be at least 10 chars to be processed here.  # noqa: E501
    ):
        if link[:10] == 'adjustment':  # Adjustment trade links are 'adjustment' + a1.event_identifier + a2.event_identifier  # noqa: E501
            # Find which adjustment history event ids are present in this trade link.
            adjustments_for_this_trade = set()
            for adjustment_trade_id, adjustment_data in kraken_adjustments_data.items():
                if adjustment_trade_id not in link:
                    continue

                adjustments_for_this_trade.add(adjustment_trade_id)
                # Set location_label and amounts from the adjustment event data
                location_label, amount, subtype = adjustment_data
                if subtype == 'spend':
                    spend = AssetAmount(asset=spend.asset, amount=FVal(amount))
                elif subtype == 'receive':
                    receive = AssetAmount(asset=receive.asset, amount=FVal(amount))

                if len(adjustments_for_this_trade) == 2:
                    break  # Found both adjustments associated with this trade

            kraken_ids_to_delete.update(adjustments_for_this_trade)

        else:  # Normal kraken trade. Link is trade ID + timestamp.
            # Remove timestamp from link to get trade ID for label lookup.
            location_label = kraken_ids_to_labels.get(link[:-10])

    return create_swap_events(
        timestamp=ts_sec_to_ms(row[0]),
        location=location,
        spend=spend,
        receive=receive,
        fee=AssetAmount(
            asset=Asset(row[8]),
            amount=FVal(row[7]),
        ) if row[8] is not None and row[7] is not None else None,
        location_label=location_label,
        unique_id=link,
        spend_notes=row[10],
    )


@enter_exit_debug_log(name='UserDB v47->v48 upgrade')
def upgrade_v47_to_v48(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v47 to v48. This was in v1.39 release."""

    @progress_step(description='Converting trades to history events')
    def _convert_trades_to_swap_events(write_cursor: 'DBCursor') -> None:
        new_events: list[SwapEvent] = []
        # Kraken events appear both as history events and trades. We'll convert to SwapEvents
        # from the trades, but preserve the location_labels from the history events.
        write_cursor.execute(
            'SELECT DISTINCT event_identifier, location_label '
            'FROM history_events WHERE location=? AND type=?',
            (Location.KRAKEN.serialize_for_db(), HistoryEventType.TRADE.serialize()),
        )
        kraken_ids_to_labels = dict(write_cursor)  # Map event_identifiers (trade IDs) to location_labels.  # noqa: E501
        kraken_ids_to_delete = set(kraken_ids_to_labels)
        # Adjustments need special treatment, so save them in a different mapping with more info.
        write_cursor.execute(
            'SELECT DISTINCT event_identifier, location_label, amount, subtype '
            'FROM history_events WHERE location=? AND type=?',
            (Location.KRAKEN.serialize_for_db(), HistoryEventType.ADJUSTMENT.serialize()),
        )
        kraken_adjustments_data = {row[0]: (row[1], row[2], row[3]) for row in write_cursor}

        write_cursor.execute(
            'SELECT timestamp, location, base_asset, quote_asset, type, '
            'amount, rate, fee, fee_currency, link, notes FROM trades',
        )
        for row in write_cursor:
            try:
                new_events.extend(upgrade_trade_to_swap_events(
                    row=row,
                    kraken_ids_to_labels=kraken_ids_to_labels,
                    kraken_adjustments_data=kraken_adjustments_data,
                    kraken_ids_to_delete=kraken_ids_to_delete,
                ))
            except (DeserializationError, ValueError) as e:
                log.error(f'Failed to deserialize row {row} due to {e}. Skipping.')

        # Remove old Kraken history events that are no longer needed.
        placeholders = ','.join(['?'] * len(kraken_ids_to_delete))
        write_cursor.execute(
            f'DELETE FROM history_events WHERE location=? AND event_identifier IN ({placeholders})',  # noqa: E501
            (Location.KRAKEN.serialize_for_db(),) + tuple(kraken_ids_to_delete),
        )
        # Write the new swap events to the db and drop the old trade tables.
        write_cursor.executemany(
            'INSERT OR IGNORE INTO history_events(entry_type, event_identifier, '
            'sequence_index, timestamp, location, location_label, asset, amount, '
            'notes, type, subtype, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (event.serialize_for_db()[0][2] for event in new_events),
        )
        # TODO: Uncomment these when ready to drop the tables
        # write_cursor.execute('DROP TABLE trades')  # noqa: ERA001
        # write_cursor.execute('DROP TABLE trade_type')  # noqa: ERA001

    @progress_step(description='Replacing specific history note locations with HISTORY')
    def _replace_history_note_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            """
            UPDATE user_notes
            SET location = 'HISTORY'
            WHERE location IN (
                'HISTORY_TRADES',
                'HISTORY_TRANSACTIONS',
                'HISTORY_DEPOSITS_WITHDRAWALS'
            )
            """,
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
