import os
from contextlib import contextmanager
from pathlib import Path
from shutil import copyfile
from sqlite3 import Cursor
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.old_create import OLD_DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.upgrade_manager import UPGRADES_LIST
from rotkehlchen.db.upgrades.v6_v7 import (
    v6_deserialize_location_from_db,
    v6_deserialize_trade_type_from_db,
    v6_generate_trade_id,
)
from rotkehlchen.db.upgrades.v7_v8 import (
    MCDAI_LAUNCH_TS,
    v7_deserialize_asset_movement_category,
    v7_generate_asset_movement_id,
)
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.tests.utils.constants import A_BCH, A_BSV, A_RDN
from rotkehlchen.typing import FilePath, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

creation_patch = patch(
    'rotkehlchen.db.dbhandler.DB_SCRIPT_CREATE_TABLES',
    new=OLD_DB_SCRIPT_CREATE_TABLES,
)


@contextmanager
def target_patch(target_version: int):
    """Patches the upgrades to stop at target_version and also sets
    ROTKEHLCHEN_DB_VERSION to the target_version"""
    a = patch(
        'rotkehlchen.db.upgrade_manager.ROTKEHLCHEN_DB_VERSION',
        new=target_version,
    )
    b = patch(
        'rotkehlchen.db.dbhandler.ROTKEHLCHEN_DB_VERSION',
        new=target_version,
    )
    new_upgrades_list = [
        upgrade for upgrade in UPGRADES_LIST if upgrade.from_version < target_version
    ]

    c = patch(
        'rotkehlchen.db.upgrade_manager.UPGRADES_LIST',
        new=new_upgrades_list,
    )

    with a, b, c:
        yield (a, b, c)


def populate_db_and_check_for_asset_renaming(
        cursor: Cursor,
        data: DataHandler,
        data_dir: FilePath,
        msg_aggregator: MessagesAggregator,
        username: str,
        to_rename_asset: str,
        renamed_asset: Asset,
        target_version: int,
):
    # Manually input data to the affected tables.
    # timed_balances, multisettings and (external) trades

    # At this time point we only have occurence of the to_rename_asset
    cursor.execute(
        'INSERT INTO timed_balances('
        '   time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        ('1557499129', to_rename_asset, '10.1', '150'),
    )
    # But add a time point where we got both to_rename_asset and
    # renamed_asset. This is to test merging if renaming falls in time where
    # both new and old asset had entries
    cursor.execute(
        'INSERT INTO timed_balances('
        '   time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        ('1558499129', to_rename_asset, '1.1', '15'),
    )
    cursor.execute(
        'INSERT INTO timed_balances('
        '   time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        ('1558499129', renamed_asset.identifier, '2.2', '25'),
    )
    # Add one different asset for control test
    cursor.execute(
        'INSERT INTO timed_balances('
        '   time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        ('1556392121', 'ETH', '5.5', '245'),
    )
    # Also populate an ignored assets entry
    cursor.execute(
        'INSERT INTO multisettings(name, value) VALUES(?, ?)',
        ('ignored_asset', to_rename_asset),
    )
    cursor.execute(
        'INSERT INTO multisettings(name, value) VALUES(?, ?)',
        ('ignored_asset', 'RDN'),
    )
    # Finally include it in some trades
    cursor.execute(
        'INSERT INTO trades('
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes)'
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            1543298883,
            'external',
            'ETH_EUR',
            'buy',
            '100',
            '0.5',
            '0.1',
            'EUR',
            '',
            '',
        ),
    )
    cursor.execute(
        'INSERT INTO trades('
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes)'
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            1563298883,
            'kraken',
            f'{to_rename_asset}_EUR',
            'buy',
            '100',
            '0.5',
            '0.1',
            to_rename_asset,
            '',
            '',
        ),
    )
    cursor.execute(
        'INSERT INTO trades('
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes)'
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            1564218181,
            'binance',
            f'{to_rename_asset}_EUR',
            'buy',
            '100',
            '0.5',
            '0.1',
            'BNB',
            '',
            '',
        ),
    )
    data.db.conn.commit()

    # now relogin and check that all tables have appropriate data
    del data
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch, target_patch(target_version=target_version):
        data.unlock(username, '123', create_new=False)
    # Check that owned and ignored assets reflect the new state
    ignored_assets = data.db.get_ignored_assets()
    assert A_RDN in ignored_assets
    assert renamed_asset in ignored_assets
    owned_assets = data.db.query_owned_assets()
    assert A_ETH in owned_assets
    assert renamed_asset in owned_assets

    # Make sure that the merging of both new and old name entry in same timestamp works
    timed_balances = data.db.query_timed_balances(
        from_ts=Timestamp(0),
        to_ts=Timestamp(2556392121),
        asset=renamed_asset,
    )
    assert len(timed_balances) == 2
    assert timed_balances[0].time == 1557499129
    assert timed_balances[0].amount == '10.1'
    assert timed_balances[0].usd_value == '150'
    assert timed_balances[1].time == 1558499129
    assert timed_balances[1].amount == '3.3'
    assert timed_balances[1].usd_value == '40'

    # Assert that trades got renamed properly
    cursor = data.db.conn.cursor()
    query = (
        'SELECT id,'
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes FROM trades ORDER BY time ASC;'
    )
    results = cursor.execute(query)
    trades = []
    for result in results:
        trades.append({
            'id': result[0],
            'timestamp': result[1],
            'location': result[2],
            'pair': result[3],
            'trade_type': result[4],
            'amount': result[5],
            'rate': result[6],
            'fee': result[7],
            'fee_currency': result[8],
            'link': result[9],
            'notes': result[10],
        })
    assert len(trades) == 3
    assert trades[0]['fee_currency'] == 'EUR'
    assert trades[0]['pair'] == 'ETH_EUR'
    assert trades[1]['fee_currency'] == renamed_asset.identifier
    assert trades[1]['pair'] == f'{renamed_asset.identifier}_EUR'
    assert trades[2]['pair'] == f'{renamed_asset.identifier}_EUR'

    assert data.db.get_version() == target_version


