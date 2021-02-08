import json
import os
from contextlib import contextmanager
from pathlib import Path
from shutil import copyfile
from sqlite3 import Cursor
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures import BalanceType
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
from rotkehlchen.db.upgrades.v13_v14 import REMOVED_ASSETS, REMOVED_ETH_TOKENS
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.tests.utils.constants import A_BCH, A_BSV, A_RDN
from rotkehlchen.tests.utils.factories import make_ethereum_address
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


def _init_db_with_target_version(
        target_version: int,
        user_data_dir: Path,
        msg_aggregator: MessagesAggregator,
) -> DBHandler:
    with target_patch(target_version=target_version):
        db = DBHandler(
            user_data_dir=user_data_dir,
            password='123',
            msg_aggregator=msg_aggregator,
            initial_settings=None,
        )
    return db


def _use_prepared_db(user_data_dir: Path, filename: str) -> None:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', filename),
        user_data_dir / 'rotkehlchen.db',
    )


def populate_db_and_check_for_asset_renaming(
        cursor: Cursor,
        data: DataHandler,
        data_dir: Path,
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
    querystr = (
        f'SELECT time, amount, usd_value FROM timed_balances WHERE time BETWEEN '
        f'0 AND 2556392121 AND currency="{renamed_asset.identifier}" ORDER BY time ASC;'
    )
    cursor = data.db.conn.cursor()
    result = cursor.execute(querystr).fetchall()
    assert len(result) == 2
    assert result[0][0] == 1557499129
    assert result[0][1] == '10.1'
    assert result[0][2] == '150'
    assert result[1][0] == 1558499129
    assert result[1][1] == '3.3'
    assert result[1][2] == '40'

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


def test_upgrade_db_5_to_6(user_data_dir):
    """Test upgrading the DB from version 5 to version 6.

    Test that the trades table is upgraded.
    Test that cache files are removed
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v5_rotkehlchen.db')
    # Create fake cache files and make sure they are deleted.
    fake_cache_files = [
        user_data_dir / 'kraken_trades.json',
        user_data_dir / 'trades_history.json',
        user_data_dir / 'binance_deposits_withdrawals.json',
    ]
    for filename in fake_cache_files:
        filename.touch()
    db = _init_db_with_target_version(
        target_version=6,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
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


def test_upgrade_db_6_to_7(user_data_dir):
    """Test upgrading the DB from version 6 to version 7.

    Test that the trades tables has the new trade ids.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v6_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=7,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
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


def test_upgrade_db_7_to_8(user_data_dir):
    """Test upgrading the DB from version 7 to version 8.

    Test that the SAI to DAI upgrade and renaming is done succesfully.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v7_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=8,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
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


def test_upgrade_broken_db_7_to_8(user_data_dir):
    """Test that if SAI is already in owned tokens upgrade fails"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v7_rotkehlchen_broken.db')
    with pytest.raises(DBUpgradeError):
        _init_db_with_target_version(
            target_version=8,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
        )


def test_upgrade_db_8_to_9(user_data_dir):
    """Test upgrading the DB from version 8 to version 9.

    Adding the passphrase column to user credentials"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v8_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=9,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )

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


def test_upgrade_db_9_to_10(user_data_dir):
    """Test upgrading the DB from version 9 to version 10.

    Deleting all entries from used_query_ranges"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v9_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=10,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )

    cursor = db.conn.cursor()
    results = cursor.execute(
        'SELECT name, start_ts, end_ts FROM used_query_ranges;',
    )
    assert len(results.fetchall()) == 0
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 10


def test_upgrade_db_10_to_11(user_data_dir):
    """Test upgrading the DB from version 10 to version 11.

    Deleting all entries from used_query_ranges"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v10_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=11,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )

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


def test_upgrade_db_11_to_12(user_data_dir):
    """Test upgrading the DB from version 11 to version 12.

    Deleting all bittrex data from the DB"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v11_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=12,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )

    # Make sure that only one trade is left
    cursor = db.conn.cursor()
    results = cursor.execute('SELECT * FROM trades;')
    assert len(results.fetchall()) == 1
    # Same thing for used query ranges
    results = cursor.execute('SELECT * FROM used_query_ranges;')
    assert len(results.fetchall()) == 1
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 12


def test_upgrade_db_12_to_13(user_data_dir):
    """Test upgrading the DB from version 12 to version 13.

    Migrating fiat balances to manually tracked balances and
    deleting alethio credentials and owned eth tokens
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v12_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=13,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )

    # Make sure that current balances table is deleted
    cursor = db.conn.cursor()
    # with pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member
    query = cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name="current_balances"',
    )
    assert query.fetchall()[0][0] == 0, 'current_balances table still exists'

    # Also assure that fiat balances migrated properly
    expected_manual_balances = [
        ('EUR', 'My EUR bank', '3000', 'I'),
        ('ETH', 'ETH in paper wallet', '1', 'J'),
        ('CNY', 'My Chinese bank', '40000', 'I'),
        ('USD', 'My USD bank', '2000', 'I'),
        ('EUR', 'Migrated from fiat balances. My EUR bank', '2500', 'I'),
        ('CNY', 'My CNY bank', '350000', 'I'),
    ]
    query = cursor.execute('SELECT asset, label, amount, location FROM manually_tracked_balances;')
    results = query.fetchall()
    assert set(results) == set(expected_manual_balances)

    # Check that eth tokens are deleted, and only ignored asset remains
    query = cursor.execute('SELECT name, value FROM multisettings;')
    results = query.fetchall()
    assert len(results) == 1
    assert results[0][0] == 'ignored_asset'
    assert results[0][1] == 'DAO'

    # Check that alethio credentials are deleted
    query = cursor.execute('SELECT name, api_key FROM external_service_credentials;')
    results = query.fetchall()
    assert len(results) == 1
    assert results[0][0] == 'etherscan'
    assert results[0][1] == 'APIKEYVALUE'

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 13


def test_upgrade_db_13_to_14(user_data_dir):
    """Test upgrading the DB from version 13 to version 14.

    Deletes all references of removed assets from the DB
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v13_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=14,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )

    cursor = db.conn.cursor()
    # Make sure that all cached ethereum account details are deleted
    query = cursor.execute('SELECT COUNT(*) FROM ethereum_accounts_details;')
    assert query.fetchall()[0][0] == 0, 'ethereum accounts details were not deleted'
    # Make sure that timed balances with removed assets are removed
    query = cursor.execute('SELECT currency FROM timed_balances;')
    result = query.fetchall()
    assert len(result) == 32
    for entry in result:
        assert entry[0] not in REMOVED_ASSETS + REMOVED_ETH_TOKENS

    # Make sure that manually tracked balances with removed assets are removed
    query = cursor.execute('SELECT asset FROM manually_tracked_balances;')
    result = query.fetchall()
    assert len(result) == 1
    assert result[0][0] == 'EUR'

    # Make sure that trades with removed assets in the pair or in the fee currency are removed
    query = cursor.execute('SELECT pair FROM trades;')
    result = query.fetchall()
    assert len(result) == 1
    assert result[0][0] == 'ETH_EUR'

    # Make sure that removed assets are also gone from the ignored_assets
    query = cursor.execute(
        'SELECT name, value FROM multisettings where name = ?;', ('ignored_asset',),
    )
    result = query.fetchall()
    assert len(result) == 1
    assert result[0][1] == 'DAO'

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 14


