from pathlib import Path
from typing import Any

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.data_import.utils import BaseExchangeImporter, detect_duplicate_event
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, TimestampMS


class DummyImporter(BaseExchangeImporter):
    def _import_csv(self, write_cursor, filepath: Path, **kwargs: Any) -> None:
        return None


def test_detect_duplicate_event_escapes_like(database) -> None:
    assert database is not None
    history_db = DBHistoryEvents(database)
    event = HistoryEvent(
        event_identifier='ABCXYZ',
        sequence_index=0,
        timestamp=TimestampMS(1700000000000),
        location=Location.BINANCE,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_ETH,
        amount=FVal('1'),
    )
    with database.user_write() as write_cursor:
        history_db.add_history_event(write_cursor, event)

    importer = DummyImporter(db=database, name='dummy')
    with database.user_write() as write_cursor:
        assert detect_duplicate_event(
            event_type=event.event_type,
            event_subtype=event.event_subtype,
            amount=event.amount,
            asset=event.asset,
            timestamp_ms=event.timestamp,
            location=event.location,
            event_prefix='ABC',
            importer=importer,
            write_cursor=write_cursor,
        ) is True
        assert detect_duplicate_event(
            event_type=event.event_type,
            event_subtype=event.event_subtype,
            amount=event.amount,
            asset=event.asset,
            timestamp_ms=event.timestamp,
            location=event.location,
            event_prefix='ABC%',
            importer=importer,
            write_cursor=write_cursor,
        ) is False
