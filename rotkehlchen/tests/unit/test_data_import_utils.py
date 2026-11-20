from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.data_import.importers.rotki_events import RotkiGenericEventsImporter
from rotkehlchen.data_import.importers.rotki_trades import RotkiGenericTradesImporter
from rotkehlchen.data_import.utils import BaseExchangeImporter, detect_duplicate_event
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_swap
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_KRAKEN,
)
from rotkehlchen.types import AssetAmount, TimestampMS

if TYPE_CHECKING:
    from pathlib import Path


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
        location=LOCATION_BINANCE,
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


def test_rotki_generic_trades_unknown_asset(database, tmp_path) -> None:
    """Regression for https://github.com/rotki/rotki/issues/12233.

    An asset on a row that can't be mapped to a known asset must not crash the
    import task — it should be surfaced as a per-row error and the rest of the
    file should import fine.
    """
    filepath = tmp_path / 'rotki_generic_trades.csv'
    filepath.write_text(
        'Location,Spend Currency,Receive Currency,Receive Amount,Spend Amount,'
        'Fee,Fee Currency,Description,Timestamp\n'
        'bittrex,ZZZFAKE,BTC,0.01,100,,,Trade ZZZFAKE for BTC,1545575255000\n'
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
    assert 'ZZZFAKE' in error_msgs[0]['msg']
    assert 'Unknown asset' in error_msgs[0]['msg']


def test_rotki_generic_events_unknown_asset(database, tmp_path) -> None:
    """Same regression for the rotki generic events importer."""
    filepath = tmp_path / 'rotki_generic_events.csv'
    filepath.write_text(
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp\n'
        'Deposit,bittrex,ZZZFAKE,100,,,Deposit ZZZFAKE,1545575255000\n'
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
    assert 'ZZZFAKE' in error_msgs[0]['msg']
    assert 'Unknown asset' in error_msgs[0]['msg']


def _count_history_events(database) -> int:
    with database.conn.read_ctx() as cursor:
        return cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0]


def test_rotki_generic_events_reimport_skips_duplicates(database, tmp_path) -> None:
    """Regression for https://github.com/rotki/rotki/issues/13691.

    Re-importing a file, or a reordered superset of it, must not duplicate events while
    identical rows in the same file (e.g. identical fills in the same second) are all kept.
    """
    header = 'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp\n'
    (filepath := tmp_path / 'events.csv').write_text(
        header +
        (row_a := 'Deposit,kraken,ETH,1.5,0.01,ETH,Deposit A,1659171600000\n') +
        (row_b := 'Staking,kraken,ETH,0.1,,,Reward,1659171700000\n') +
        row_b,  # legitimately identical second reward
    )
    importer = RotkiGenericEventsImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert _count_history_events(database) == 4  # deposit + fee + 2 rewards
    assert importer.imported_entries == 3

    assert importer.import_csv(filepath=filepath) == (True, '')
    assert _count_history_events(database) == 4
    assert (importer.total_entries, importer.imported_entries) == (3, 0)
    assert importer.import_msgs == [
        {'row': 1, 'msg': 'Skipped already imported deposit/deposit asset of 1.5 ETH at 2022/07/30 09:00:00'},  # noqa: E501
        {'row': 2, 'msg': 'Skipped already imported staking/reward of 0.1 ETH at 2022/07/30 09:01:40'},  # noqa: E501
        {'row': 3, 'msg': 'Skipped already imported staking/reward of 0.1 ETH at 2022/07/30 09:01:40'},  # noqa: E501
    ]

    (superset_path := tmp_path / 'renamed.csv').write_text(  # reordered, edited description
        header + row_b + 'Withdrawal,kraken,ETH,0.3,,,New C,1659171800000\n' + row_b +
        row_a.replace('Deposit A', 'Changed description'),
    )
    assert importer.import_csv(filepath=superset_path) == (True, '')
    assert _count_history_events(database) == 5
    assert (importer.total_entries, importer.imported_entries) == (4, 1)

    (more_path := tmp_path / 'more.csv').write_text(header + row_b * 3)  # a third reward
    assert importer.import_csv(filepath=more_path) == (True, '')
    assert _count_history_events(database) == 6
    assert importer.imported_entries == 1


def test_rotki_generic_events_source_id(database, tmp_path) -> None:
    """The optional Source ID column identifies rows with otherwise identical values"""
    (filepath := tmp_path / 'events.csv').write_text(
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp,Source ID\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-1\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-2\n',
    )
    importer = RotkiGenericEventsImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert _count_history_events(database) == 2

    (batch_path := tmp_path / 'batch.csv').write_text(  # incremental batch with an identical row
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp,Source ID\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-2\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-3\n',
    )
    assert importer.import_csv(filepath=batch_path) == (True, '')
    assert _count_history_events(database) == 3
    assert importer.imported_entries == 1


def test_rotki_generic_events_legacy_identifiers(database, tmp_path) -> None:
    """Events imported by older versions have random identifiers and must still be matched,
    migrated, and each existing event must match at most one row across all later imports."""
    history_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        history_db.add_history_event(write_cursor, HistoryEvent(
            group_identifier='RE_' + 'a' * 32,
            sequence_index=0,
            timestamp=TimestampMS(1659171600000),
            location=LOCATION_KRAKEN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal('1'),
        ))

    (filepath := tmp_path / 'events.csv').write_text(
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp,Source ID\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-1\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-2\n',
    )
    importer = RotkiGenericEventsImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 1
    assert _count_history_events(database) == 2
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE length(group_identifier)=?',
            (len('RE_' + 'a' * 32),),
        ).fetchone()[0] == 0

    filepath.write_text(
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp,Source ID\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-2\n'
        'Deposit,kraken,ETH,1,,,,1659171600000,id-3\n',
    )
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert _count_history_events(database) == 3
    assert importer.imported_entries == 1


