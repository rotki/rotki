from typing import TYPE_CHECKING, Any

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.data_import.importers.bittrex import BittrexImporter
from rotkehlchen.data_import.importers.kucoin import KucoinImporter
from rotkehlchen.data_import.importers.rotki_events import RotkiGenericEventsImporter
from rotkehlchen.data_import.importers.rotki_trades import RotkiGenericTradesImporter
from rotkehlchen.data_import.utils import BaseExchangeImporter, detect_duplicate_event
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, TimestampMS

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


def test_kucoin_unknown_asset(database, tmp_path) -> None:
    """Same regression for the kucoin importer."""
    filepath = tmp_path / 'kucoin_order_history.csv'
    filepath.write_text(
        'tradeCreatedAt,symbol,side,price,size,funds,fee,feeCurrency\n'
        '2022-04-28 12:36:00,ZZZFAKE-USDT,sell,0.1025,36.4479,3.7359,0.0037,USDT\n'
        '2022-04-28 15:46:07,XRP-USDT,buy,0.64924,432.5918,280.8559,0.2808,USDT\n',
    )

    importer = KucoinImporter(db=database)
    success, msg = importer.import_csv(filepath=filepath)
    assert success is True
    assert msg == ''
    assert importer.total_entries == 2
    assert importer.imported_entries == 1
    error_msgs = [m for m in importer.import_msgs if m.get('is_error')]
    assert len(error_msgs) == 1
    assert 'ZZZFAKE' in error_msgs[0]['msg']
    assert 'Unknown asset' in error_msgs[0]['msg']


def test_bittrex_unknown_asset(database, tmp_path) -> None:
    """Same regression for the bittrex importer."""
    filepath = tmp_path / 'bittrex_tx_history.csv'
    filepath.write_text(
        'Date,Currency,Type,Address,Memo/Tag,TxId,Amount\n'
        '2023-03-07 07:51:43.043,ZZZFAKE,DEPOSIT,"","","0x01",+100\n'
        '2023-03-08 07:51:43.043,ETH,DEPOSIT,"","","0x02",+0.5\n',
    )

    importer = BittrexImporter(db=database)
    success, msg = importer.import_csv(filepath=filepath)
    assert success is True
    assert msg == ''
    assert importer.total_entries == 2
    assert importer.imported_entries == 1
    error_msgs = [m for m in importer.import_msgs if m.get('is_error')]
    assert len(error_msgs) == 1
    assert 'ZZZFAKE' in error_msgs[0]['msg']
    assert 'Unknown asset' in error_msgs[0]['msg']