def test_upgrade_db_1_to_2(data_dir, username):
    """Test upgrading the DB from version 1 to version 2, which means that
    ethereum accounts are now checksummed"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch, target_patch(1):
        data.unlock(username, '123', create_new=True)
    # Manually input a non checksummed account
    data.db.conn.commit()
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO blockchain_accounts(blockchain, account) VALUES(?, ?)',
        ('ETH', '0xe3580c38b0106899f45845e361ea7f8a0062ef12'),
    )
    data.db.conn.commit()

    # now relogin and check that the account has been re-saved as checksummed
    del data
    data = DataHandler(data_dir, msg_aggregator)
    with target_patch(target_version=2):
        data.unlock(username, '123', create_new=False)
    accounts = data.db.get_blockchain_accounts()
    assert accounts.eth[0] == '0xe3580C38B0106899F45845E361EA7F8a0062Ef12'
    version = data.db.get_version()
    # Also make sure that we have updated to the target_version
    assert version == 2


def test_upgrade_db_2_to_3(data_dir, username):
    """Test upgrading the DB from version 2 to version 3, rename BCHSV to BSV"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch:
        data.unlock(username, '123', create_new=True)
    # Manually set version (Both here and in 4 -> 5 it needs to be done like this and
    # target patch can't be used for some reason. Still have not debugged what fails
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(2)),
    )
    data.db.conn.commit()
    populate_db_and_check_for_asset_renaming(
        cursor=cursor,
        data=data,
        data_dir=data_dir,
        msg_aggregator=msg_aggregator,
        username=username,
        to_rename_asset='BCHSV',
        renamed_asset=A_BSV,
        target_version=3,
    )
    version = data.db.get_version()
    # Also make sure that we have updated to the target_version
    assert version == 3


