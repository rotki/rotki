import json
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from shutil import copyfile
from unittest.mock import patch

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures import BalanceType
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.typing import AssetType
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
from rotkehlchen.tests.utils.database import (
    mock_dbhandler_add_globaldb_assetids,
    mock_dbhandler_ensura_data_integrity,
    mock_dbhandler_update_owned_assets,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress
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
    with ExitStack() as stack:
        stack.enter_context(target_patch(target_version=target_version))
        if target_version <= 24:
            stack.enter_context(mock_dbhandler_update_owned_assets())
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


def _init_prepared_db(user_data_dir: Path, filename: str):
    _use_prepared_db(user_data_dir, filename)
    password = '123'
    conn = sqlcipher.connect(str(user_data_dir / 'rotkehlchen.db'))  # pylint: disable=no-member
    conn.executescript(f'PRAGMA key={password};')
    conn.execute('PRAGMA foreign_keys=ON;')
    return conn


def populate_db_and_check_for_asset_renaming(
        db: DBHandler,
        user_data_dir: Path,
        msg_aggregator: MessagesAggregator,
        to_rename_asset: str,
        renamed_asset: str,
        target_version: int,
):
    # Manually input data to the affected tables.
    # timed_balances, multisettings and (external) trades
    cursor = db.conn.cursor()

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
        ('1558499129', renamed_asset, '2.2', '25'),
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
    db.conn.commit()

    # now relogin and check that all tables have appropriate data
    with mock_dbhandler_update_owned_assets(), creation_patch:
        new_db = _init_db_with_target_version(
            target_version=target_version,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
        )

    cursor = new_db.conn.cursor()
    # Check that owned and ignored assets reflect the new state
    query = cursor.execute(
        'SELECT value FROM multisettings WHERE name="ignored_asset";',
    )
    ignored_assets = [q[0] for q in query]
    assert 'RDN' in ignored_assets
    assert renamed_asset in ignored_assets
    results = cursor.execute(
        'SELECT DISTINCT currency FROM timed_balances ORDER BY time ASC;',
    )
    owned_assets = set()
    for result in results:
        owned_assets.add(result[0])
    assert 'ETH' in owned_assets
    assert renamed_asset in owned_assets

    # Make sure that the merging of both new and old name entry in same timestamp works
    querystr = (
        f'SELECT time, amount, usd_value FROM timed_balances WHERE time BETWEEN '
        f'0 AND 2556392121 AND currency="{renamed_asset}" ORDER BY time ASC;'
    )
    cursor = new_db.conn.cursor()
    result = cursor.execute(querystr).fetchall()
    assert len(result) == 2
    assert result[0][0] == 1557499129
    assert result[0][1] == '10.1'
    assert result[0][2] == '150'
    assert result[1][0] == 1558499129
    assert result[1][1] == '3.3'
    assert result[1][2] == '40'

    # Assert that trades got renamed properly
    cursor = new_db.conn.cursor()
    querystr = (
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
    results = cursor.execute(querystr)
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
    assert trades[1]['fee_currency'] == renamed_asset
    assert trades[1]['pair'] == f'{renamed_asset}_EUR'
    assert trades[2]['pair'] == f'{renamed_asset}_EUR'

    assert new_db.get_version() == target_version
    with mock_dbhandler_update_owned_assets():
        del new_db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_db_1_to_2(data_dir, username):
    """Test upgrading the DB from version 1 to version 2, which means that
    ethereum accounts are now checksummed"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch, target_patch(1), mock_dbhandler_update_owned_assets(), mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
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
    with mock_dbhandler_update_owned_assets():
        del data
        data = DataHandler(data_dir, msg_aggregator)
        with target_patch(target_version=2):
            data.unlock(username, '123', create_new=False)
    accounts = data.db.get_blockchain_accounts()
    assert accounts.eth[0] == '0xe3580C38B0106899F45845E361EA7F8a0062Ef12'
    version = data.db.get_version()
    # Also make sure that we have updated to the target_version
    assert version == 2
    with mock_dbhandler_update_owned_assets():
        del data.db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_db_2_to_3(user_data_dir):
    """Test upgrading the DB from version 2 to version 3, rename BCHSV to BSV"""
    msg_aggregator = MessagesAggregator()
    with creation_patch, mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
        db = _init_db_with_target_version(
            target_version=2,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
        )

    with mock_dbhandler_update_owned_assets(), mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
        populate_db_and_check_for_asset_renaming(
            db=db,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
            to_rename_asset='BCHSV',
            renamed_asset='BSV',
            target_version=3,
        )
        del db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_db_3_to_4(data_dir, username):
    """Test upgrading the DB from version 3 to version 4, which means that
    the eth_rpc_port setting is changed to eth_rpc_endpoint"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    with creation_patch, target_patch(3), mock_dbhandler_update_owned_assets(), mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
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
    with mock_dbhandler_update_owned_assets(), mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
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
    with mock_dbhandler_update_owned_assets():
        del data.db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_db_4_to_5(user_data_dir):
    """Test upgrading the DB from version 4 to version 5, rename BCC to BCH"""
    msg_aggregator = MessagesAggregator()
    with creation_patch, mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
        db = _init_db_with_target_version(
            target_version=4,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
        )

    with mock_dbhandler_update_owned_assets(), mock_dbhandler_add_globaldb_assetids(), mock_dbhandler_ensura_data_integrity():  # noqa: E501
        populate_db_and_check_for_asset_renaming(
            db=db,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
            to_rename_asset='BCC',
            renamed_asset='BCH',
            target_version=5,
        )
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_broken_db_7_to_8(user_data_dir):
    """Test that if SAI is already in owned tokens upgrade fails"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v7_rotkehlchen_broken.db')
    with mock_dbhandler_update_owned_assets(), pytest.raises(DBUpgradeError):
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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_db_11_to_12(user_data_dir):
    """Test upgrading the DB from version 11 to version 12.

    Deleting all bittrex data from the DB"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v11_rotkehlchen.db')
    with mock_dbhandler_ensura_data_integrity():
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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db, db_v22  # explicit delete the db so update_owned_assets still runs mocked


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
    with mock_dbhandler_update_owned_assets():
        del db, db_v22  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_db_23_to_24(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 23 to version 24.

    Deletes the AdEx used query ranges, drops the AdEx events table and re-creates it.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v23_rotkehlchen.db')
    db_v23 = _init_db_with_target_version(
        target_version=23,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db_v23.conn.cursor()

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
    with mock_dbhandler_update_owned_assets():
        del db, db_v23  # explicit delete the db so update_owned_assets still runs mocked


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_24_to_25(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 24 to version 25.

    - deletes the icon cache of all icons (they will be repulled with new ids)
    - Upgrades to the new eth token identifier schema
    - trade pairs are now replaced by base/quote asset
    - purges some tables
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v24_rotkehlchen.db')
    with mock_dbhandler_ensura_data_integrity():
        db_v24 = _init_db_with_target_version(
            target_version=24,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
        )
    # copy some test icons in the test directory
    icons_dir = user_data_dir.parent / 'icons'
    custom_icons_dir = icons_dir / 'custom'
    custom_icons_dir.mkdir(parents=True, exist_ok=True)
    test_icondata_dir = Path(os.path.realpath(__file__)).parent.parent / 'data' / 'icons'
    custom_icon_filename = '_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94.webp'
    copyfile(test_icondata_dir / custom_icon_filename, custom_icons_dir / custom_icon_filename)
    for size in ('small', 'thumb', 'large'):
        name = f'USDT_{size}.png'
        copyfile(test_icondata_dir / name, icons_dir / name)
    icon_files = list(icons_dir.glob('*.*'))
    assert len(icon_files) == 3
    # create some fake history cache files
    price_history_dir = user_data_dir.parent / 'price_history'
    price_history_dir.mkdir(parents=True, exist_ok=True)
    history_cache_files = [
        price_history_dir / 'cc_price_history_BTC_EUR.json',
        price_history_dir / 'price_history_forex.json',
        price_history_dir / 'gecko_price_history_XMR_USD.json',
    ]
    for price_file in history_cache_files:
        price_file.touch(mode=0o666, exist_ok=True)
        assert price_file.is_file()

    cursor = db_v24.conn.cursor()
    # Checks before migration
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "uniswap%";',
    ).fetchone()[0] == 4
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from uniswap_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from balancer_pools;').fetchone()[0] == 1
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "balancer_events%";',
    ).fetchone()[0] == 1
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "balancer_trades%";',
    ).fetchone()[0] == 3
    assert cursor.execute('SELECT COUNT(*) from yearn_vaults_events;').fetchone()[0] == 1
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "yearn_vaults_events%";',
    ).fetchone()[0] == 24
    assert cursor.execute('SELECT COUNT(*) from ethereum_accounts_details;').fetchone()[0] == 3
    # coinbase/coinbasepro exchange data purging
    assert cursor.execute('SELECT COUNT(*) from trades where location IN ("G", "K");').fetchone()[0] == 2  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) from asset_movements where location IN ("G", "K");').fetchone()[0] == 2  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges where name LIKE "coinbase%";').fetchone()[0] == 6  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) from adex_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges WHERE name LIKE "adex_events%";').fetchone()[0] == 1  # noqa: E501
    trades_count = cursor.execute('SELECT COUNT(*) from trades;').fetchone()[0]
    assert trades_count == 18
    trades_query = cursor.execute(
        'SELECT id, time, location, pair, type, amount, rate, fee,'
        'fee_currency, link, notes from trades ORDER BY time ASC;',
    ).fetchall()
    assert trades_query == [
        ('foo1', 1, 'G', 'ETH_BTC', 'A', '1', '1', '1', 'ETH', '', ''),
        ('foo2', 1, 'K', 'ETH_BTC', 'A', '1', '1', '1', 'ETH', '', ''),
        ('5a12acc85a2787a982f4fa4861103c8dd2fd4fb3e4535648894f46da4a5d0f6a', 1493227049, 'D', 'SWT_BTC', 'A', '867.46673624', '0.00114990', '0.00249374', 'BTC', 'l1', ''),  # noqa: E501
        ('87fae909392162febb703010ceb00e1d23e998ddc02a524d477d0e4bbb81d62c', 1493228252, 'D', 'EDG_BTC', 'A', '11348.12286689', '0.00008790', '0.00249374', 'BTC', 'l2', ''),  # noqa: E501
        ('8ad65d14ae4781afa03adcd0452bd7b0c3ded70821c2fa66fc3818fc8c708e6e', 1498949799, 'D', 'SWT_BTC', 'A', '150.00000000', '0.00091705', '0.00034389', 'BTC', 'l3', ''),  # noqa: E501
        ('aee370e00bdaf393012895acdd0663f10375d2508deb8e214ca9fd7bb71879ed', 1498966605, 'D', 'SWT_BTC', 'A', '1000.00000000', '0.00091409', '0.00228521', 'BTC', 'l4', ''),  # noqa: E501
        ('ae8660dfd750a68792057b1b075c2d075550ea1bf47f8fd58d6d981252ae8cad', 1499011364, 'D', 'SWT_BTC', 'A', '200.00000000', '0.00092401', '0.00046200', 'BTC', 'l5', ''),  # noqa: E501
        ('2de3e2216c4887398a72435ac48db06c3ce36866cb15165e700f180c3d80f124', 1499051024, 'D', 'SWT_BTC', 'A', '120.00000000', '0.00091603', '0.00027480', 'BTC', 'l6', ''),  # noqa: E501
        ('13b54258a2c089ff47f1116769b5ff6a9e10f182e4a38703b9c1247a4bc63024', 1499675187, 'D', 'SWT_BTC', 'A', '200.00000000', '0.00091747', '0.00045869', 'BTC', 'l7', ''),  # noqa: E501
        ('3079ce93914cbab9e2e812932af84fde4cc4a60fec258ec34a214f869f80071a', 1499677638, 'D', 'SWT_BTC', 'A', '1135.00000000', '0.00088101', '0.00249985', 'BTC', 'l8', ''),  # noqa: E501
        ('c45b5255b5cf099d9ea60a889ea01b7dc9ff520d82465125b4f362761288de15', 1500494329, 'D', 'EDG_BTC', 'B', '10490.34064784', '0.00024385', '0.00639521', 'BTC', 'l9', ''),  # noqa: E501
        ('44156083e0f00c780e2375ea73d1123fa6a06b778113c6a0ea2548570d41e62e', 1500501003, 'D', 'EDG_BTC', 'B', '857.78221905', '0.00018099', '0.00038812', 'BTC', 'l10', ''),  # noqa: E501
        ('5c41cbce8b992585e88c2980ab6640d31a6c75fbf8ff9bb9f2f72d27862f7536', 1501194075, 'D', 'SWT_BTC', 'A', '510.21713000', '0.00039101', '0.00049875', 'BTC', 'l11', ''),  # noqa: E501
        ('90c6101f4991732d93f518f580f7e8442e82d9edf6059bc661b0aec0b813d666', 1501585385, 'D', 'SWT_BTC', 'A', '731.28354007', '0.00034101', '0.00062343', 'BTC', 'l12', ''),  # noqa: E501
        ('306e28a5314355ca533a9ebb3b4ba20aabbe81ad698af0be02119af436f88a18', 1599751485, 'A', 'ETH_EUR', 'A', '150', '210.15', '0.2', 'EUR', '', ''),  # noqa: E501
        ('94bf5ad1c9b73b1c35e92e49cb3296256a81b5ba387aa774710b8a6346fddfef', 1607172606, 'D', 'MAID_BTC', 'B', '15515.00000000', '0.00001299', '0.00040305', 'BTC', 'l13', ''),  # noqa: E501
        ('493138ad2eadc0ead06aad345f8f4bdf196e44e34a71ad8a6e8fb5ad14d644ae', 1610915040, 'A', 'ETH_EUR', 'A', '5', '0.1', '0.001', '1INCH', 'dsad', 'ads'),  # noqa: E501
        ('f96d90c8179b502fa1f67ed2829fbbcc5e8dfac0b5873188ee5f753473bf7384', 1612302374, 'A', 'UNI_ETH', 'A', '1', '0.01241', '0', 'UNI', '', ''),  # noqa: E501
    ]
    assert cursor.execute('SELECT COUNT(*) from timed_balances;').fetchone()[0] == 392
    query = cursor.execute('SELECT id, location, open_time, close_time, profit_loss, pl_currency, fee, fee_currency, link, notes from margin_positions;')  # noqa: E501
    assert query.fetchall() == [
        ("foo1", "C", 1, 5, "500", "ETH", "1", "GNO", "", ""),
        ("foo2", "A", 1, 5, "1", "BTC", "1", "RDN", "", ""),
        ("foo3", "A", 0, 5, "1", "YFI", "1", "DPI", "", ""),
    ]
    query = cursor.execute('SELECT asset, label, amount, location from manually_tracked_balances;')  # noqa: E501
    assert query.fetchall() == [
        ('EUR', 'test eur balance', '1', 'A'),
        ('USD', 'test usd balance', '1', 'A'),
        ('CNY', 'test CNY balance', '1', 'A'),
        ('AKRO', 'exotic asset', '1500', 'A'),
        ('1INCH', 'test for duplication', '100000', 'J'),
        ('_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94', 'test custom token balance', '65', 'A'),  # noqa: E501
        ('FTT-2', 'test_asset_with_same_symbol', '85', 'A'),
        ('_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e', 'test_custom_token', '25', 'A'),
    ]
    query = cursor.execute('SELECT id, location, category, address, transaction_id, time, asset, amount, fee_asset, fee, link from asset_movements;')  # noqa: E501
    assert query.fetchall() == [
        ('a5444b4263b72e86b6de724631346c8c89b6b44a46f10c882b4e9a15a5fdde13', 'D', 'A', '0xaddress', '0xtxid', 1577666912, 'MAID', '15515.00000000', 'MAID', '0', 'link1'),  # noqa: E501
        ('48aa7e2ce1c16fa1094f0577a52f81a120ab1bb68eaf1d9da5bf6aafe63e4ac2', 'D', 'A', '0xaddress', '0xtxid', 1498941726, 'BTC', '4.20000000', 'BTC', '0', 'link2'),  # noqa: E501
        ('f2847295c8d236d46242c6868f1da91ee83bb2a71e56134bd793872ebb9f4a0d', 'D', 'A', '0xaddress', '0xtxid', 1493226738, 'BTC', '2.00000000', 'BTC', '0', 'link3'),  # noqa: E501
        ('f91fa46f5b7f8d7b3581d8be61d1243050af6ab8fa8aba0c36557ee13a2a4fe7', 'D', 'B', '0xaddress', '0xtxid', 1607094370, 'SWT', '4753.96740631', 'SWT', '160.00000000', 'link4'),  # noqa: E501
        ('dbb994c9e36b1b00bcfc70876ce6f429fe1229d3c44beccd7d3f4194a994491b', 'D', 'B', '0xaddress', '0xtxid', 1501161076, 'BTC', '3.91944853', 'BTC', '0.00100000', 'link5'),  # noqa: E501
        ('boo1', 'G', 'A', '', '', 1, 'BTC', '1', 'BTC', '1', ''),
        ('boo2', 'K', 'A', '', '', 1, 'BTC', '1', 'BTC', '1', ''),
        ('foo1', 'L', 'B', '0xaddy', '0xtxid', 1, 'YFI', '1', 'GNO', '1', 'customlink'),
    ]
    asset_movements_count = cursor.execute('SELECT COUNT(*) from asset_movements;').fetchone()[0]
    query = cursor.execute('SELECT identifier, timestamp, type, location, amount, asset, link, notes from ledger_actions;')  # noqa: E501
    assert query.fetchall() == [
        (1, 1611260690, 'A', 'A', '1', 'ABYSS', '', ''),
        (2, 1610483475, 'A', 'A', '1', '0xBTC', 'sad', 'asdsad'),
    ]
    query = cursor.execute('SELECT name, value from multisettings;')
    assert query.fetchall() == [
        ('ignored_asset', 'DAO'),
        ('ignored_asset', 'OMG'),
        ('ignored_asset', 'XMR'),
        ('queried_address_makerdao_vaults', '0x7e57fBBb05A0557c133bAcB8a66a1955F0D66B1D'),
        ('queried_address_aave', '0x7e57fBBb05A0557c133bAcB8a66a1955F0D66B1D'),
    ]

    with mock_dbhandler_update_owned_assets():
        del db_v24  # explicit delete the db so update_owned_assets still runs mocked
    # Migrate to v25
    db = _init_db_with_target_version(
        target_version=25,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    # check that all tables that should have been purged/cleaned, were done so
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "uniswap%";',
    ).fetchone()[0] == 0
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "balancer_events%";',
    ).fetchone()[0] == 0
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "balancer_trades%";',
    ).fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from uniswap_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from balancer_pools;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from yearn_vaults_events;').fetchone()[0] == 0
    assert cursor.execute(
        'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE "yearn_vaults_events%";',
    ).fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from ethereum_accounts_details;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from trades where location IN ("G", "K");').fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) from asset_movements where location IN ("G", "K");').fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges where name LIKE "coinbase%";').fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) from adex_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges WHERE name LIKE "adex_events%";').fetchone()[0] == 0  # noqa: E501
    new_trades_count = cursor.execute('SELECT COUNT(*) from trades;').fetchone()[0]
    assert new_trades_count == trades_count - 2, 'all but the coinbase/pro trades should be there'
    assert cursor.execute('SELECT COUNT(*) from timed_balances;').fetchone()[0] == 392

    # check the ledger actions were upgraded
    query = cursor.execute('SELECT identifier, timestamp, type, location, amount, asset, rate, rate_asset, link, notes from ledger_actions;')  # noqa: E501
    assert query.fetchall() == [
        (1, 1611260690, 'A', 'A', '1', '_ceth_0x0E8d6b471e332F140e7d9dbB99E5E3822F728DA6', None, None, None, None),  # noqa: E501
        (2, 1610483475, 'A', 'A', '1', '_ceth_0xB6eD7644C69416d67B522e20bC294A9a9B405B31', None, None, 'sad', 'asdsad'),  # noqa: E501
    ]
    # check that margin positions were upgraded
    query = cursor.execute('SELECT id, location, open_time, close_time, profit_loss, pl_currency, fee, fee_currency, link, notes from margin_positions;')  # noqa: E501
    raw_upgraded = query.fetchall()
    assert raw_upgraded == [
        ("3ebd1ff33f6b6431778db56393e6105b94b0b23d0976462d70279e6f82db9924", "C", 1, 5, "500", "ETH", "1", "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96", "", ""),  # noqa: E501
        ("2ecdf50622f0ad6277b2c4b28954118753db195c9ae2005ce7da7b30d4a873c4", "A", 1, 5, "1", "BTC", "1", "_ceth_0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6", "", ""),  # noqa: E501
        ("bec34827cd9ce879e91d45dfe11942752f810504439701ff7f3d005850f458a8", "A", 0, 5, "1", "_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e", "1", "_ceth_0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b", "", ""),  # noqa: E501
    ]
    # Check that identifiers match with what is expected. This may need amendment if the upgrade test stays around while the code changes.  # noqa: E501
    margins = db.get_margin_positions()
    assert all(x.identifier == raw_upgraded[idx][0] for idx, x in enumerate(margins))

    # check that the asset movements were upgraded
    query = cursor.execute('SELECT id, location, category, address, transaction_id, time, asset, amount, fee_asset, fee, link from asset_movements ORDER BY time ASC;')  # noqa: E501
    raw_upgraded = query.fetchall()
    assert raw_upgraded == [
        ('822511b6035c5d2a7a7ff82c21b61381016e76764e84f656aedcfbc3b7a2e2f4', 'L', 'B', '0xaddy', '0xtxid', 1, '_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', '1', '_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96', '1', 'customlink'),  # noqa: E501
        ('98c8378892955d3c95cc24277188ad33504d2e668441ba23a270b6c65f00be43', 'D', 'A', '0xaddress', '0xtxid', 1493226738, 'BTC', '2.00000000', 'BTC', '0', 'link3'),  # noqa: E501
        ('9713d2c2f90edfc375bfea1d014599e9f3a20eded94625c0a2483c4ab2692ff9', 'D', 'A', '0xaddress', '0xtxid', 1498941726, 'BTC', '4.20000000', 'BTC', '0', 'link2'),  # noqa: E501
        ('86f6cda4bcd36e2fd0e8938fd3b31ebe895af2df6d8b60479c401cd846a3ccf8', 'D', 'B', '0xaddress', '0xtxid', 1501161076, 'BTC', '3.91944853', 'BTC', '0.00100000', 'link5'),  # noqa: E501
        ('9a3ab62aea2892e9000c868ce29a471e34f57d3bbae7691b920bcf58fbea10ce', 'D', 'A', '0xaddress', '0xtxid', 1577666912, 'MAID', '15515.00000000', 'MAID', '0', 'link1'),  # noqa: E501
        ('79d6d91d1fd2acf02a9d244e33ff340c04a938faaf0d1ba10aba9d8ae55b11cc', 'D', 'B', '0xaddress', '0xtxid', 1607094370, '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', '4753.96740631', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', '160.00000000', 'link4'),  # noqa: E501
    ]
    assert len(raw_upgraded) == asset_movements_count - 2, 'coinbase/pro movements should have been deleted'  # noqa: E501
    # Check that identifiers match with what is expected. This may need amendment if the upgrade test stays around while the code changes.  # noqa: E501
    movements = db.get_asset_movements()
    assert all(x.identifier == raw_upgraded[idx][0] for idx, x in enumerate(movements))

    # check that the timed balances had the currency properly changed
    query = cursor.execute('SELECT category, time, currency, amount, usd_value from timed_balances;')  # noqa: E501
    for idx, entry in enumerate(query):
        # the test DB also has some custom tokens which are not in the globalDB as of this writing
        # 1st one is random fake address, 2nd one is vBNT
        if entry[2] in ('_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e', '_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94'):  # noqa: E501
            continue

        # make sure the asset is understood
        _ = Asset(entry[2])
        # check some specific entries are converted properly
        if idx == 391:
            assert entry == (
                'A',
                1616766011,
                '_ceth_0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9',
                '85',
                '2909.55',
            )
        elif idx == 387:
            assert entry == (
                'A',
                1616766011,
                '_ceth_0x8Ab7404063Ec4DBcfd4598215992DC3F8EC853d7',
                '1500',
                '76.986000',
            )
        elif idx == 369:
            assert entry == (
                'A',
                1616593325,
                '_ceth_0xc00e94Cb662C3520282E6f5717214004A7f26888',
                '0.001948068074186848',
                '0.75082439715309495616',
            )
        elif idx == 2:
            assert entry == (
                'A',
                1610559319,
                '_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F',
                '90.5639',
                '90.54578722',
            )
        elif idx == 1:
            assert entry == (
                'A',
                1610559319,
                '_ceth_0x4DC3643DbC642b72C158E7F3d2ff232df61cb6CE',
                '0.1',
                '0.001504',
            )

    # test the manually tracked balances were upgraded
    query = cursor.execute('SELECT asset, label, amount, location from manually_tracked_balances;')  # noqa: E501
    assert query.fetchall() == [
        ('EUR', 'test eur balance', '1', 'A'),
        ('USD', 'test usd balance', '1', 'A'),
        ('CNY', 'test CNY balance', '1', 'A'),
        ('_ceth_0x8Ab7404063Ec4DBcfd4598215992DC3F8EC853d7', 'exotic asset', '1500', 'A'),
        ('_ceth_0x111111111117dC0aa78b770fA6A738034120C302', 'test for duplication', '100000', 'J'),  # noqa: E501
        ('_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94', 'test custom token balance', '65', 'A'),  # noqa: E501
        ('_ceth_0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9', 'test_asset_with_same_symbol', '85', 'A'),  # noqa: E501
        ('_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e', 'test_custom_token', '25', 'A'),
    ]

    # test that the ignored assets were properly upgraded
    query = cursor.execute('SELECT name, value from multisettings;')
    assert query.fetchall() == [
        ('ignored_asset', '_ceth_0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413'),
        ('ignored_asset', '_ceth_0xd26114cd6EE289AccF82350c8d8487fedB8A0C07'),
        ('ignored_asset', 'XMR'),
        ('queried_address_makerdao_vaults', '0x7e57fBBb05A0557c133bAcB8a66a1955F0D66B1D'),
        ('queried_address_aave', '0x7e57fBBb05A0557c133bAcB8a66a1955F0D66B1D'),
    ]

    # test that the trades were properly upgraded
    trades_query = cursor.execute(
        'SELECT id, time, location, base_asset, quote_asset, type, amount, rate, fee,'
        'fee_currency, link, notes from trades ORDER BY time ASC;',
    ).fetchall()
    assert trades_query == [
        ('fac279d109466a908119816d2ee7af90fba28f1ae60437bcbfab10e40a62bbc7', 1493227049, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '867.46673624', '0.00114990', '0.00249374', 'BTC', 'l1', None),  # noqa: E501
        ('56775b4b80f46d1dfc1b53fc0f6b61573c14142499bfe3a62e3371f7afc166db', 1493228252, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'A', '11348.12286689', '0.00008790', '0.00249374', 'BTC', 'l2', None),  # noqa: E501
        ('d38687c92fd4b56f7241b38653390a72022709ef8835c289f6d49cc436b8e05a', 1498949799, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '150.00000000', '0.00091705', '0.00034389', 'BTC', 'l3', None),  # noqa: E501
        ('cc31283b6e723f4a7364496b349869564b06b4320da3a14d95dcda1801369361', 1498966605, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '1000.00000000', '0.00091409', '0.00228521', 'BTC', 'l4', None),  # noqa: E501
        ('c76a42bc8b32407b7444da89cc9f73c22fd6a1bc0055b7d4112e3e59709b2b5b', 1499011364, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '200.00000000', '0.00092401', '0.00046200', 'BTC', 'l5', None),  # noqa: E501
        ('18810df423b24bb438360b23b50bd0fc11ed2d3701420651ef716f4840367894', 1499051024, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '120.00000000', '0.00091603', '0.00027480', 'BTC', 'l6', None),  # noqa: E501
        ('27bb15dfc1a008c2efa2c5510b30808d8246ab903cf9f950ea7a175f0779925d', 1499675187, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '200.00000000', '0.00091747', '0.00045869', 'BTC', 'l7', None),  # noqa: E501
        ('b0c4d1d816fa3448ba1ab1a285a35d71a42ff27d68438626eacecc4bf927ab07', 1499677638, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '1135.00000000', '0.00088101', '0.00249985', 'BTC', 'l8', None),  # noqa: E501
        ('6b91fc81d40c121af7397c5f3351547de4bd3f288fe483ace14b7b7922cfcd36', 1500494329, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'B', '10490.34064784', '0.00024385', '0.00639521', 'BTC', 'l9', None),  # noqa: E501
        ('59ea4f98a815467122d201d737b97f910c8918cfe8f476a74d51a4006ef1aaa8', 1500501003, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'B', '857.78221905', '0.00018099', '0.00038812', 'BTC', 'l10', None),  # noqa: E501
        ('dc4a8a1dd3ef78b6eae5ee69f24bed73196ba3677150015f80d28a70b963253c', 1501194075, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '510.21713000', '0.00039101', '0.00049875', 'BTC', 'l11', None),  # noqa: E501
        ('8ba98869f1398d9d64d974a13bc1e686746c7068b765223a46f886ef9c100722', 1501585385, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '731.28354007', '0.00034101', '0.00062343', 'BTC', 'l12', None),  # noqa: E501
        ('6f583c1297a86beadb46e8876db9589bb2ca60c603a4eca77b331611a49cd482', 1599751485, 'A', 'ETH', 'EUR', 'A', '150', '210.15', '0.2', 'EUR', None, None),  # noqa: E501
        ('3fc94b6b91de61d98b21bdba9a6e449b3ff25756f34a14d17dcf3979d08c4ee3', 1607172606, 'D', 'MAID', 'BTC', 'B', '15515.00000000', '0.00001299', '0.00040305', 'BTC', 'l13', None),  # noqa: E501
        ('ecd64dba4367a42292988abb34ed46b3dda0d48728c629f9727706d198023d6c', 1610915040, 'A', 'ETH', 'EUR', 'A', '5', '0.1', '0.001', '_ceth_0x111111111117dC0aa78b770fA6A738034120C302', 'dsad', 'ads'),  # noqa: E501c
        ('7aae102d9240f7d5f7f0669d6eefb47f2d1cf5bba462b0cee267719e9272ffde', 1612302374, 'A', '_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'ETH', 'A', '1', '0.01241', '0', '_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', None, None),  # noqa: E501
    ]
    # Check that identifiers match with what is expected. This may need amendment if the upgrade test stays around while the code changes.  # noqa: E501
    trades = db.get_trades()
    assert all(x.identifier == trades_query[idx][0] for idx, x in enumerate(trades))

    # Check that cached icons were purged but custom icons were not
    assert (custom_icons_dir / custom_icon_filename).is_file()
    assert not any(x.is_file() for x in icons_dir.glob('*.*'))

    # Check that the cache history files no longer exist
    for price_file in history_cache_files:
        assert not price_file.is_file()
    assert not price_history_dir.is_dir()

    # Check errors/warnings
    warnings = msg_aggregator.consume_warnings()
    assert len(warnings) == 13
    for idx in (0, 1, 3, 5, 7):
        assert "During v24 -> v25 DB upgrade could not find key '_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94'" in warnings[idx]  # noqa: E501
    for idx in (2, 4, 6):
        assert "During v24 -> v25 DB upgrade could not find key '_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e'" in warnings[idx]  # noqa: E501
    for idx in (9, 11):
        assert 'Unknown/unsupported asset _ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94' in warnings[idx]  # noqa: E501
    for idx in (10, 12):
        assert 'Unknown/unsupported asset _ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e' in warnings[idx]  # noqa: E501
    errors = msg_aggregator.consume_errors()
    assert len(errors) == 0
    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 25


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('have_kraken', [True, False])
@pytest.mark.parametrize('have_kraken_setting', [True, False])
def test_upgrade_db_25_to_26(globaldb, user_data_dir, have_kraken, have_kraken_setting):  # pylint: disable=unused-argument  # noqa: E501
    """Test upgrading the DB from version 25 to version 26"""
    msg_aggregator = MessagesAggregator()
    with mock_dbhandler_ensura_data_integrity():
        v25_conn = _init_prepared_db(user_data_dir, 'v25_rotkehlchen.db')
    cursor = v25_conn.cursor()

    # make sure the globaldb has a custom token used in the DB
    globaldb.add_asset(
        asset_id='_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94',
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=EthereumToken.initialize(
            address=ChecksumEthAddress('0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94'),
            decimals=18,
            name='foo',
            symbol='FOO',
        ),
    )

    # Checks before migration
    credentials = cursor.execute(
        'SELECT name, api_key, api_secret, passphrase from user_credentials',
    ).fetchall()
    expected_credentials_before = [
        ('rotkehlchen', 'key', 'secret', ''),
        ('kraken', 'key', 'secret', ''),
        ('poloniex', 'key', 'secret', ''),
        ('bittrex', 'key', 'secret', ''),
        ('bitmex', 'key', 'secret', ''),
        ('binance', 'key', 'secret', ''),
        ('coinbase', 'key', 'secret', ''),
        ('coinbasepro', 'key', 'secret', 'phrase'),
        ('gemini', 'key', 'secret', ''),
        ('bitstamp', 'key', 'secret', ''),
        ('binance_us', 'key', 'secret', ''),
        ('bitfinex', 'key', 'secret', ''),
        ('bitcoinde', 'key', 'secret', ''),
        ('iconomi', 'key', 'secret', ''),
        ('kucoin', 'key', 'secret', ''),
        ('ftx', 'key', 'secret', ''),
    ]
    if have_kraken:
        expected_credentials_before.append(('kraken', 'key', 'secret', ''))
    else:  # Make sure the credentials are not in the DB
        cursor.execute('DELETE from user_credentials WHERE name="kraken";')

    if have_kraken_setting is False:
        # Make sure it's not there
        cursor.execute('DELETE from settings WHERE name="kraken_account_type";')

    assert set(credentials) == set(expected_credentials_before)
    settings = cursor.execute(
        'SELECT name, value from settings WHERE name="kraken_account_type";',
    ).fetchone()
    if have_kraken_setting:
        assert settings == ('kraken_account_type', 'pro')
    else:
        assert settings is None
    settings = cursor.execute(
        'SELECT name, value from settings WHERE name="anonymized_logs";',
    ).fetchone()
    assert settings == ('anonymized_logs', 'True')

    # check all tables are there before the upgrade
    assert cursor.execute('SELECT COUNT(*) from timed_balances;').fetchone()[0] == 392
    trades_query = cursor.execute(
        'SELECT id, time, location, base_asset, quote_asset, type, amount, rate, fee,'
        'fee_currency, link, notes from trades ORDER BY time ASC;',
    ).fetchall()
    assert trades_query == [
        ('foo1', 1, 'S', 'ETH', 'BTC', 'A', '1', '1', '1', 'ETH', '', ''),
        ('foo2', 1, 'B', 'ETH', 'BTC', 'A', '1', '1', '1', 'ETH', '', ''),
        ('fac279d109466a908119816d2ee7af90fba28f1ae60437bcbfab10e40a62bbc7', 1493227049, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '867.46673624', '0.00114990', '0.00249374', 'BTC', 'l1', None),  # noqa: E501
        ('56775b4b80f46d1dfc1b53fc0f6b61573c14142499bfe3a62e3371f7afc166db', 1493228252, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'A', '11348.12286689', '0.00008790', '0.00249374', 'BTC', 'l2', None),  # noqa: E501
        ('d38687c92fd4b56f7241b38653390a72022709ef8835c289f6d49cc436b8e05a', 1498949799, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '150.00000000', '0.00091705', '0.00034389', 'BTC', 'l3', None),  # noqa: E501
        ('cc31283b6e723f4a7364496b349869564b06b4320da3a14d95dcda1801369361', 1498966605, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '1000.00000000', '0.00091409', '0.00228521', 'BTC', 'l4', None),  # noqa: E501
        ('c76a42bc8b32407b7444da89cc9f73c22fd6a1bc0055b7d4112e3e59709b2b5b', 1499011364, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '200.00000000', '0.00092401', '0.00046200', 'BTC', 'l5', None),  # noqa: E501
        ('18810df423b24bb438360b23b50bd0fc11ed2d3701420651ef716f4840367894', 1499051024, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '120.00000000', '0.00091603', '0.00027480', 'BTC', 'l6', None),  # noqa: E501
        ('27bb15dfc1a008c2efa2c5510b30808d8246ab903cf9f950ea7a175f0779925d', 1499675187, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '200.00000000', '0.00091747', '0.00045869', 'BTC', 'l7', None),  # noqa: E501
        ('b0c4d1d816fa3448ba1ab1a285a35d71a42ff27d68438626eacecc4bf927ab07', 1499677638, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '1135.00000000', '0.00088101', '0.00249985', 'BTC', 'l8', None),  # noqa: E501
        ('6b91fc81d40c121af7397c5f3351547de4bd3f288fe483ace14b7b7922cfcd36', 1500494329, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'B', '10490.34064784', '0.00024385', '0.00639521', 'BTC', 'l9', None),  # noqa: E501
        ('59ea4f98a815467122d201d737b97f910c8918cfe8f476a74d51a4006ef1aaa8', 1500501003, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'B', '857.78221905', '0.00018099', '0.00038812', 'BTC', 'l10', None),  # noqa: E501
        ('dc4a8a1dd3ef78b6eae5ee69f24bed73196ba3677150015f80d28a70b963253c', 1501194075, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '510.21713000', '0.00039101', '0.00049875', 'BTC', 'l11', None),  # noqa: E501
        ('8ba98869f1398d9d64d974a13bc1e686746c7068b765223a46f886ef9c100722', 1501585385, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '731.28354007', '0.00034101', '0.00062343', 'BTC', 'l12', None),  # noqa: E501
        ('6f583c1297a86beadb46e8876db9589bb2ca60c603a4eca77b331611a49cd482', 1599751485, 'A', 'ETH', 'EUR', 'A', '150', '210.15', '0.2', 'EUR', None, None),  # noqa: E501
        ('3fc94b6b91de61d98b21bdba9a6e449b3ff25756f34a14d17dcf3979d08c4ee3', 1607172606, 'D', 'MAID', 'BTC', 'B', '15515.00000000', '0.00001299', '0.00040305', 'BTC', 'l13', None),  # noqa: E501
        ('ecd64dba4367a42292988abb34ed46b3dda0d48728c629f9727706d198023d6c', 1610915040, 'A', 'ETH', 'EUR', 'A', '5', '0.1', '0.001', '_ceth_0x111111111117dC0aa78b770fA6A738034120C302', 'dsad', 'ads'),  # noqa: E501c
        ('7aae102d9240f7d5f7f0669d6eefb47f2d1cf5bba462b0cee267719e9272ffde', 1612302374, 'A', '_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'ETH', 'A', '1', '0.01241', '0', '_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', None, None),  # noqa: E501
    ]
    asset_movements_query = cursor.execute('SELECT id, location, category, address, transaction_id, time, asset, amount, fee_asset, fee, link from asset_movements ORDER BY time ASC;').fetchall()  # noqa: E501
    assert asset_movements_query == [
        ('foo1', 'S', 'B', '0xaddy', '0xtxid', 1, 'ETH', '1', 'BTC', '1', 'customlink'),
        ('foo2', 'B', 'B', '0xaddy', '0xtxid', 1, 'ETH', '1', '_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F', '1', 'customlink'),  # noqa: E501
        ('822511b6035c5d2a7a7ff82c21b61381016e76764e84f656aedcfbc3b7a2e2f4', 'L', 'B', '0xaddy', '0xtxid', 1, '_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', '1', '_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96', '1', 'customlink'),  # noqa: E501
        ('98c8378892955d3c95cc24277188ad33504d2e668441ba23a270b6c65f00be43', 'D', 'A', '0xaddress', '0xtxid', 1493226738, 'BTC', '2.00000000', 'BTC', '0', 'link3'),  # noqa: E501
        ('9713d2c2f90edfc375bfea1d014599e9f3a20eded94625c0a2483c4ab2692ff9', 'D', 'A', '0xaddress', '0xtxid', 1498941726, 'BTC', '4.20000000', 'BTC', '0', 'link2'),  # noqa: E501
        ('86f6cda4bcd36e2fd0e8938fd3b31ebe895af2df6d8b60479c401cd846a3ccf8', 'D', 'B', '0xaddress', '0xtxid', 1501161076, 'BTC', '3.91944853', 'BTC', '0.00100000', 'link5'),  # noqa: E501
        ('9a3ab62aea2892e9000c868ce29a471e34f57d3bbae7691b920bcf58fbea10ce', 'D', 'A', '0xaddress', '0xtxid', 1577666912, 'MAID', '15515.00000000', 'MAID', '0', 'link1'),  # noqa: E501
        ('79d6d91d1fd2acf02a9d244e33ff340c04a938faaf0d1ba10aba9d8ae55b11cc', 'D', 'B', '0xaddress', '0xtxid', 1607094370, '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', '4753.96740631', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', '160.00000000', 'link4'),  # noqa: E501
    ]
    # Check manually tracked balances before upgrade
    query = cursor.execute('SELECT asset, label, amount, location from manually_tracked_balances;')  # noqa: E501
    assert query.fetchall() == [
        ('EUR', 'test eur balance', '1', 'A'),
        ('USD', 'test usd balance', '1', 'A'),
        ('CNY', 'test CNY balance', '1', 'A'),
        ('_ceth_0x8Ab7404063Ec4DBcfd4598215992DC3F8EC853d7', 'exotic asset', '1500', 'A'),
        ('_ceth_0x111111111117dC0aa78b770fA6A738034120C302', 'test for duplication', '100000', 'J'),  # noqa: E501
        ('_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94', 'test custom token balance', '65', 'A'),  # noqa: E501
        ('_ceth_0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9', 'test_asset_with_same_symbol', '85', 'A'),  # noqa: E501
        ('_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e', 'test_custom_token', '25', 'A'),  # this token is not known but will still be here after the upgrade  # noqa: E501
    ]
    # Check ledger actions before upgrade
    query = cursor.execute('SELECT identifier, timestamp, type, location, amount, asset, rate, rate_asset, link, notes from ledger_actions;')  # noqa: E501
    assert query.fetchall() == [
        (1, 1611260690, 'A', 'A', '1', '_ceth_0x0E8d6b471e332F140e7d9dbB99E5E3822F728DA6', None, None, None, None),  # noqa: E501
        (2, 1610483475, 'A', 'A', '1', '_ceth_0xB6eD7644C69416d67B522e20bC294A9a9B405B31', None, None, 'sad', 'asdsad'),  # noqa: E501
    ]
    # Check margin positions before upgrade
    query = cursor.execute('SELECT id, location, open_time, close_time, profit_loss, pl_currency, fee, fee_currency, link, notes from margin_positions;')  # noqa: E501
    raw_upgraded = query.fetchall()
    assert raw_upgraded == [
        ("3ebd1ff33f6b6431778db56393e6105b94b0b23d0976462d70279e6f82db9924", "C", 1, 5, "500", "ETH", "1", "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96", "", ""),  # noqa: E501
        ("2ecdf50622f0ad6277b2c4b28954118753db195c9ae2005ce7da7b30d4a873c4", "A", 1, 5, "1", "BTC", "1", "_ceth_0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6", "", ""),  # noqa: E501
        ("bec34827cd9ce879e91d45dfe11942752f810504439701ff7f3d005850f458a8", "A", 0, 5, "1", "_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e", "1", "_ceth_0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b", "", ""),  # noqa: E501
    ]
    # Check the tables that are just gonna get deleted have data before the upgrade
    assert cursor.execute('SELECT COUNT(*) from adex_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from aave_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from yearn_vaults_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from ethereum_accounts_details;').fetchone()[0] == 1
    # Check used query ranges before upgrade
    used_query_ranges = cursor.execute('SELECT * from used_query_ranges').fetchall()
    assert used_query_ranges == [
        ('binance_us_trades', 0, 1),
        ('binance_us_asset_movements', 0, 1),
        ('kraken_trades', 0, 1),
        ('kraken_asset_movements', 0, 1),
    ]

    v25_conn.commit()  # for changes done depending on test params
    v25_conn.close()

    # Migrate to v26
    with mock_dbhandler_ensura_data_integrity():
        db = _init_db_with_target_version(
            target_version=26,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
        )
    cursor = db.conn.cursor()

    # Make sure that the user credentials have been upgraded
    credentials = cursor.execute(
        'SELECT name, location, api_key, api_secret, passphrase from user_credentials',
    ).fetchall()
    expected_credentials = [
        ('rotkehlchen', 'A', 'key', 'secret', ''),
        ('poloniex', 'C', 'key', 'secret', ''),
        ('bittrex', 'D', 'key', 'secret', ''),
        ('bitmex', 'F', 'key', 'secret', ''),
        ('binance', 'E', 'key', 'secret', ''),
        ('coinbase', 'G', 'key', 'secret', ''),
        ('coinbasepro', 'K', 'key', 'secret', 'phrase'),
        ('gemini', 'L', 'key', 'secret', ''),
        ('bitstamp', 'R', 'key', 'secret', ''),
        ('binance_us', 'S', 'key', 'secret', ''),
        ('bitfinex', 'T', 'key', 'secret', ''),
        ('bitcoinde', 'U', 'key', 'secret', ''),
        ('iconomi', 'V', 'key', 'secret', ''),
        ('kucoin', 'W', 'key', 'secret', ''),
        ('ftx', 'Z', 'key', 'secret', ''),
    ]
    if have_kraken:
        expected_credentials.append(('kraken', 'B', 'key', 'secret', ''))
    assert set(credentials) == set(expected_credentials)
    # Make sure settings is no longer there
    settings = cursor.execute(
        'SELECT name, value from settings WHERE name="kraken_account_type";',
    ).fetchone()
    assert settings is None
    settings = cursor.execute(
        'SELECT name, value from settings WHERE name="anonymized_logs";',
    ).fetchone()
    assert settings is None
    mapping = cursor.execute(
        'SELECT credential_name, credential_location, setting_name, setting_value '
        'FROM user_credentials_mappings;',
    ).fetchone()
    if have_kraken and have_kraken_setting:
        assert mapping == ('kraken', 'B', 'kraken_account_type', 'pro')
    else:
        assert mapping is None

    # check trades/assets movements and used query ranges of binanceus were purged
    # Also check tables were properly migrated and we lost no data
    trades_query = cursor.execute(
        'SELECT id, time, location, base_asset, quote_asset, type, amount, rate, fee,'
        'fee_currency, link, notes from trades ORDER BY time ASC;',
    ).fetchall()
    assert trades_query == [
        ('foo2', 1, 'B', 'ETH', 'BTC', 'A', '1', '1', '1', 'ETH', '', ''),
        ('fac279d109466a908119816d2ee7af90fba28f1ae60437bcbfab10e40a62bbc7', 1493227049, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '867.46673624', '0.00114990', '0.00249374', 'BTC', 'l1', None),  # noqa: E501
        ('56775b4b80f46d1dfc1b53fc0f6b61573c14142499bfe3a62e3371f7afc166db', 1493228252, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'A', '11348.12286689', '0.00008790', '0.00249374', 'BTC', 'l2', None),  # noqa: E501
        ('d38687c92fd4b56f7241b38653390a72022709ef8835c289f6d49cc436b8e05a', 1498949799, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '150.00000000', '0.00091705', '0.00034389', 'BTC', 'l3', None),  # noqa: E501
        ('cc31283b6e723f4a7364496b349869564b06b4320da3a14d95dcda1801369361', 1498966605, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '1000.00000000', '0.00091409', '0.00228521', 'BTC', 'l4', None),  # noqa: E501
        ('c76a42bc8b32407b7444da89cc9f73c22fd6a1bc0055b7d4112e3e59709b2b5b', 1499011364, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '200.00000000', '0.00092401', '0.00046200', 'BTC', 'l5', None),  # noqa: E501
        ('18810df423b24bb438360b23b50bd0fc11ed2d3701420651ef716f4840367894', 1499051024, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '120.00000000', '0.00091603', '0.00027480', 'BTC', 'l6', None),  # noqa: E501
        ('27bb15dfc1a008c2efa2c5510b30808d8246ab903cf9f950ea7a175f0779925d', 1499675187, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '200.00000000', '0.00091747', '0.00045869', 'BTC', 'l7', None),  # noqa: E501
        ('b0c4d1d816fa3448ba1ab1a285a35d71a42ff27d68438626eacecc4bf927ab07', 1499677638, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '1135.00000000', '0.00088101', '0.00249985', 'BTC', 'l8', None),  # noqa: E501
        ('6b91fc81d40c121af7397c5f3351547de4bd3f288fe483ace14b7b7922cfcd36', 1500494329, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'B', '10490.34064784', '0.00024385', '0.00639521', 'BTC', 'l9', None),  # noqa: E501
        ('59ea4f98a815467122d201d737b97f910c8918cfe8f476a74d51a4006ef1aaa8', 1500501003, 'D', '_ceth_0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c', 'BTC', 'B', '857.78221905', '0.00018099', '0.00038812', 'BTC', 'l10', None),  # noqa: E501
        ('dc4a8a1dd3ef78b6eae5ee69f24bed73196ba3677150015f80d28a70b963253c', 1501194075, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '510.21713000', '0.00039101', '0.00049875', 'BTC', 'l11', None),  # noqa: E501
        ('8ba98869f1398d9d64d974a13bc1e686746c7068b765223a46f886ef9c100722', 1501585385, 'D', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', 'BTC', 'A', '731.28354007', '0.00034101', '0.00062343', 'BTC', 'l12', None),  # noqa: E501
        ('6f583c1297a86beadb46e8876db9589bb2ca60c603a4eca77b331611a49cd482', 1599751485, 'A', 'ETH', 'EUR', 'A', '150', '210.15', '0.2', 'EUR', None, None),  # noqa: E501
        ('3fc94b6b91de61d98b21bdba9a6e449b3ff25756f34a14d17dcf3979d08c4ee3', 1607172606, 'D', 'MAID', 'BTC', 'B', '15515.00000000', '0.00001299', '0.00040305', 'BTC', 'l13', None),  # noqa: E501
        ('ecd64dba4367a42292988abb34ed46b3dda0d48728c629f9727706d198023d6c', 1610915040, 'A', 'ETH', 'EUR', 'A', '5', '0.1', '0.001', '_ceth_0x111111111117dC0aa78b770fA6A738034120C302', 'dsad', 'ads'),  # noqa: E501c
        ('7aae102d9240f7d5f7f0669d6eefb47f2d1cf5bba462b0cee267719e9272ffde', 1612302374, 'A', '_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'ETH', 'A', '1', '0.01241', '0', '_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', None, None),  # noqa: E501
    ]
    asset_movements_query = cursor.execute('SELECT id, location, category, address, transaction_id, time, asset, amount, fee_asset, fee, link from asset_movements ORDER BY time ASC;').fetchall()  # noqa: E501
    assert asset_movements_query == [
        ('foo2', 'B', 'B', '0xaddy', '0xtxid', 1, 'ETH', '1', '_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F', '1', 'customlink'),  # noqa: E501
        ('822511b6035c5d2a7a7ff82c21b61381016e76764e84f656aedcfbc3b7a2e2f4', 'L', 'B', '0xaddy', '0xtxid', 1, '_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', '1', '_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96', '1', 'customlink'),  # noqa: E501
        ('98c8378892955d3c95cc24277188ad33504d2e668441ba23a270b6c65f00be43', 'D', 'A', '0xaddress', '0xtxid', 1493226738, 'BTC', '2.00000000', 'BTC', '0', 'link3'),  # noqa: E501
        ('9713d2c2f90edfc375bfea1d014599e9f3a20eded94625c0a2483c4ab2692ff9', 'D', 'A', '0xaddress', '0xtxid', 1498941726, 'BTC', '4.20000000', 'BTC', '0', 'link2'),  # noqa: E501
        ('86f6cda4bcd36e2fd0e8938fd3b31ebe895af2df6d8b60479c401cd846a3ccf8', 'D', 'B', '0xaddress', '0xtxid', 1501161076, 'BTC', '3.91944853', 'BTC', '0.00100000', 'link5'),  # noqa: E501
        ('9a3ab62aea2892e9000c868ce29a471e34f57d3bbae7691b920bcf58fbea10ce', 'D', 'A', '0xaddress', '0xtxid', 1577666912, 'MAID', '15515.00000000', 'MAID', '0', 'link1'),  # noqa: E501
        ('79d6d91d1fd2acf02a9d244e33ff340c04a938faaf0d1ba10aba9d8ae55b11cc', 'D', 'B', '0xaddress', '0xtxid', 1607094370, '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', '4753.96740631', '_ceth_0xB9e7F8568e08d5659f5D29C4997173d84CdF2607', '160.00000000', 'link4'),  # noqa: E501
    ]  # noqa: E501
    query = cursor.execute('SELECT identifier, timestamp, type, location, amount, asset, rate, rate_asset, link, notes from ledger_actions;')  # noqa: E501
    assert query.fetchall() == [
        (1, 1611260690, 'A', 'A', '1', '_ceth_0x0E8d6b471e332F140e7d9dbB99E5E3822F728DA6', None, None, None, None),  # noqa: E501
        (2, 1610483475, 'A', 'A', '1', '_ceth_0xB6eD7644C69416d67B522e20bC294A9a9B405B31', None, None, 'sad', 'asdsad'),  # noqa: E501
    ]
    # Check manually tracked balances after upgrades
    query = cursor.execute('SELECT asset, label, amount, location from manually_tracked_balances;')  # noqa: E501
    assert query.fetchall() == [
        ('EUR', 'test eur balance', '1', 'A'),
        ('USD', 'test usd balance', '1', 'A'),
        ('CNY', 'test CNY balance', '1', 'A'),
        ('_ceth_0x8Ab7404063Ec4DBcfd4598215992DC3F8EC853d7', 'exotic asset', '1500', 'A'),
        ('_ceth_0x111111111117dC0aa78b770fA6A738034120C302', 'test for duplication', '100000', 'J'),  # noqa: E501
        ('_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94', 'test custom token balance', '65', 'A'),  # noqa: E501
        ('_ceth_0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9', 'test_asset_with_same_symbol', '85', 'A'),  # noqa: E501
        ('_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e', 'test_custom_token', '25', 'A'),  # this token is not known but will still be here after the upgrade  # noqa: E501
    ]
    # Check margin positions after upgrade
    query = cursor.execute('SELECT id, location, open_time, close_time, profit_loss, pl_currency, fee, fee_currency, link, notes from margin_positions;')  # noqa: E501
    raw_upgraded = query.fetchall()
    assert raw_upgraded == [
        ("3ebd1ff33f6b6431778db56393e6105b94b0b23d0976462d70279e6f82db9924", "C", 1, 5, "500", "ETH", "1", "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96", "", ""),  # noqa: E501
        ("2ecdf50622f0ad6277b2c4b28954118753db195c9ae2005ce7da7b30d4a873c4", "A", 1, 5, "1", "BTC", "1", "_ceth_0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6", "", ""),  # noqa: E501
        ("bec34827cd9ce879e91d45dfe11942752f810504439701ff7f3d005850f458a8", "A", 0, 5, "1", "_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e", "1", "_ceth_0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b", "", ""),  # noqa: E501
    ]
    used_query_ranges = cursor.execute('SELECT * from used_query_ranges').fetchall()
    assert used_query_ranges == [
        ('kraken_trades', 0, 1),
        ('kraken_asset_movements', 0, 1),
    ]
    # Check the tables that should have had their data deleted had them
    assert cursor.execute('SELECT COUNT(*) from adex_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from aave_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from yearn_vaults_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from ethereum_accounts_details;').fetchone()[0] == 0
    # check that the timed balances are still there and have not changed
    assert cursor.execute('SELECT COUNT(*) from timed_balances;').fetchone()[0] == 392
    query = cursor.execute('SELECT category, time, currency, amount, usd_value from timed_balances;')  # noqa: E501
    for idx, entry in enumerate(query):
        # the test DB also has some custom tokens which are not in the globalDB as of this writing
        # 1st one is random fake address, 2nd one is vBNT
        if entry[2] in ('_ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e', '_ceth_0x48Fb253446873234F2fEBbF9BdeAA72d9d387f94'):  # noqa: E501
            continue

        # make sure the asset is understood
        _ = Asset(entry[2])
        # check some specific entries
        if idx == 388:
            assert entry == (
                'A',
                1616766011,
                'CNY',
                '1',
                '0.1528360528',
            )
        elif idx == 384:
            assert entry == (
                'A',
                1616766011,
                '_ceth_0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643',
                '1711.44952226',
                '36.3901575584242602',
            )
        elif idx == 2:
            assert entry == (
                'A',
                1610559319,
                '_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F',
                '90.5639',
                '90.54578722',
            )
        elif idx == 1:
            assert entry == (
                'A',
                1610559319,
                '_ceth_0x4DC3643DbC642b72C158E7F3d2ff232df61cb6CE',
                '0.1',
                '0.001504',
            )
    userdb_assets_num = cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0]
    globaldb_cursor = globaldb._conn.cursor()
    globaldb_assets_num = globaldb_cursor.execute('SELECT COUNT(*) from assets;').fetchone()[0]
    msg = 'User DB should contain 1 extra asset that is moved over without existing in the global DB'  # noqa: E501
    assert globaldb_assets_num == userdb_assets_num - 1, msg

    # Check errors/warnings
    warnings = msg_aggregator.consume_warnings()
    assert len(warnings) == 3
    assert 'During v25 -> v26 DB upgrade found timed_balances entry of unknown asset _ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e' in warnings[0]  # noqa: E501
    for idx in (1, 2):
        assert 'Unknown/unsupported asset _ceth_0xdb89d55d8878680FED2233ea6E1Ae7DF79C7073e found in the database' in warnings[idx]  # noqa: E501
    errors = msg_aggregator.consume_errors()
    assert len(errors) == 0

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 26


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_26_to_27(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 26 to version 27.

    - Recreates balancer events, uniswap events, amm_swaps. Deletes balancer pools
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v26_rotkehlchen.db')
    db_v26 = _init_db_with_target_version(
        target_version=26,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    # Checks before migration
    cursor = db_v26.conn.cursor()
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "uniswap%";',
    ).fetchone()[0] == 2
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "balancer%";',
    ).fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges;').fetchone()[0] == 6
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from balancer_pools;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 1

    # Migrate to v27
    db = _init_db_with_target_version(
        target_version=27,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges;').fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 0

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 27


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_27_to_28(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 27 to version 28.

    - Adds a new column 'version' to the 'yearn_vaults_events' table
    - Delete aave events
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v27_rotkehlchen.db')
    db_v27 = _init_db_with_target_version(
        target_version=27,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db_v27.conn.cursor()

    # Checks before migration
    assert cursor.execute('SELECT COUNT(*) FROM aave_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from yearn_vaults_events;').fetchone()[0] == 1
    # Migrate to v28
    db = _init_db_with_target_version(
        target_version=28,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()

    cursor.execute(
        'SELECT COUNT(*) FROM pragma_table_info("yearn_vaults_events") '
        'WHERE name="version"',
    )
    assert cursor.fetchone()[0] == 1

    cursor.execute('SELECT count(*) from yearn_vaults_events;')
    assert cursor.fetchone()[0] == 1

    # Check that the version is correct for the event in db
    cursor.execute('SELECT version from yearn_vaults_events;')
    assert cursor.fetchone()[0] == 1

    # Check that aave_events got deleted
    assert cursor.execute('SELECT COUNT(*) FROM aave_events;').fetchone()[0] == 0

    # Finally also make sure that we have updated to the target version
    assert db.get_version() == 28


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
