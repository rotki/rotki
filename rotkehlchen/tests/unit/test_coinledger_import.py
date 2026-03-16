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
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[
                ('timestamp', True),
                ('history_events_identifier', True),
            ]),
        )

    assert len(events) == 27
    event = events[3]
    assert isinstance(event, AssetMovement)
    assert event.timestamp == _coinledger_ts('2025-03-02T16:24:08.000')
    assert event.location == Location.BINANCE
    assert event.event_subtype == HistoryEventSubType.RECEIVE
    assert event.asset == Asset('DOGE')
    assert event.amount == FVal('111.5')
    assert event.extra_data == {
        'transaction_id': '11165cb38fa8b31eb910d03d4c2afb8ebb0abc0a967485ee7b07d026722714f6',
    }
    assert event.location_label == 'Binance'
    assert event.notes == 'Deposit (Credit) from CoinLedger'

    event = events[10]
    assert isinstance(event, AssetMovement)
    assert event.timestamp == _coinledger_ts('2025-08-12T05:33:18.000')
    assert event.location == Location.BINANCE
    assert event.event_subtype == HistoryEventSubType.SPEND
    assert event.asset == Asset('DOGE')
    assert event.amount == FVal('55')
    assert event.extra_data == {
        'transaction_id': 'b1923e958f1110a8ef9fbd8b8f1592211ed7bf2256c07501a76168830a651bce',
    }
    assert event.location_label == 'Binance'
    assert event.notes == 'Withdrawal (Debit) from CoinLedger'

    event = events[8]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-08-06T07:16:26.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.SPEND
    assert event.event_subtype == HistoryEventSubType.NONE
    assert event.asset == Asset('EUR')
    assert event.amount == FVal('15.6')
    assert event.extra_data == {'transaction_id': 'b7f960bd8e194d3991ab50111013ce58'}
    assert event.location_label == 'Binance'
    assert event.notes == 'Buy (Debit) from CoinLedger'

    event = events[6]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-03-06T00:00:00.000')
    assert event.location == Location.EXTERNAL
    assert event.event_type == HistoryEventType.SPEND
    assert event.event_subtype == HistoryEventSubType.FEE
    assert event.asset.symbol_or_name() == 'TRX'
    assert event.amount == FVal('0.14195')
    assert event.location_label == 'Pionex'
    assert event.notes == 'Trade (Platform Fee) from CoinLedger'

    event = events[11]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-09-22T07:58:00.000')
    assert event.location == Location.EXTERNAL
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.NONE
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('111')
    assert event.location_label == 'Pionex'
    assert event.notes == 'Margin Gain (Margin Gain) from CoinLedger'

    event = events[12]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T10:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.SPEND
    assert event.event_subtype == HistoryEventSubType.FEE
    assert event.asset.symbol_or_name() == 'ETH'
    assert event.amount == FVal('0.002')
    assert event.location_label == 'Binance'
    assert event.notes == 'Network Fee (Debit) from CoinLedger'

    event = events[13]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T11:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.INTEREST
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('1.5')
    assert event.location_label == 'Binance'
    assert event.notes == 'Interest (Credit) from CoinLedger'

    event = events[14]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T12:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.REWARD
    assert event.asset.symbol_or_name() == 'BTC'
    assert event.amount == FVal('0.01')
    assert event.location_label == 'Binance'
    assert event.notes == 'Mining (Credit) from CoinLedger'

    event = events[15]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T13:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.STAKING
    assert event.event_subtype == HistoryEventSubType.REWARD
    assert event.asset.symbol_or_name() == 'ETH'
    assert event.amount == FVal('0.2')
    assert event.location_label == 'Binance'
    assert event.notes == 'Staking (Credit) from CoinLedger'

    event = events[16]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T14:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.AIRDROP
    assert event.asset.symbol_or_name() == 'DOGE'
    assert event.amount == FVal('5')
    assert event.location_label == 'Binance'
    assert event.notes == 'Airdrop (Credit) from CoinLedger'

    event = events[17]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T15:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.DONATE
    assert event.asset.symbol_or_name() == 'BTC'
    assert event.amount == FVal('0.001')
    assert event.location_label == 'Binance'
    assert event.notes == 'Gift Received (Credit) from CoinLedger'

    event = events[18]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T16:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.SPEND
    assert event.event_subtype == HistoryEventSubType.DONATE
    assert event.asset.symbol_or_name() == 'BTC'
    assert event.amount == FVal('0.0005')
    assert event.location_label == 'Binance'
    assert event.notes == 'Gift Sent (Debit) from CoinLedger'

    event = events[19]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T17:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.INTEREST
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('0.5')
    assert event.location_label == 'Binance'
    assert event.notes == 'Interest Payment (Credit) from CoinLedger'

    event = events[20]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T18:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.LOSS
    assert event.event_subtype == HistoryEventSubType.NONE
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('12')
    assert event.location_label == 'Binance'
    assert event.notes == 'Investment Loss (Debit) from CoinLedger'

    event = events[21]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T19:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.LOSS
    assert event.event_subtype == HistoryEventSubType.HACK
    assert event.asset.symbol_or_name() == 'ETH'
    assert event.amount == FVal('0.03')
    assert event.location_label == 'Binance'
    assert event.notes == 'Theft Loss (Debit) from CoinLedger'

    event = events[22]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T20:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.SPEND
    assert event.event_subtype == HistoryEventSubType.PAYMENT
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('4')
    assert event.location_label == 'Binance'
    assert event.notes == 'Merchant Payment (Debit) from CoinLedger'

    event = events[23]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T21:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.NONE
    assert event.asset.symbol_or_name() == 'BCH'
    assert event.amount == FVal('0.7')
    assert event.location_label == 'Binance'
    assert event.notes == 'Hard Fork (Credit) from CoinLedger'

    event = events[24]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T22:00:00.000')
    assert event.location == Location.KRAKEN
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.INTEREST
    assert event.asset.symbol_or_name() == 'EUR'
    assert event.amount == FVal('2.5')
    assert event.location_label == 'Kraken'
    assert event.notes == 'Interest (Credit) from CoinLedger'

    event = events[25]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-01T23:00:00.000')
    assert event.location == Location.COINBASE
    assert event.event_type == HistoryEventType.STAKING
    assert event.event_subtype == HistoryEventSubType.REWARD
    assert event.asset.symbol_or_name() == 'ETH'
    assert event.amount == FVal('0.5')
    assert event.location_label == 'Coinbase'
    assert event.notes == 'Staking (Credit) from CoinLedger'

    event = events[26]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-02T00:00:00.000')
    assert event.location == Location.BINANCE
    assert event.event_type == HistoryEventType.LOSS
    assert event.event_subtype == HistoryEventSubType.NONE
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('5.8')
    assert event.location_label == 'Binance'
    assert event.notes == 'Margin Gain (Margin Gain) from CoinLedger'


