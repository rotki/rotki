from pathlib import Path

from rotkehlchen.assets.asset import Asset
from rotkehlchen.data_import.importers.coinledger import CoinledgerImporter
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_date
from rotkehlchen.types import Location, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms


def _coinledger_ts(date: str) -> TimestampMS:
    return ts_sec_to_ms(deserialize_timestamp_from_date(
        date=date,
        formatstr='%Y-%m-%dT%H:%M:%S.%f',
        location='CoinLedger',
    ))


def test_coinledger_importer(database) -> None:
    importer = CoinledgerImporter(db=database)
    filepath = Path(__file__).resolve().parent.parent / 'data' / 'coinledger_export.csv'
    success, msg = importer.import_csv(filepath=filepath)

    assert success is True
    assert msg == ''
    assert importer.total_entries == 27
    assert importer.imported_entries == 27
    assert importer.import_msgs == []

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[('timestamp', True)]),
        )

    assert len(events) == 27
    assert any(
        isinstance(event, AssetMovement) and
        event.timestamp == _coinledger_ts('2025-03-02T16:24:08.000') and
        event.location == Location.BINANCE and
        event.event_subtype == HistoryEventSubType.RECEIVE and
        event.asset == Asset('DOGE') and
        event.amount == FVal('111.5') and
        event.extra_data == {
            'transaction_id': '11165cb38fa8b31eb910d03d4c2afb8ebb0abc0a967485ee7b07d026722714f6',
        } and
        event.location_label == 'Binance' and
        event.notes == 'Deposit (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, AssetMovement) and
        event.timestamp == _coinledger_ts('2025-08-12T05:33:18.000') and
        event.location == Location.BINANCE and
        event.event_subtype == HistoryEventSubType.SPEND and
        event.asset == Asset('DOGE') and
        event.amount == FVal('55') and
        event.extra_data == {
            'transaction_id': 'b1923e958f1110a8ef9fbd8b8f1592211ed7bf2256c07501a76168830a651bce',
        } and
        event.location_label == 'Binance' and
        event.notes == 'Withdrawal (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-08-06T07:16:26.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.NONE and
        event.asset == Asset('EUR') and
        event.amount == FVal('15.6') and
        event.extra_data == {'transaction_id': 'b7f960bd8e194d3991ab50111013ce58'} and
        event.location_label == 'Binance' and
        event.notes == 'Buy (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-03-06T00:00:00.000') and
        event.location == Location.EXTERNAL and
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.FEE and
        event.asset.symbol_or_name() == 'TRX' and
        event.amount == FVal('0.14195') and
        event.location_label == 'Pionex' and
        event.notes == 'Trade (Platform Fee) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-09-22T07:58:00.000') and
        event.location == Location.EXTERNAL and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.NONE and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('111') and
        event.location_label == 'Pionex' and
        event.notes == 'Margin Gain (Margin Gain) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T10:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.FEE and
        event.asset.symbol_or_name() == 'ETH' and
        event.amount == FVal('0.002') and
        event.location_label == 'Binance' and
        event.notes == 'Network Fee (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T11:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.INTEREST and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('1.5') and
        event.location_label == 'Binance' and
        event.notes == 'Interest (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T12:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.REWARD and
        event.asset.symbol_or_name() == 'BTC' and
        event.amount == FVal('0.01') and
        event.location_label == 'Binance' and
        event.notes == 'Mining (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T13:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.STAKING and
        event.event_subtype == HistoryEventSubType.REWARD and
        event.asset.symbol_or_name() == 'ETH' and
        event.amount == FVal('0.2') and
        event.location_label == 'Binance' and
        event.notes == 'Staking (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T14:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.AIRDROP and
        event.asset.symbol_or_name() == 'DOGE' and
        event.amount == FVal('5') and
        event.location_label == 'Binance' and
        event.notes == 'Airdrop (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T15:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.DONATE and
        event.asset.symbol_or_name() == 'BTC' and
        event.amount == FVal('0.001') and
        event.location_label == 'Binance' and
        event.notes == 'Gift Received (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T16:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.DONATE and
        event.asset.symbol_or_name() == 'BTC' and
        event.amount == FVal('0.0005') and
        event.location_label == 'Binance' and
        event.notes == 'Gift Sent (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T17:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.INTEREST and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('0.5') and
        event.location_label == 'Binance' and
        event.notes == 'Interest Payment (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T18:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.LOSS and
        event.event_subtype == HistoryEventSubType.NONE and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('12') and
        event.location_label == 'Binance' and
        event.notes == 'Investment Loss (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T19:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.LOSS and
        event.event_subtype == HistoryEventSubType.HACK and
        event.asset.symbol_or_name() == 'ETH' and
        event.amount == FVal('0.03') and
        event.location_label == 'Binance' and
        event.notes == 'Theft Loss (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T20:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.PAYMENT and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('4') and
        event.location_label == 'Binance' and
        event.notes == 'Merchant Payment (Debit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T21:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.NONE and
        event.asset.symbol_or_name() == 'BCH' and
        event.amount == FVal('0.7') and
        event.location_label == 'Binance' and
        event.notes == 'Hard Fork (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T22:00:00.000') and
        event.location == Location.KRAKEN and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.INTEREST and
        event.asset.symbol_or_name() == 'EUR' and
        event.amount == FVal('2.5') and
        event.location_label == 'Kraken' and
        event.notes == 'Interest (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-01T23:00:00.000') and
        event.location == Location.COINBASE and
        event.event_type == HistoryEventType.STAKING and
        event.event_subtype == HistoryEventSubType.REWARD and
        event.asset.symbol_or_name() == 'ETH' and
        event.amount == FVal('0.5') and
        event.location_label == 'Coinbase' and
        event.notes == 'Staking (Credit) from CoinLedger'
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-02T00:00:00.000') and
        event.location == Location.BINANCE and
        event.event_type == HistoryEventType.LOSS and
        event.event_subtype == HistoryEventSubType.NONE and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('5.8') and
        event.location_label == 'Binance' and
        event.notes == 'Margin Gain (Margin Gain) from CoinLedger'
        for event in events
    )