def test_upgrade_db_15_to_16(user_data_dir):
    """Test upgrading the DB from version 15 to version 16.

    Deletes all transactions and asset movements from the DB, also asset movement query ranges
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v15_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=16,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    assert cursor.execute('SELECT COUNT(*) FROM ethereum_transactions;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) FROM asset_movements;').fetchone()[0] == 0
    # Make sure address and transaction_id exist as part of asset movements
    assert cursor.execute('SELECT address FROM asset_movements;').fetchall() == []
    assert cursor.execute('SELECT transaction_id FROM asset_movements;').fetchall() == []
    # Test that the only remaining query ranges are the non-asset movements ones
    assert cursor.execute('SELECT COUNT(*) FROM used_query_ranges;').fetchone()[0] == 2

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 16


def test_upgrade_db_16_to_17(user_data_dir):
    """Test upgrading the DB from version 16 to version 17.

    Deletes all transactions from the DB and recreates the table
    to include from_adddress in primary key
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v16_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=17,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    assert cursor.execute('SELECT COUNT(*) FROM ethereum_transactions;').fetchone()[0] == 0
    # Test that query ranges also get cleared
    assert cursor.execute('SELECT COUNT(*) FROM used_query_ranges;').fetchone()[0] == 0

    # Test that entering same tx hash, from nonce but different from/to is allowed
    from_addr = make_ethereum_address()
    to_addr = make_ethereum_address()
    query = """
    INSERT INTO ethereum_transactions(
    tx_hash,
    timestamp,
    block_number,
    from_address,
    to_address,
    value,
    gas,
    gas_price,
    gas_used,
    input_data,
    nonce)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    cursor.executemany(query, [
        (b'1', 1, 1, from_addr, to_addr, 1, 1, 1, 1, b'', 1),
        (b'1', 1, 1, to_addr, from_addr, 1, 1, 1, 1, b'', 1),
    ])
    assert cursor.execute('SELECT COUNT(*) FROM ethereum_transactions;').fetchone()[0] == 2

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 17


def test_upgrade_db_18_to_19(user_data_dir):
    """Test upgrading the DB from version 18 to version 19.

    Deletes all aave data and recreates table with all the new attributes
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v18_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=19,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    assert cursor.execute('SELECT COUNT(*) FROM aave_events;').fetchone()[0] == 0
    # Test that query ranges also get cleared
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "aave_events%";',
    ).fetchone()[0] == 0
    # test schema upgrade by using a new column from the upgraded schema. If nonexisting it raises
    cursor.execute('SELECT asset2usd_value_accruedinterest_feeusdvalue FROM aave_events;')

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 19