def test_coinledger_importer_rejects_contradictory_signs(database, tmp_path) -> None:
    importer = CoinledgerImporter(db=database)
    filepath = tmp_path / 'coinledger_contradictory_signs.csv'
    header = (
        'Timestamp (UTC),Type,Internal Id,Platform,Account Name,'
        'Platform Id,Blockchain Id,Record Type,Asset,Amount,Description'
    )
    filepath.write_text(
        f'{header}\n'
        '2025-10-05T10:00:00.000,Interest,7000000001,Binance,Binance,,,Credit,USDT,-1.25,\n'
        '2025-10-05T10:01:00.000,Gift Sent,7000000002,Binance,Binance,,,Debit,BTC,0.001,\n'
        '2025-10-05T10:02:00.000,Interest,7000000003,Binance,Binance,,,Credit,USDT,0.8,',
        encoding='utf-8',
    )

    success, msg = importer.import_csv(filepath=filepath)

    assert success is True
    assert msg == ''
    assert importer.total_entries == 3
    assert importer.imported_entries == 2
    assert len(importer.import_msgs) == 1
    assert all(import_msg.get('is_error') is True for import_msg in importer.import_msgs)
    assert all(
        'Contradictory amount sign' in import_msg['msg'] for import_msg in importer.import_msgs
    )

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[
                ('timestamp', True),
                ('history_events_identifier', True),
            ]),
        )

    assert len(events) == 2
    event = events[0]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-05T10:00:00.000')
    assert event.event_type == HistoryEventType.SPEND
    assert event.event_subtype == HistoryEventSubType.NONE
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('1.25')

    event = events[1]
    assert isinstance(event, HistoryEvent)
    assert event.timestamp == _coinledger_ts('2025-10-05T10:02:00.000')
    assert event.event_type == HistoryEventType.RECEIVE
    assert event.event_subtype == HistoryEventSubType.INTEREST
    assert event.asset.symbol_or_name() == 'USDT'
    assert event.amount == FVal('0.8')