def test_upgrade_db_3_to_4(data_dir, username):
    """Test upgrading the DB from version 3 to version 4, which means that
    the eth_rpc_port setting is changed to eth_rpc_endpoint"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch, target_patch(3):
        data.unlock(username, '123', create_new=True)
    # Manually set version and input the old rpcport setting
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(3)),
    )
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('eth_rpc_port', '8585'),
    )
    data.db.conn.commit()

    # now relogin and check that the setting has been changed and the version bumped
    del data
    data = DataHandler(data_dir, msg_aggregator)
    with target_patch(target_version=4):
        data.unlock(username, '123', create_new=False)
    cursor = data.db.conn.cursor()
    query = cursor.execute('SELECT value FROM settings where name="eth_rpc_endpoint";')
    query = query.fetchall()
    assert query[0][0] == 'http://localhost:8585'
    query = cursor.execute('SELECT value FROM settings where name="eth_rpc_port";')
    query = query.fetchall()
    assert len(query) == 0
    version = data.db.get_version()
    # Also make sure that we have updated to the target_version
    assert version == 4


def test_upgrade_db_4_to_5(data_dir, username):
    """Test upgrading the DB from version 4 to version 5, rename BCC to BCH"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch:
        data.unlock(username, '123', create_new=True)
    # Manually set version (Both here and in 2 -> 3 it needs to be done like this and
    # target patch can't be used for some reason. Still have not debugged what fails

    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(4)),
    )
    data.db.conn.commit()
    populate_db_and_check_for_asset_renaming(
        cursor=cursor,
        data=data,
        data_dir=data_dir,
        msg_aggregator=msg_aggregator,
        username=username,
        to_rename_asset='BCC',
        renamed_asset=A_BCH,
        target_version=5,
    )
    # Also make sure that we have updated to the target version
    assert data.db.get_version() == 5


def test_upgrade_db_5_to_6(data_dir, username):
    """Test upgrading the DB from version 5 to version 6.

    Test that the trades table is upgraded.
    Test that cache files are removed
    """
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v5_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )
    # Create fake cache files and make sure they are deleted.
    fake_cache_files = [
        os.path.join(userdata_dir, 'kraken_trades.json'),
        os.path.join(userdata_dir, 'trades_history.json'),
        os.path.join(userdata_dir, 'binance_deposits_withdrawals.json'),
    ]
    for filename in fake_cache_files:
        Path(filename).touch()

    with target_patch(target_version=6):
        db = DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)

    cursor = db.conn.cursor()
    query = (
        'SELECT id,'
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes FROM trades ORDER BY time ASC;'
    )
    results = cursor.execute(query)
    expected_results = [(
        '6cfa0a6db20c70910e06de83136448ef0ce90e524c80ba65bc8e9627cdfcbc00',
        1568928120,  # time
        'A',  # external symbol for location Enum
        'ETH_EUR',  # pair
        'B',  # type sell
        '10',  # amount
        '196.6',  # rate
        '0.001',  # fee
        'ETH',  # fee currency
        '',  # link
        'Test Sell 1',  # notes
    ), (
        '3f5d2dee22ad7efa545683351a8cec562c11dd9c357bdfce713154696bdd56ea',
        1569010800,  # time
        'A',  # external symbol for location Enum
        'BTC_EUR',  # pair
        'A',  # type buy
        '0.5',  # amount
        '9240.1',  # rate
        '0.1',  # fee
        'EUR',  # fee currency
        '',  # link
        'Test Buy 1',  # notes
    )]
    results = results.fetchall()
    assert results == expected_results

    # Also test that the location got properly updated in the timed_location_data table
    query = 'SELECT time, location, usd_value FROM timed_location_data ORDER BY time ASC;'
    results = cursor.execute(query)
    expected_results = [(
        1569186628,  # time
        'H',  # total symbol for DB location Enum
        '6561.07369468235924484',  # usd_value
    ), (
        1569186628,  # time
        'I',  # bank symbol for DB location Enum
        '165.450',  # usd_value
    ), (
        1569186628,  # time
        'J',  # blockchain symbol for DB location Enum
        '6395.62369468235924484',  # usd_value
    )]
    results = results.fetchall()

    assert results == expected_results

    # Also make sure the cache files were deleted
    for filename in fake_cache_files:
        assert not os.path.exists(filename)
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 6