def test_upgrade_db_19_to_20(user_data_dir):
    """Test upgrading the DB from version 19 to version 20.

    Deletes all xpubs with derivations path that are invalid and not processable by rotki
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v19_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=20,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()
    query = cursor.execute('SELECT xpub, derivation_path, label FROM xpubs;')
    length = 0
    expected_results = [
        ('xpub6DCi5iJ57ZPd5qPzvTm5hUt6X23TJdh9H4NjNsNbt7t7UuTMJfawQWsdWRFhfLwkiMkB1rQ4ZJWLB9YBnzR7kbs9N8b2PsKZgKUHQm1X4or', '', 'My totally public xpub'),  # noqa: E501
        ('ypub6WkRUvNhspMCJLiLgeP7oL1pzrJ6wA2tpwsKtXnbmpdAGmHHcC6FeZeF4VurGU14dSjGpF2xLavPhgvCQeXd6JxYgSfbaD1wSUi2XmEsx33', '', ''),  # noqa: E501
        ('xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk', 'm/1/15', 'valid derivation path xpub'),  # noqa: E501
    ]
    for entry in query:
        assert (entry[0], entry[1], entry[2]) in expected_results
        length += 1

    assert length == 3

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 20


def test_upgrade_db_20_to_21(user_data_dir):
    """Test upgrading the DB from version 20 to version 21.

    Create a new balance_category table and upgrades the timed
    balances to also contain the balance type (category). Defaults to asset
    right now, but opens up the way to store liabilities too
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v20_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=21,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()
    # if nothing is raised here we are good
    query = cursor.execute('SELECT * FROM balance_category;')
    query = cursor.execute(
        'SELECT category, time, currency, amount, usd_value FROM timed_balances '
        'ORDER BY time ASC;',
    )
    length = 0
    entry = None
    for entry in query:
        assert BalanceType.deserialize_from_db(entry[0]) == BalanceType.ASSET
        # Check the last 3 entries to make sure no data is lost during upgrade
        if length == 1297:
            assert entry == (
                BalanceType.ASSET.serialize_for_db(),
                1605194428,
                'yaLINK',
                '444.562307846438094287',
                '5843.922363085966843444941265',
            )
        elif length == 1298:
            assert entry == (
                BalanceType.ASSET.serialize_for_db(),
                1605194428,
                'ypaxCrv',
                '211.750728445895069118',
                '217.2597399646382941219959776',
            )
        elif length == 1299:
            assert entry == (
                BalanceType.ASSET.serialize_for_db(),
                1605194428,
                'yyDAI+yUSDC+yUSDT+yBUSD',
                '167.18639752015697023',
                '185.7646591376060274165290659',
            )
        length += 1
    assert length == 1300
    assert entry == (
        BalanceType.ASSET.serialize_for_db(),
        1605194428,
        'yyDAI+yUSDC+yUSDT+yBUSD',
        '167.18639752015697023',
        '185.7646591376060274165290659',
    )
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 21


