from rotkehlchen.data_import.importers.bittrex import BittrexImporter
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.types import Location


def test_bittrex_import_trades_unknown_asset_continues(database, tmp_path) -> None:
    """An unknown asset in a Bittrex trade row must not fail the entire import."""
    filepath = tmp_path / 'bittrex_order_history.csv'
    filepath.write_text(
        'TXID,Time (UTC),Transaction,Order Type,Market,Base,Quote,Price,'
        'Quantity (Base),Fees (Quote),Total (Quote),Approx Value (USD),'
        'Time In Force,Notes\n'
        '28445361-31c6-1ab1-91a9-e196d50ad1a5,2017-12-03T12:04:16,Bought,'
        'Limit,ZZZFAKE/BTC,ZZZFAKE,BTC,0.00034100,731.28354007,0.00062343,'
        '0.24999841,,Good til cancelled,"Bought 731.28354007 ZZZFAKE for 0.24999841 BTC"\n'
        'a3a27e1a-2b6c-3b82-c275-d61e375d35a2,2017-08-13T21:32:03,Sold,'
        'Limit,ETH/BTC,ETH,BTC,0.00018098,857.78221905,0.00038812,'
        '0.15486188,,Good til cancelled,"Sold 857.78221905 ETH for 0.15486188 BTC"\n',
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

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.BITTREX),
        )
    assert len(events) == 3  # spend, receive, and fee for the valid ETH/BTC trade


def test_bittrex_import_movements_unknown_asset_continues(database, tmp_path) -> None:
    """An unknown asset in a Bittrex deposit or withdrawal row must not fail the entire import."""
    filepath = tmp_path / 'bittrex_tx_history.csv'
    filepath.write_text(
        'Date,Currency,Type,Address,Memo/Tag,TxId,Amount\n'
        '2023-03-07 07:51:43.043,ZZZFAKE,WITHDRAWAL,'
        '"0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5","",'
        '"0xecac30357b613f6bcb5bc148fdd1d608bd94021e95a59233003948fde0c7c4d9",-0.20084931\n'
        '2021-09-28 22:35:21.970,ETH,DEPOSIT,"","",'
        '"1A313456CCEA5AF45B334881513CF472",+0.00000001\n',
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

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.BITTREX),
        )
    assert len(events) == 1
