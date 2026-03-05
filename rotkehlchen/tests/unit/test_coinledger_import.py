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
    assert importer.total_entries == 12
    assert importer.imported_entries == 12
    assert importer.import_msgs == []

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[('timestamp', True)]),
        )

    assert len(events) == 12
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
