from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, List, Tuple

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade


ITEMS_PER_DB_WRITE = 400


class BaseExchangeImporter(metaclass=ABCMeta):
    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)
        self.history_db = DBHistoryEvents(self.db)
        self._trades: List[Trade] = []
        self._asset_movements: List[AssetMovement] = []
        self._ledger_actions: List[LedgerAction] = []
        self._history_events: List[HistoryBaseEntry] = []

    def import_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        try:
            with self.db.user_write() as cursor:
                self._import_csv(cursor, filepath=filepath, **kwargs)
                self._flush_all(cursor)
            return True, ''
        except InputError as e:
            return False, str(e)

    @abstractmethod
    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """The method that processes csv. Should be implemented by subclasses.
        May raise:
        - InputError if one of the rows is malformed
        """
        ...

    def add_trade(self, cursor: DBCursor, trade: Trade) -> None:
        self._trades.append(trade)
        self.maybe_flush_all(cursor)

    def add_asset_movement(self, cursor: DBCursor, asset_movement: AssetMovement) -> None:
        self._asset_movements.append(asset_movement)
        self.maybe_flush_all(cursor)

    def add_ledger_action(self, cursor: DBCursor, ledger_action: LedgerAction) -> None:
        self._ledger_actions.append(ledger_action)
        self.maybe_flush_all(cursor)

    def add_history_events(self, cursor: DBCursor, history_events: List[HistoryBaseEntry]) -> None:
        self._history_events.extend(history_events)
        self.maybe_flush_all(cursor)

    def maybe_flush_all(self, cursor: DBCursor) -> None:
        if len(self._trades) + len(self._asset_movements) + len(self._ledger_actions) + len(self._history_events) >= ITEMS_PER_DB_WRITE:  # noqa: E501
            self._flush_all(cursor)

    def _flush_all(self, cursor: DBCursor) -> None:
        self.db.add_trades(cursor, trades=self._trades)
        self.db.add_asset_movements(cursor, asset_movements=self._asset_movements)
        self.db_ledger.add_ledger_actions(cursor, actions=self._ledger_actions)
        self.history_db.add_history_events(cursor, history=self._history_events)
        self._trades = []
        self._asset_movements = []
        self._ledger_actions = []
        self._history_events = []


class UnsupportedCSVEntry(Exception):
    """Thrown for external exchange exported entries we can't import"""
