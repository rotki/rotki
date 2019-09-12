from sqlite3 import Cursor
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.old_create import OLD_DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.utils import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.tests.utils.constants import A_BCH, A_BSV, A_RDN
from rotkehlchen.typing import FilePath, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator

creation_patch = patch(
    'rotkehlchen.db.dbhandler.DB_SCRIPT_CREATE_TABLES',
    new=OLD_DB_SCRIPT_CREATE_TABLES,
)


def populate_db_and_check_for_asset_renaming(
        cursor: Cursor,
        data: DataHandler,
        data_dir: FilePath,
        msg_aggregator: MessagesAggregator,
        username: str,
        to_rename_asset: str,
        renamed_asset: Asset,
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
    data.unlock(username, '123', create_new=False)
    # Check that owned and ignored assets reflect the new state
    ignored_assets = data.db.get_ignored_assets()
    assert A_RDN in ignored_assets
    assert renamed_asset in ignored_assets
    owned_assets = data.db.query_owned_assets()
    assert A_ETH in owned_assets
    assert renamed_asset in owned_assets

    # Make sure that the merging of both new and old name entry in same timestamp works
    timed_balances = data.db.query_timed_balances(from_ts=0, to_ts=2556392121, asset=renamed_asset)
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

    assert data.db.get_version() == ROTKEHLCHEN_DB_VERSION


def test_upgrade_db_1_to_2(data_dir, username):
    """Test upgrading the DB from version 1 to version 2, which means that
    ethereum accounts are now checksummed"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch:
        data.unlock(username, '123', create_new=True)
    # Manually set version and input a non checksummed account
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(1)),
    )
    data.db.conn.commit()
    data.db.add_blockchain_account(
        SupportedBlockchain.ETHEREUM,
        '0xe3580c38b0106899f45845e361ea7f8a0062ef12',
    )

    # now relogin and check that the account has been re-saved as checksummed
    del data
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=False)
    accounts = data.db.get_blockchain_accounts()
    assert accounts.eth[0] == '0xe3580C38B0106899F45845E361EA7F8a0062Ef12'
    version = data.db.get_version()
    assert version == ROTKEHLCHEN_DB_VERSION
    # Also make sure that we have updated the latest DB version constant
    assert version > 1


def test_upgrade_db_2_to_3(data_dir, username):
    """Test upgrading the DB from version 2 to version 3, rename BCHSV to BSV"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch:
        data.unlock(username, '123', create_new=True)
    # Manually set version
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
    )
    version = data.db.get_version()
    # Also make sure that we have updated the latest DB version constant
    assert version > 2


def test_upgrade_db_3_to_4(data_dir, username):
    """Test upgrading the DB from version 3 to version 4, which means that
    the eth_rpc_port setting is changed to eth_rpc_endpoint"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch:
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
    data.unlock(username, '123', create_new=False)
    cursor = data.db.conn.cursor()
    query = cursor.execute('SELECT value FROM settings where name="eth_rpc_endpoint";')
    query = query.fetchall()
    assert query[0][0] == 'http://localhost:8585'
    query = cursor.execute('SELECT value FROM settings where name="eth_rpc_port";')
    query = query.fetchall()
    assert len(query) == 0
    version = data.db.get_version()
    assert version == ROTKEHLCHEN_DB_VERSION
    # Also make sure that we have updated the latest DB version constant
    assert version > 3


def test_upgrade_db_4_to_5(data_dir, username):
    """Test upgrading the DB from version 4 to version 5, rename BCC to BCH"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch:
        data.unlock(username, '123', create_new=True)
    # Manually set version
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
    )
    # Also make sure that we have updated the latest DB version constant
    assert data.db.get_version() > 4


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