def test_coinledger_importer_rejects_contradictory_signs(database, tmp_path) -> None:
    importer = CoinledgerImporter(db=database)
    filepath = tmp_path / 'coinledger_contradictory_signs.csv'
    filepath.write_text(
        '\n'.join([
            'Timestamp (UTC),Type,Internal Id,Platform,Account Name,Platform Id,Blockchain Id,Record Type,Asset,Amount,Description',
            '2025-10-05T10:00:00.000,Interest,7000000001,Binance,Binance,,,Credit,USDT,-1.25,',
            '2025-10-05T10:01:00.000,Gift Sent,7000000002,Binance,Binance,,,Debit,BTC,0.001,',
            '2025-10-05T10:02:00.000,Interest,7000000003,Binance,Binance,,,Credit,USDT,0.8,',
        ]),
        encoding='utf-8',
    )

    success, msg = importer.import_csv(filepath=filepath)

    assert success is True
    assert msg == ''
    assert importer.total_entries == 3
    assert importer.imported_entries == 2
    assert len(importer.import_msgs) == 1
    assert all(import_msg.get('is_error') is True for import_msg in importer.import_msgs)
    assert all('Contradictory amount sign' in import_msg['msg'] for import_msg in importer.import_msgs)

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[('timestamp', True)]),
        )

    assert len(events) == 2
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-05T10:00:00.000') and
        event.event_type == HistoryEventType.SPEND and
        event.event_subtype == HistoryEventSubType.NONE and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('1.25')
        for event in events
    )
    assert any(
        isinstance(event, HistoryEvent) and
        event.timestamp == _coinledger_ts('2025-10-05T10:02:00.000') and
        event.event_type == HistoryEventType.RECEIVE and
        event.event_subtype == HistoryEventSubType.INTEREST and
        event.asset.symbol_or_name() == 'USDT' and
        event.amount == FVal('0.8')
        for event in events
    )