def test_rotki_generic_events_legacy_fee_matching(database, tmp_path) -> None:
    """A fee-less row must not claim a legacy event that has a companion fee row."""
    history_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        history_db.add_history_events(write_cursor, [HistoryEvent(
            group_identifier=(legacy_identifier := 'RE_' + 'a' * 32),
            sequence_index=4,
            timestamp=TimestampMS(1659171600000),
            location=LOCATION_KRAKEN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal('1'),
        ), HistoryEvent(
            group_identifier=legacy_identifier,
            sequence_index=5,
            timestamp=TimestampMS(1659171600000),
            location=LOCATION_KRAKEN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.01'),
        )])

    (filepath := tmp_path / 'events.csv').write_text(
        'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp\n'
        'Deposit,kraken,ETH,1,,,,1659171600000\n'
        'Deposit,kraken,ETH,1,0.01,ETH,,1659171600000\n',
    )
    importer = RotkiGenericEventsImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 1
    assert _count_history_events(database) == 3

    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 0
    assert _count_history_events(database) == 3


def test_rotki_generic_events_zero_and_blank_fee_match(database, tmp_path) -> None:
    """Zero and blank fees create the same identity because neither creates a fee event."""
    header = 'Type,Location,Currency,Amount,Fee,Fee Currency,Description,Timestamp\n'
    (filepath := tmp_path / 'events.csv').write_text(
        header + 'Deposit,kraken,ETH,1,,,,1659171600000\n',
    )
    importer = RotkiGenericEventsImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')

    filepath.write_text(header + 'Deposit,kraken,ETH,1,0,ETH,,1659171600000\n')
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 0
    assert _count_history_events(database) == 1


def test_rotki_generic_trades_identical_fills(database, tmp_path) -> None:
    """Identical trades in the same file are all kept, and the first one keeps the
    identifier used by older versions so that re-imports still match it."""
    (filepath := tmp_path / 'trades.csv').write_text(
        'Location,Spend Currency,Receive Currency,Receive Amount,Spend Amount,'
        'Fee,Fee Currency,Description,Timestamp\n' +
        'kraken,LTC,BTC,4.3241,392.8870,,,Fill,1659171600000\n' * 2,
    )
    importer = RotkiGenericTradesImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert _count_history_events(database) == 4  # spend + receive per trade
    assert importer.imported_entries == 2

    assert importer.import_csv(filepath=filepath) == (True, '')
    assert _count_history_events(database) == 4
    assert (importer.total_entries, importer.imported_entries) == (2, 0)
    assert [msg['row'] for msg in importer.import_msgs] == [1, 2]
    with database.conn.read_ctx() as cursor:
        assert create_group_identifier_from_swap(
            location=LOCATION_KRAKEN,
            timestamp=TimestampMS(1659171600000),
            spend=AssetAmount(asset=Asset('LTC'), amount=FVal('392.8870')),
            receive=AssetAmount(asset=A_BTC, amount=FVal('4.3241')),
        ) in {row[0] for row in cursor.execute('SELECT group_identifier FROM history_events')}


def test_rotki_generic_trades_identical_fill_superset(database, tmp_path) -> None:
    """Each existing trade can satisfy only one occurrence in an overlapping import."""
    header = (
        'Location,Spend Currency,Receive Currency,Receive Amount,Spend Amount,'
        'Fee,Fee Currency,Description,Timestamp\n'
    )
    row = 'kraken,LTC,BTC,4.3241,392.8870,,,Fill,1659171600000\n'
    (filepath := tmp_path / 'trades.csv').write_text(header + row * 2)
    importer = RotkiGenericTradesImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')

    filepath.write_text(header + row * 3)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 1
    assert _count_history_events(database) == 6


def test_rotki_generic_trades_identical_fills_across_flush(database, tmp_path) -> None:
    """Flushing the first 200 trades must not make their base group reusable."""
    (filepath := tmp_path / 'trades.csv').write_text(
        'Location,Spend Currency,Receive Currency,Receive Amount,Spend Amount,'
        'Fee,Fee Currency,Description,Timestamp\n' +
        'kraken,LTC,BTC,4.3241,392.8870,,,Fill,1659171600000\n' * 201,
    )
    importer = RotkiGenericTradesImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 201
    assert _count_history_events(database) == 402


def test_rotki_generic_trades_reordered_fee_variants(database, tmp_path) -> None:
    """A new fee variant in a reordered superset must not displace the existing trade."""
    header = (
        'Location,Spend Currency,Receive Currency,Receive Amount,Spend Amount,'
        'Fee,Fee Currency,Description,Timestamp\n'
    )
    row_a = 'kraken,LTC,BTC,4.3241,392.8870,1,USD,Fill A,1659171600000\n'
    row_b = 'kraken,LTC,BTC,4.3241,392.8870,2,USD,Fill B,1659171600000\n'
    (filepath := tmp_path / 'trades.csv').write_text(header + row_a)
    importer = RotkiGenericTradesImporter(db=database)
    assert importer.import_csv(filepath=filepath) == (True, '')

    filepath.write_text(header + row_b + row_a)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 1
    assert _count_history_events(database) == 6

    filepath.write_text(header + row_a + row_b)
    assert importer.import_csv(filepath=filepath) == (True, '')
    assert importer.imported_entries == 0
    assert _count_history_events(database) == 6