def test_upgrade_db_6_to_7(data_dir, username):
    """Test upgrading the DB from version 6 to version 7.

    Test that the trades tables has the new trade ids.
    """
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v6_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )

    with target_patch(target_version=7):
        db = DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)

    cursor = db.conn.cursor()
    query = (
        'SELECT id,'
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes FROM trades ORDER BY time ASC;'
    )
    results = cursor.execute(query)
    expected_results = [(
        'fafd58fce59b9d5c5308be1994633e4adc35bce82ac04a9f793f8137ba4a6793',
        1568928120,  # time
        'A',  # external symbol for location Enum
        'ETH_EUR',  # pair
        'B',  # type sell
        '10',  # amount
        '196.6',  # rate
        '0.001',  # fee
        'ETH',  # fee currency
        '',  # link
        'Test Sell 1',  # notes
    ), (
        'dca097b6e0b5aa2b3d5fc26fd9d83527db7fe447e2a42b4000799ddb17bf1e83',
        1569010800,  # time
        'A',  # external symbol for location Enum
        'BTC_EUR',  # pair
        'A',  # type buy
        '0.5',  # amount
        '9240.1',  # rate
        '0.1',  # fee
        'EUR',  # fee currency
        '',  # link
        'Test Buy 1',  # notes
    )]
    results = results.fetchall()
    assert results == expected_results

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 7


def test_upgrade_db_7_to_8(data_dir, username):
    """Test upgrading the DB from version 7 to version 8.

    Test that the SAI to DAI upgrade and renaming is done succesfully.
    """
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v7_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )
    with target_patch(target_version=8):
        db = DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)
    cursor = db.conn.cursor()

    # Check that trades got upgraded properly
    query = (
        'SELECT id,'
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes FROM trades ORDER BY time ASC;'
    )

    results = cursor.execute(query)
    count = 0
    for result in results:
        count += 1
        trade_id = result[0]
        time = int(result[1])
        location = result[2]
        pair = result[3]
        trade_type = result[4]
        amount = result[5]
        rate = result[6]
        fee_currency = result[8]
        link = result[9]

        # External trades, kraken trades
        if location in ('A', 'B'):
            if time < MCDAI_LAUNCH_TS:
                assert pair == 'SAI_EUR'
                assert fee_currency == 'EUR'
            else:
                assert pair == 'DAI_EUR'
                assert fee_currency == 'EUR'
        # coinbase trades
        elif location == 'G':
            if time < MCDAI_LAUNCH_TS:
                assert pair == 'SAI_USD'
                assert fee_currency == 'USD'
            else:
                assert pair == 'DAI_USD'
                assert fee_currency == 'USD'
        # bittrex trades
        elif location == 'D':
            if time < MCDAI_LAUNCH_TS:
                assert pair == 'SAI_BTC'
                assert fee_currency == 'SAI'
            else:
                assert pair == 'DAI_BTC'
                assert fee_currency == 'DAI'
        else:
            raise AssertionError('Unexpected location data')

        # also make sure the ids still match
        serialized_location = v6_deserialize_location_from_db(location)
        serialized_trade_type = v6_deserialize_trade_type_from_db(trade_type)
        expected_trade_id = v6_generate_trade_id(
            location=serialized_location,
            time=time,
            trade_type=serialized_trade_type,
            pair=pair,
            amount=amount,
            rate=rate,
            link=link,
        )
        assert trade_id == expected_trade_id

    assert count == 8, '8 trades should have been found'

    # Check that deposits/withdrawals got upgraded properly
    query = (
        'SELECT id,'
        '  location,'
        '  category,'
        '  time,'
        '  asset,'
        '  amount,'
        '  fee_asset,'
        '  fee,'
        '  link FROM asset_movements '
    )
    results = cursor.execute(query)
    count = 0
    for result in results:
        count += 1
        entry_id = result[0]
        location = result[1]
        category = result[2]
        time = result[3]
        asset = result[4]
        fee_asset = result[6]
        link = result[8]

        # kraken , bittrex, coinbase
        assert location in ('B', 'D', 'G'), 'Unexpected location of asset movement'
        if time < MCDAI_LAUNCH_TS:
            assert asset == 'SAI'
            assert fee_asset == 'SAI'
        else:
            assert asset == 'DAI'
            assert fee_asset == 'DAI'

        deserialized_location = v6_deserialize_location_from_db(location)
        deserialized_category = v7_deserialize_asset_movement_category(category)
        expected_id = v7_generate_asset_movement_id(
            location=deserialized_location,
            category=deserialized_category,
            time=time,
            asset=asset,
            fee_asset=fee_asset,
            link=link,
        )
        assert expected_id == entry_id

    assert count == 12, '12 asset movements should have been found'

    # Check that both SAI and DAI are included in the ETH tokens owned
    query = cursor.execute(
        'SELECT value FROM multisettings WHERE name="eth_token";',
    )
    assert [q[0] for q in query.fetchall()] == ['DAI', 'SAI']

    # Check that saved balances of DAI are upgraded to SAI if before the upgrade time
    query = cursor.execute('SELECT time, currency, amount, usd_value FROM timed_balances;')
    count = 0
    for result in query:
        count += 1
        time = int(result[0])
        asset = result[1]

        if time < MCDAI_LAUNCH_TS:
            assert asset == 'SAI'
        else:
            assert asset == 'DAI'

    assert count == 2, '2 saved balances should have been found'

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 8


