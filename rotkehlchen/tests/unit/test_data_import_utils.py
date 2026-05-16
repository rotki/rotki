from pathlib import Path
from typing import Any

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.data_import.importers.rotki_events import RotkiGenericEventsImporter
from rotkehlchen.data_import.importers.rotki_trades import RotkiGenericTradesImporter
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
        group_identifier='ABCXYZ',
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


def test_rotki_generic_trades_unsupported_asset(database, tmp_path) -> None:
    """Regression for https://github.com/rotki/rotki/issues/12233.

    An UnsupportedAsset on a row (GLD on Bittrex is blacklisted in
    location_unsupported_assets) must not crash the import task — it should be
    surfaced as a per-row error and the rest of the file should import fine.
    """
    filepath = tmp_path / 'rotki_generic_trades.csv'
    filepath.write_text(
        'Location,Spend Currency,Receive Currency,Receive Amount,Spend Amount,'
        'Fee,Fee Currency,Description,Timestamp\n'
        'bittrex,GLD,BTC,0.01,100,,,Trade GLD for BTC,1545575255000\n'
        'kraken,LTC,BTC,4.3241,392.8870,,,Trade LTC for BTC,1659171600000\n',
    )

    importer = RotkiGenericTradesImporter(db=database)
    success, msg = importer.import_csv(filepath=filepath)
    assert success is True
    assert msg == ''
    assert importer.total_entries == 2
    assert importer.imported_entries == 1
    error_msgs = [m for m in importer.import_msgs if m.get('is_error')]
    assert len(error_msgs) == 1
    assert 'GLD' in error_msgs[0]['msg']
    assert 'not supported' in error_msgs[0]['msg']
    assert 'bittrex' in error_msgs[0]['msg']


def test_rotki_generic_events_unsupported_asset(database, tmp_path) -> None:
    """Same regression for the rotki generic events importer."""
    filepath = tmp_path / 'rotki_generic_events.csv'
    filepath.write_text(
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp\n'
        'Deposit,bittrex,GLD,100,,,Deposit GLD,1545575255000\n'
        'Deposit,kraken,LTC,5,,,Deposit LTC,1659171600000\n',
    )

    importer = RotkiGenericEventsImporter(db=database)
    success, msg = importer.import_csv(filepath=filepath)
    assert success is True
    assert msg == ''
    assert importer.total_entries == 2
    assert importer.imported_entries == 1
    error_msgs = [m for m in importer.import_msgs if m.get('is_error')]
    assert len(error_msgs) == 1
    assert 'GLD' in error_msgs[0]['msg']
    assert 'not supported' in error_msgs[0]['msg']
    assert 'bittrex' in error_msgs[0]['msg']
