from rotkehlchen.data_import.importers.kucoin import KucoinImporter
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.types import Location


def test_kucoin_import_unknown_asset_continues(database, tmp_path) -> None:
    """An asset in a row that cannot be resolved must not crash the whole
    import. It should be recorded as a per-row error and valid rows must import.
    """
    filepath = tmp_path / 'kucoin_order_history.csv'
    filepath.write_text(
        'tradeCreatedAt,symbol,side,price,size,funds,fee,feeCurrency\n'
        '2022-04-28 12:36:00,ZZZFAKE-USDT,sell,0.1025,36.4479,3.73590975,0.00373590975,USDT\n'
        '2022-04-28 15:46:07,ETH-USDT,buy,3000.0,1.5,4500.0,4.5,USDT\n',
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

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KUCOIN),
        )
    assert len(events) == 3  # spend, receive, and fee for the valid ETH-USDT buy swap


def test_kucoin_import_unknown_fee_currency_continues(database, tmp_path) -> None:
    """An unknown fee currency must also be caught per-row."""
    filepath = tmp_path / 'kucoin_fee_unknown.csv'
    filepath.write_text(
        'tradeCreatedAt,symbol,side,price,size,funds,fee,feeCurrency\n'
        '2022-04-28 12:36:00,ETH-USDT,buy,3000.0,1.0,3000.0,0.01,ZZZFAKE\n'
        '2022-04-28 15:46:07,BTC-USDT,buy,40000.0,0.1,4000.0,0.0001,BTC\n',
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


def test_kucoin_import_old_format_unknown_asset_continues(database, tmp_path) -> None:
    """Old Kucoin CSV format handles unknown assets per row."""
    filepath = tmp_path / 'kucoin_order_history_old.csv'
    filepath.write_text(
        'Time,Pair,Side,FilledPrice,FilledPriceCoin,Amount,AmountCoin,'
        'Volume,VolumeCoin,Fee,FeeCoin\n'
        '2019/05/11 10:27:17,ZZZFAKE/BTC,Buy,0.00015225,BTC,10.01,ZZZFAKE,'
        '0.00152402,BTC,0.00000152,BTC\n'
        '2019/05/11 10:27:18,ETH/BTC,Sell,0.05,BTC,2.0,ETH,0.1,BTC,0.0001,BTC\n',
    )

    importer = KucoinImporter(db=database)
    success, msg = importer.import_csv(
        filepath=filepath,
        timestamp_format='%Y/%m/%d %H:%M:%S',
    )
    assert success is True
    assert msg == ''
    assert importer.total_entries == 2
    assert importer.imported_entries == 1

    error_msgs = [m for m in importer.import_msgs if m.get('is_error')]
    assert len(error_msgs) == 1
    assert 'ZZZFAKE' in error_msgs[0]['msg']
    assert 'Unknown asset' in error_msgs[0]['msg']