def test_upgrade_broken_db_7_to_8(data_dir, username):
    """Test that if SAI is already in owned tokens upgrade fails"""
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v7_rotkehlchen_broken.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )
    with pytest.raises(DBUpgradeError):
        with target_patch(target_version=8):
            DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)


def test_upgrade_db_8_to_9(data_dir, username):
    """Test upgrading the DB from version 8 to version 9.

    Adding the passphrase column to user credentials"""
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v8_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )

    with target_patch(target_version=9):
        db = DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)

    cursor = db.conn.cursor()
    results = cursor.execute(
        'SELECT name, api_key, api_secret, passphrase FROM user_credentials;',
    )
    names = {'coinbase', 'coinbasepro', 'binance', 'bittrex', 'kraken', 'bitmex'}
    for result in results:
        assert result[0] in names
        names.remove(result[0])
        assert result[1] == '9f07a6f548f3d0ddb68fb406353063ba'  # api key
        assert result[2] == (
            'auIO4FWI3HmL1AnhYaNoK0vr4tTaZyAU3/TI9M46V9IeeCPTxyWV'
            '3JCVzHmcVV9+n+v4TbsIyRndaL9XbFkCuQ=='
        )  # api secret
        assert result[3] is None  # passphrase

    assert len(names) == 0, 'not all exchanges were found in the new DB'
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 9


def test_upgrade_db_9_to_10(data_dir, username):
    """Test upgrading the DB from version 9 to version 10.

    Deleting all entries from used_query_ranges"""
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v9_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )

    with target_patch(target_version=10):
        db = DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)

    cursor = db.conn.cursor()
    results = cursor.execute(
        'SELECT name, start_ts, end_ts FROM used_query_ranges;',
    )
    assert len(results.fetchall()) == 0
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 10


def test_upgrade_db_10_to_11(data_dir, username):
    """Test upgrading the DB from version 10 to version 11.

    Deleting all entries from used_query_ranges"""
    msg_aggregator = MessagesAggregator()
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'v10_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )

    with target_patch(target_version=11):
        db = DBHandler(user_data_dir=userdata_dir, password='123', msg_aggregator=msg_aggregator)

    # Make sure that the blockchain accounts table is upgraded
    expected_results = [
        ('ETH', '0xB2CEB220df2e4a5ec6A0aC93d79655895E9886Bc', None),
        ('ETH', '0x926cbe37d3487a881F9EB18F4746Ee09557D79cB', None),
        ('BTC', '37SQZzaCPbDno9aFBjaVKhA9KkzTbt94x2', None),
    ]
    cursor = db.conn.cursor()
    results = cursor.execute(
        'SELECT blockchain, account, label FROM blockchain_accounts;',
    )
    for idx, entry in enumerate(results):
        assert entry == expected_results[idx]

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 11


def test_db_newer_than_software_raises_error(data_dir, username):
    """
    If the DB version is greater than the current known version in the
    software warn the user to use the latest version of the software
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    # Manually set a bigger version than the current known one
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(ROTKEHLCHEN_DB_VERSION + 1)),
    )
    data.db.conn.commit()

    # now relogin and check that an error is thrown
    del data
    data = DataHandler(data_dir, msg_aggregator)
    with pytest.raises(DBUpgradeError):
        data.unlock(username, '123', create_new=False)
