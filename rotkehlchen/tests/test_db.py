import os
import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.utils import ts_now
from rotkehlchen.db.dbhandler import (
    ROTKEHLCHEN_DB_VERSION,
    DEFAULT_START_DATE,
    DEFAULT_UI_FLOATING_PRECISION
)
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.errors import AuthenticationError, InputError


TABLES_AT_INIT = [
    'timed_balances',
    'timed_location_data',
    'user_credentials',
    'blockchain_accounts',
    'multisettings',
    'current_balances',
    'trades',
    'settings',
]


def test_data_init_and_password(data_dir, username):
    """DB Creation logic and tables at start testing"""
    # Creating a new data dir should work
    data = DataHandler(data_dir)
    data.unlock(username, '123', create_new=True)
    assert os.path.exists(os.path.join(data_dir, username))

    # Trying to re-create it should throw
    with pytest.raises(AuthenticationError):
        data.unlock(username, '123', create_new=True)

    # Trying to unlock a non-existing user without create_new should throw
    with pytest.raises(AuthenticationError):
        data.unlock('otheruser', '123', create_new=False)

    # now relogin and check all tables are there
    del data
    data = DataHandler(data_dir)
    data.unlock(username, '123', create_new=False)
    cursor = data.db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    results = cursor.fetchall()
    results = [result[0] for result in results]
    assert set(results) == set(TABLES_AT_INIT)

    # finally logging in with wrong password should also fail
    del data
    data = DataHandler(data_dir)
    with pytest.raises(AuthenticationError):
        data.unlock(username, '1234', create_new=False)


def test_export_import_db(data_dir, username):
    """Create a DB, write some data and then after export/import confirm it's there"""
    data = DataHandler(data_dir)
    data.unlock(username, '123', create_new=True)
    data.set_fiat_balance('EUR', 10)

    encoded_data, data_hash = data.compress_and_encrypt_db('123')
    # The server would return them decoded
    encoded_data = encoded_data.decode()
    data.decompress_and_decrypt_db('123', encoded_data)
    fiat_balances = data.get_fiat_balances()
    assert len(fiat_balances) == 1
    assert int(fiat_balances['EUR']) == 10


def test_writting_fetching_data(data_dir, username):
    data = DataHandler(data_dir)
    data.unlock(username, '123', create_new=True)

    tokens = ['GNO', 'RDN']
    data.write_owned_eth_tokens(tokens)
    result = data.db.get_owned_tokens()
    assert set(tokens) == set(result)

    data.add_blockchain_account('BTC', '1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS')
    data.add_blockchain_account('ETH', '0xd36029d76af6fE4A356528e4Dc66B2C18123597D')
    data.add_blockchain_account('ETH', '0x80b369799104a47e98a553f3329812a44a7facdc')
    accounts = data.db.get_blockchain_accounts()
    assert len(accounts) == 2
    assert accounts['BTC'] == ['1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS']
    assert set(accounts['ETH']) == set([
        '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
        '0x80b369799104a47e98a553f3329812a44a7facdc'

    ])
    # Add existing account should fail
    with pytest.raises(sqlcipher.IntegrityError):
        data.add_blockchain_account('ETH', '0xd36029d76af6fE4A356528e4Dc66B2C18123597D')
    # Remove non-existing account
    with pytest.raises(InputError):
        data.remove_blockchain_account('ETH', '0x136029d76af6fE4A356528e4Dc66B2C18123597D')
    # Remove existing account
    data.remove_blockchain_account('ETH', '0xd36029d76af6fE4A356528e4Dc66B2C18123597D')
    accounts = data.db.get_blockchain_accounts()
    assert accounts['ETH'] == ['0x80b369799104a47e98a553f3329812a44a7facdc']

    result, _ = data.add_ignored_asset('DAO')
    assert result
    result, _ = data.add_ignored_asset('DOGE')
    assert result
    result, _ = data.add_ignored_asset('DOGE')
    assert not result
    assert set(data.db.get_ignored_assets()) == set(['DAO', 'DOGE'])
    result, _ = data.remove_ignored_asset('XXX')
    assert not result
    result, _ = data.remove_ignored_asset('DOGE')
    assert result
    assert data.db.get_ignored_assets() == ['DAO']

    # With nothing inserted in settings make sure default values are returned
    result = data.db.get_settings()
    last_write_diff = ts_now() - result['last_write_ts']
    # make sure last_write was within 3 secs
    assert last_write_diff >= 0 and last_write_diff < 3
    del result['last_write_ts']
    assert result == {
        'historical_data_start': DEFAULT_START_DATE,
        'eth_rpc_port': '8545',
        'ui_floating_precision': DEFAULT_UI_FLOATING_PRECISION,
        'db_version': ROTKEHLCHEN_DB_VERSION
    }

    # Check setting non-existing settings. Should be ignored
    _, msg = data.set_settings({'nonexisting_setting': 1}, accountant=None)
    assert msg != '' and 'nonexisting_setting' in msg
    _, msg = data.set_settings({
        'nonexisting_setting': 1,
        'eth_rpc_port': '8555',
        'ui_floating_precision': 3,
    }, accountant=None)
    assert msg != '' and 'nonexisting_setting' in msg

    # Now check nothing funny made it in the db
    result = data.db.get_settings()
    assert result['eth_rpc_port'] == '8555'
    assert result['ui_floating_precision'] == 3
    assert 'nonexisting_setting' not in result
