import hashlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING, asset_from_common_identifier
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_timestamp
from rotkehlchen.types import AssetAmount, Fee, Location, TimestampMS

ITEMS_PER_DB_WRITE = 400
MAX_ERROR_PERCENT = 0.2  # max percent of messages to total entries
MIN_ENTRIES = 50  # mininmum number of entries before checking MAX_ERROR_PERCENT

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseExchangeImporter(ABC):
    def __init__(self, db: DBHandler, name: str) -> None:
        self.db = db
        self.history_db = DBHistoryEvents(self.db)
        self._trades: list[Trade] = []
        self._margin_trades: list[MarginPosition] = []
        self._asset_movements: list[AssetMovement] = []
        self._history_events: list[HistoryBaseEntry] = []
        self.name = name
        self.reset()

    def reset(self) -> None:
        """[Re]Initialize variables used by the CSV imports"""
        self.total_entries: int = 0
        self.imported_entries: int = 0
        self.import_msgs: list[dict] = []
        self.max_msgs: bool = False

    def import_csv(self, filepath: Path, **kwargs: Any) -> tuple[bool, str]:
        self.reset()

        try:
            with self.db.user_write() as write_cursor:
                self._import_csv(write_cursor, filepath=filepath, **kwargs)
                self.flush_all(write_cursor)

            # Group by msg. Assume warning will be the same for all identical msgs.
            grouped_msgs = {}
            for import_msg in self.import_msgs:
                msg = import_msg['msg']
                row = import_msg['row']
                if msg not in grouped_msgs:
                    grouped_msgs[msg] = {
                        'msg': msg,
                        'rows': [row],
                        **({'is_error': True} if 'is_error' in import_msg else {}),
                    }
                else:
                    grouped_msgs[msg]['rows'].append(row)

            log.debug(f'Imported {self.imported_entries}/{self.total_entries} entries.')
            self.db.msg_aggregator.add_message(WSMessageType.CSV_IMPORT_RESULT, {
                'source_name': self.name,
                'total_entries': self.total_entries,
                'imported_entries': self.imported_entries,
                'messages': list(grouped_msgs.values()),
            })

        except InputError as e:
            return False, str(e)
        else:
            return True, ''

    @abstractmethod
    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """The method that processes csv. Should be implemented by subclasses.
        May raise:
        - InputError if one of the rows is malformed
        """

    def add_trade(self, write_cursor: DBCursor, trade: Trade) -> None:
        self._trades.append(trade)
        self.maybe_flush_all(write_cursor)

    def add_margin_trade(self, write_cursor: DBCursor, margin_trade: MarginPosition) -> None:
        self._margin_trades.append(margin_trade)
        self.maybe_flush_all(write_cursor)

    def add_asset_movement(self, write_cursor: DBCursor, asset_movement: AssetMovement) -> None:
        self._asset_movements.append(asset_movement)
        self.maybe_flush_all(write_cursor)

    def add_history_events(self, write_cursor: DBCursor, history_events: list[HistoryBaseEntry]) -> None:  # noqa: E501
        self._history_events.extend(history_events)
        self.maybe_flush_all(write_cursor)

    def maybe_flush_all(self, cursor: DBCursor) -> None:
        if len(self._trades) + len(self._margin_trades) + len(self._asset_movements) + len(self._history_events) >= ITEMS_PER_DB_WRITE:  # noqa: E501
            self.flush_all(cursor)

    def flush_all(self, write_cursor: DBCursor) -> None:
        self.db.add_trades(write_cursor, trades=self._trades)
        self.db.add_margin_positions(write_cursor, margin_positions=self._margin_trades)
        self.db.add_asset_movements(write_cursor, asset_movements=self._asset_movements)
        self.history_db.add_history_events(write_cursor, history=self._history_events)
        self._trades = []
        self._margin_trades = []
        self._asset_movements = []
        self._history_events = []

    def append_msg(self, row_index: int, msg: str, is_error: bool) -> None:
        """Append message to queue to be sent to frontend.
        Stop collecting messages if more than MAX_ERROR_PERCENT have messages.
        Note that total_entries only contains the number of rows processed so far.
        So if the percentage of messages is too high in the first MIN_ENTRIES rows,
        message collecting will stop even if the rest of the file has few messages.

        Args:
            - row_index (int): CSV row index where message originated
            - msg (str): Message text
            - error (bool): Indicates if the row failed to import (True)
                or was skipped on purpose (False).
        """
        if self.max_msgs:
            return

        if (
            self.total_entries >= MIN_ENTRIES and
            len(self.import_msgs) >= self.total_entries * MAX_ERROR_PERCENT
        ):
            self.max_msgs = True

        self.import_msgs.append({
            'row': row_index,
            'msg': msg,
            **({'is_error': True} if is_error else {}),
        })

    def send_message(self, row_index: int, csv_row: dict, msg: str, is_error: bool) -> None:
        """Send message to log and frontend
        Args:
            - row_index (int): CSV row index where message originated
            - csv_row (dict): CSV row data that caused the message
            - msg (str): Message text
            - is_error (bool): Indicates if the row failed to import (True)
                or was skipped on purpose (False).
        """
        log.debug(f'Failed to import row {row_index} {csv_row} of {self.name} CSV file. {msg}.')
        self.append_msg(row_index=row_index, msg=msg, is_error=is_error)


class UnsupportedCSVEntry(Exception):
    """Raised for csv entries we fail to import."""


class SkippedCSVEntry(Exception):
    """Raised for csv entries we skip on purpose."""


def process_rotki_generic_import_csv_fields(
        csv_row: dict[str, Any],
        currency_colname: str,
) -> tuple[AssetWithOracles, Fee | None, Asset | None, Location, TimestampMS]:
    """
    Process the imported csv for generic rotki trades and events
    """
    location = Location.deserialize(csv_row['Location'])
    timestamp = TimestampMS(deserialize_timestamp(csv_row['Timestamp']))
    fee = Fee(deserialize_asset_amount(csv_row['Fee'])) if csv_row['Fee'] else None
    asset_mapping = LOCATION_TO_ASSET_MAPPING.get(location, asset_from_common_identifier)
    asset = asset_mapping(csv_row[currency_colname])
    fee_currency = (
        asset_mapping(csv_row['Fee Currency'])
        if csv_row['Fee Currency'] and fee is not None else None
    )
    return asset, fee, fee_currency, location, timestamp


def hash_csv_row(csv_row: Mapping[str, Any]) -> str:
    """Convert the row to string and encode it to a hex string to get a unique hash"""
    row_str = str(csv_row).encode()
    return hashlib.sha256(row_str).hexdigest()


def detect_duplicate_event(
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        amount: AssetAmount,
        asset: Asset,
        timestamp_ms: TimestampMS,
        location: Location,
        event_prefix: str,
        importer: BaseExchangeImporter,
        write_cursor: DBCursor,
) -> bool:
    """Detect if an event with these attributes is already in the database.
    Returns True if the event is found, and False if not found.
    """
    importer.flush_all(write_cursor)  # flush so that the DB check later can work and not miss unwritten events  # noqa: E501
    with importer.db.conn.read_ctx() as read_cursor:
        read_cursor.execute(
            f"SELECT COUNT(*) FROM history_events WHERE "
            f"event_identifier LIKE '{event_prefix}%' "
            "AND asset=? AND amount=? AND timestamp=? AND location=? "
            "AND type=? AND subtype=?",
            (asset.identifier, str(amount), timestamp_ms, location.serialize_for_db(),
             event_type.serialize(), event_subtype.serialize()),
        )
        return read_cursor.fetchone()[0] != 0