def test_upgrade_db_21_to_22(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 21 to version 22.

    Upgrade the eth2 deposits table to rename validator_index to deposit_index
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v21_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=22,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()
    # if nothing is raised here we are good
    query = cursor.execute('SELECT * FROM eth2_deposits;')
    query = cursor.execute(
        'SELECT tx_hash, '
        'log_index, '
        'from_address, '
        'timestamp, '
        'pubkey, '
        'withdrawal_credentials, '
        'amount, '
        'usd_value, '
        'deposit_index from eth2_deposits;',
    )
    length = 0
    for _ in query:
        length += 1
    assert length == 0
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 22


def test_upgrade_db_22_to_23_with_frontend_settings(user_data_dir):
    """Test upgrading the DB from version 22 to version 23.

    - Migrates the settings entries 'thousand_separator', 'decimal_separator'
    and 'currency_location' into the 'frontend_settings' entry.
    - Deletes Bitfinex trades and their used query range, so trades can be
    populated again with the right `fee_asset`.
    - Deletes deprecated historical_data_start (this DB should not have it)
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v22_rotkehlchen_w_frontend_settings.db')
    db_v22 = _init_db_with_target_version(
        target_version=22,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db_v22.conn.cursor()

    # Check all settings exist
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name = "frontend_settings";',
    ).fetchone()[0] == 1
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name = "historical_data_start";',
    ).fetchone()[0] == 0
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name IN '
        '("thousand_separator", "decimal_separator", "currency_location");',
    ).fetchone()[0] == 3

    # Check Bitfinex trades and their used query range exist
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name = "bitfinex_trades";',
    ).fetchone()[0] == 1
    assert cursor.execute(
        'SELECT COUNT(*) from trades WHERE location = "T";',
    ).fetchone()[0] == 2

    # Migrate to v23
    db = _init_db_with_target_version(
        target_version=23,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    # Make sure the settings have been removed
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name IN '
        '("thousand_separator", "decimal_separator", "currency_location");',
    ).fetchone()[0] == 0

    # Make sure the settings have been migrated into 'frontend_settings'
    frontend_settings = cursor.execute(
        'SELECT value FROM settings WHERE name = "frontend_settings";',
    ).fetchone()[0]
    frontend_settings_map = json.loads(frontend_settings)
    assert frontend_settings_map['thousand_separator'] == ','
    assert frontend_settings_map['decimal_separator'] == '.'
    assert frontend_settings_map['currency_location'] == 'after'

    # Make sure deprecated historical_data_start is removed
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name = "historical_data_start";',
    ).fetchone()[0] == 0

    # Make sure Bitfinex trades used query range has been deleted
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name = "bitfinex_trades";',
    ).fetchone()[0] == 0

    # Make sure Bitfinex trades have been deleted
    assert cursor.execute(
        'SELECT COUNT(*) from trades WHERE location = "T";',
    ).fetchone()[0] == 0

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 23


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_22_to_23_without_frontend_settings(data_dir, user_data_dir):
    """Test upgrading the DB from version 22 to version 23.

    Tests the case where frontend settings were not populated and also the cache
    file movement and deletion. Also test deleletion of deprecated historical_data_start
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v22_rotkehlchen_wo_frontend_settings.db')
    db_v22 = _init_db_with_target_version(
        target_version=22,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db_v22.conn.cursor()

    # Create cache files under the data directory
    (data_dir / 'price_history_forex.json').touch()  # we botched this (check upgrade function)
    (data_dir / 'price_history_BTC_EUR.json').touch()
    (data_dir / 'price_history_aDAI_USD.json').touch()
    (data_dir / 'price_history_YFI_USD.json').touch()
    # Also create an innocent json file and a random file
    (data_dir / 'random.json').touch()
    (data_dir / 'random.txt').touch()
    # Check all settings except 'frontend_settings' exist
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name = "frontend_settings";',
    ).fetchone()[0] == 0
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name IN '
        '("thousand_separator", "decimal_separator", "currency_location");',
    ).fetchone()[0] == 3
    # Check we got a historical data start entry to remove
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name = "historical_data_start";',
    ).fetchone()[0] == 1

    # Migrate to v23
    db = _init_db_with_target_version(
        target_version=23,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    # Make sure the settings have been removed
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name IN '
        '("thousand_separator", "decimal_separator", "currency_location");',
    ).fetchone()[0] == 0
    assert cursor.execute(
        'SELECT COUNT(*) FROM settings WHERE name = "historical_data_start";',
    ).fetchone()[0] == 0

    # Make sure the settings have been migrated into 'frontend_settings'
    frontend_settings = cursor.execute(
        'SELECT value FROM settings WHERE name = "frontend_settings";',
    ).fetchone()[0]
    frontend_settings_map = json.loads(frontend_settings)
    assert frontend_settings_map['thousand_separator'] == ','
    assert frontend_settings_map['decimal_separator'] == '.'
    assert frontend_settings_map['currency_location'] == 'after'

    # Assure the cache files were deleted
    assert not (data_dir / 'price_history_BTC_EUR.json').is_file()
    assert not (data_dir / 'price_history_aDAI_USD.json').is_file()
    assert not (data_dir / 'price_history_YFI_USD.json').is_file()
    # and that the forex history cache file moved. The problem here is that
    # the DB upgrade botched this file movement. Should have been price_history_forex.json
    # but ended up moving it with the wrong name. So here we just check the wrong
    # name. Just to satisfy the test
    assert (data_dir / 'price_history' / 'forex_history_file.json').is_file()
    # and that the other files were not touched
    assert (data_dir / 'random.json').is_file()
    assert (data_dir / 'random.txt').is_file()

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 23


