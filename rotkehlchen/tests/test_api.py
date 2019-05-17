import os
from json.decoder import JSONDecodeError

import pytest

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.dbhandler import AssetBalance
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.typing import Timestamp
from rotkehlchen.utils.serialization import rlk_jsonloads_dict


def test_add_remove_blockchain_account(rotkehlchen_server):
    """
    Test that the api call to add or remove a blockchain account correctly appends
    the accounts and properly updates the balances

    Also serves as regression for issue https://github.com/rotkehlchenio/rotkehlchen/issues/66
    """
    response = rotkehlchen_server.add_blockchain_account(
        'ETH',
        '0x00d74c25bbf93df8b2a41d82b0076843b4db0349',
    )
    checksummed = '0x00d74C25bBf93Df8B2A41d82B0076843B4dB0349'
    assert response['result'] is True
    assert response['message'] == ''
    assert 'ETH' in response['per_account']['ETH'][checksummed]
    assert 'usd_value' in response['per_account']['ETH'][checksummed]
    assert 'amount' in response['totals']['ETH']
    assert 'usd_value' in response['totals']['ETH']
    response = rotkehlchen_server.remove_blockchain_account(
        'ETH',
        '0x00d74C25bBf93Df8B2A41d82B0076843B4dB0349',
    )
    assert response['result'] is True
    assert response['message'] == ''
    assert response['per_account']['ETH'] == {}
    assert response['totals']['ETH']['amount'] == '0'
    assert response['totals']['ETH']['usd_value'] == '0'

    # Now check a bitcoin account
    btc_account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    response = rotkehlchen_server.add_blockchain_account(
        'BTC',
        btc_account,
    )
    assert response['result'] is True
    assert response['message'] == ''
    assert 'usd_value' in response['per_account']['BTC'][btc_account]
    assert 'amount' in response['totals']['BTC']
    assert 'usd_value' in response['totals']['BTC']
    response = rotkehlchen_server.remove_blockchain_account(
        'BTC',
        btc_account,
    )
    assert response['result'] is True
    assert response['message'] == ''
    assert response['per_account']['BTC'] == {}
    assert response['totals']['BTC']['amount'] == '0'
    assert response['totals']['BTC']['usd_value'] == '0'


@pytest.mark.parametrize('number_of_accounts', [0])
def test_add_remove_eth_tokens(rotkehlchen_instance):
    """Test for issue 83 https://github.com/rotkehlchenio/rotkehlchen/issues/83"""
    # Addition of tokens into the DB fires up balance checks for each account
    # we got. For that reason we give 0 accounts for this test

    tokens_to_add = ['STORJ', 'GNO', 'RDN']
    rotkehlchen_instance.add_owned_eth_tokens(tokens_to_add)
    db_tokens_list = rotkehlchen_instance.data.db.get_owned_tokens()
    assert set(tokens_to_add) == set(db_tokens_list)

    rotkehlchen_instance.remove_owned_eth_tokens(['STORJ', 'GNO'])
    db_tokens_list = rotkehlchen_instance.data.db.get_owned_tokens()
    assert len(db_tokens_list) == 1 and db_tokens_list[0] == 'RDN'


def test_periodic_query(rotkehlchen_instance):
    """Test that periodic query returns expected dict values"""
    result = rotkehlchen_instance.query_periodic_data()

    assert len(result) == 3
    assert result['last_balance_save'] == 0
    assert (
        isinstance(result['eth_node_connection'], bool) and
        result['eth_node_connection'] is False
    )
    assert result['history_process_current_ts'] == -1


def test_periodic_data_before_login_completion(cli_args):
    """Test that periodic query returns empty list if user is not yet logged in"""
    rotkehlchen = Rotkehlchen(cli_args)
    result = rotkehlchen.query_periodic_data()
    assert len(result) == 0


@pytest.mark.parametrize('number_of_accounts', [0])
def test_dbinfo_is_written_at_shutdown(rotkehlchen_instance):
    """Test that when rotkehlchen shuts down dbinfo is written"""
    filepath = os.path.join(rotkehlchen_instance.data.user_data_dir, 'dbinfo.json')
    sqlcipher_version = rotkehlchen_instance.data.db.sqlcipher_version
    rotkehlchen_instance.shutdown()

    assert os.path.exists(filepath), 'dbinfo.json was not written'
    with open(filepath, 'r') as f:
        try:
            dbinfo = rlk_jsonloads_dict(f.read())
        except JSONDecodeError:
            assert False, 'Could not decode dbinfo.json'

    assert dbinfo['sqlcipher_version'] == sqlcipher_version
    assert 'md5_hash' in dbinfo


@pytest.mark.parametrize('number_of_accounts', [0])
def test_logout_and_login_again(rotkehlchen_instance, username):
    """Test that when a rotkehlchen user logs out they can properly login again
    Regression test for https://github.com/rotkehlchenio/rotkehlchen/issues/288
    """
    rotkehlchen_instance.logout()
    assert not rotkehlchen_instance.user_is_logged_in
    rotkehlchen_instance.unlock_user(
        user=username,
        password='123',
        create_new=False,
        sync_approval='unknown',
        api_key='',
        api_secret='',
    )
    assert rotkehlchen_instance.user_is_logged_in
    # The bug for #288 was here. The inquirer instance was None and any
    # queries utilizing it were throwing exceptions.
    Inquirer().get_fiat_usd_exchange_rates(currencies=None)