def test_upgrade_db_23_to_24(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 23 to version 24.

    Deletes the AdEx used query ranges, drops the AdEx events table and re-creates it.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v23_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=23,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    # Checks before migration
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "adex_events%";',
    ).fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from adex_events;').fetchone()[0] == 1

    # Migrate to v24
    db = _init_db_with_target_version(
        target_version=24,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    # Make sure AdEx used query ranges have been deleted
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "adex_events%";',
    ).fetchone()[0] == 0

    # Make sure `adex_events` has been successfully created. All columns have
    # been selected for double-checking the new schema
    query = cursor.execute(
        'SELECT '
        'tx_hash, '
        'address, '
        'identity_address, '
        'timestamp, '
        'type, '
        'pool_id, '
        'amount, '
        'usd_value, '
        'bond_id, '
        'nonce, '
        'slashed_at, '
        'unlock_at, '
        'channel_id, '
        'token, '
        'log_index from adex_events;',
    )
    assert len(query.fetchall()) == 0

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 24


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


def test_upgrades_list_is_sane():
    idx = None
    for idx, entry in enumerate(UPGRADES_LIST):
        msg = (
            f'{idx} upgrade record was expected to have {idx + 1} '
            f'from_version but has {entry.from_version}'
        )
        assert entry.from_version == idx + 1, msg
    assert idx + 2 == ROTKEHLCHEN_DB_VERSION, 'the final version + 1 should be current version'
