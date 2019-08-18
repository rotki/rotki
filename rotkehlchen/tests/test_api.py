import os
from json.decoder import JSONDecodeError
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.blockchain import Blockchain
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.data_handler import VALID_SETTINGS
from rotkehlchen.db.utils import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.exchanges import BINANCE_BALANCES_RESPONSE
from rotkehlchen.tests.utils.history import TEST_END_TS, mock_history_processing_and_exchanges
from rotkehlchen.tests.utils.mock import MockResponse, MockWeb3
from rotkehlchen.tests.utils.rotkehlchen import add_starting_balances
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsonloads_dict


def check_positive_balances_result(response, asset_symbols, account):
    assert response['result'] is True
    assert response['message'] == ''

    for asset_symbol in asset_symbols:
        if asset_symbol != 'BTC':
            assert asset_symbol in response['per_account']['ETH'][account]
        assert 'usd_value' in response['per_account'][asset_symbol][account]
        assert 'amount' in response['totals'][asset_symbol]
        assert 'usd_value' in response['totals'][asset_symbol]


def check_no_balances_result(response, asset_symbols, check_per_account=True):
    for asset_symbol in asset_symbols:
        assert response['result'] is True
        assert response['message'] == ''
        if check_per_account:
            assert response['per_account'][asset_symbol] == {}
        assert FVal(response['totals'][asset_symbol]['amount']) == FVal('0')
        assert FVal(response['totals'][asset_symbol]['usd_value']) == FVal('0')


def check_proper_unlock_result(response):
    assert response['result'] is True
    assert response['message'] == ''
    assert isinstance(response['exchanges'], list)
    assert 'premium' in response
    assert response['settings']['db_version'] == ROTKEHLCHEN_DB_VERSION
    for setting in VALID_SETTINGS:
        assert setting in response['settings']


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
    check_positive_balances_result(response, ['ETH'], checksummed)
    response = rotkehlchen_server.remove_blockchain_account(
        'ETH',
        '0x00d74C25bBf93Df8B2A41d82B0076843B4dB0349',
    )
    check_no_balances_result(response, ['ETH'])

    # Now check a bitcoin account
    btc_account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    response = rotkehlchen_server.add_blockchain_account(
        'BTC',
        btc_account,
    )
    check_positive_balances_result(response, ['BTC'], btc_account)
    response = rotkehlchen_server.remove_blockchain_account(
        'BTC',
        btc_account,
    )
    check_no_balances_result(response, ['BTC'])


@pytest.mark.parametrize('number_of_accounts', [0])
def test_add_remove_eth_tokens(rotkehlchen_server):
    """Regression test for https://github.com/rotkehlchenio/rotkehlchen/issues/83"""
    # Addition of tokens into the DB fires up balance checks for each account
    # we got. For that reason we give 0 accounts for this test

    tokens_to_add = ['STORJ', 'GNO', 'RDN']
    response = rotkehlchen_server.add_owned_eth_tokens(tokens_to_add)
    check_no_balances_result(response, tokens_to_add, check_per_account=False)

    response = rotkehlchen_server.get_eth_tokens()
    assert set(tokens_to_add) == set(response['owned_eth_tokens'])
    assert 'all_eth_tokens' in response

    response = rotkehlchen_server.remove_owned_eth_tokens(['STORJ', 'GNO'])
    check_no_balances_result(response, ['RDN'], check_per_account=False)
    response = rotkehlchen_server.get_eth_tokens()
    assert 'all_eth_tokens' in response
    assert len(response['owned_eth_tokens']) == 1 and response['owned_eth_tokens'][0] == 'RDN'


@pytest.mark.parametrize('number_of_accounts', [0])
def test_remove_eth_token_before_any_queries(rotkehlchen_server, ethchain_client):
    """Regrestion test for 467"""
    tokens_to_add = ['PRL']
    response = rotkehlchen_server.add_owned_eth_tokens(tokens_to_add)
    assert response['result'] is True
    # At least for now the PRL token is not in cryptocompare. A token without a
    # price is not counted in the total
    assert 'PRL' not in response['totals']

    response = rotkehlchen_server.get_eth_tokens()
    assert set(tokens_to_add) == set(response['owned_eth_tokens'])
    assert 'all_eth_tokens' in response

    # Now use a clean blockchain instance to emulate restart where blockchain.totals
    # has not been populated.
    rotki = rotkehlchen_server.rotkehlchen
    rotki.blockchain = Blockchain(
        blockchain_accounts=rotki.data.db.get_blockchain_accounts(),
        owned_eth_tokens=rotki.data.db.get_owned_tokens(),
        ethchain=ethchain_client,
        msg_aggregator=MessagesAggregator(),
    )

    response = rotkehlchen_server.remove_owned_eth_tokens(['PRL'])
    assert response['result'] is True
    response = rotkehlchen_server.get_eth_tokens()
    assert 'all_eth_tokens' in response
    assert len(response['owned_eth_tokens']) == 0


def test_periodic_query(rotkehlchen_server):
    """Test that periodic query returns expected dict values"""
    result = rotkehlchen_server.query_periodic_data()

    assert len(result) == 4
    assert result['last_balance_save'] == 0
    assert (
        isinstance(result['eth_node_connection'], bool) and
        result['eth_node_connection'] is False
    )
    assert result['history_process_start_ts'] == -1
    assert result['history_process_current_ts'] == -1


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_periodic_data_before_login_completion(rotkehlchen_server):
    """Test that periodic query returns empty list if user is not yet logged in"""
    result = rotkehlchen_server.query_periodic_data()
    assert len(result) == 0


@pytest.mark.parametrize('number_of_accounts', [0])
def test_dbinfo_is_written_at_shutdown(rotkehlchen_server):
    """Test that when rotkehlchen shuts down dbinfo is written"""
    r = rotkehlchen_server.rotkehlchen
    filepath = os.path.join(r.data.user_data_dir, 'dbinfo.json')
    sqlcipher_version = r.data.db.sqlcipher_version
    # Using rotkehlchen instance's shutdown and not server's since the
    # server is not mocked well here for this.
    r.shutdown()

    assert os.path.exists(filepath), 'dbinfo.json was not written'
    with open(filepath, 'r') as f:
        try:
            dbinfo = rlk_jsonloads_dict(f.read())
        except JSONDecodeError:
            raise AssertionError('Could not decode dbinfo.json')

    assert dbinfo['sqlcipher_version'] == sqlcipher_version
    assert 'md5_hash' in dbinfo


@pytest.mark.parametrize('number_of_accounts', [0])
def test_logout_and_login_again(rotkehlchen_server, username):
    """Test that when a rotkehlchen user logs out they can properly login again

    Tests that unlock works correctly and returns proper response

    Also regression test for https://github.com/rotkehlchenio/rotkehlchen/issues/288
    """
    rotkehlchen_server.logout()
    assert not rotkehlchen_server.rotkehlchen.user_is_logged_in
    response = rotkehlchen_server.unlock_user(
        user=username,
        password='123',
        create_new=False,
        sync_approval='unknown',
        api_key='',
        api_secret='',
    )
    check_proper_unlock_result(response)

    assert rotkehlchen_server.rotkehlchen.user_is_logged_in
    # The bug for #288 was here. The inquirer instance was None and any
    # queries utilizing it were throwing exceptions.
    Inquirer().get_fiat_usd_exchange_rates(currencies=None)


@pytest.mark.parametrize('number_of_accounts', [0])
def test_query_owned_assets(rotkehlchen_server):
    """Test that query_owned_assets API call works as expected and that
    it properly serializes assets but also ignores unknown ones
    """
    add_starting_balances(rotkehlchen_server.rotkehlchen.data)

    response = rotkehlchen_server.query_owned_assets()
    assert response['message'] == ''
    assert response['result'] == ['BTC', 'ETH', 'EUR', 'XMR']

    # Check that we can get the warning for the unknown asset via the api
    response = rotkehlchen_server.consume_messages()
    assert response['message'] == ''
    assert response['result']['errors'] == []
    warnings = response['result']['warnings']
    assert len(warnings) == 1
    assert 'Unknown/unsupported asset ADSADX found in the database' in warnings[0]


def test_query_timed_balances_data(rotkehlchen_server):
    """Test that query_timed_balances_data API call works as expected and that
    it properly serializes assets but also ignores unknown ones
    """
    add_starting_balances(rotkehlchen_server.rotkehlchen.data)

    response = rotkehlchen_server.query_timed_balances_data('BTC', 0, 99999999999)
    assert response['message'] == ''
    assert len(response['result']) == 1
    assert response['result'][0] == {'time': 1488326400, 'amount': '1', 'usd_value': '1222.66'}

    response = rotkehlchen_server.query_timed_balances_data('DSXXADA', 0, 99999999999)
    assert not response['result']
    assert response['message'] == 'Unknown asset DSXXADA provided.'


def test_query_fiat_balances(rotkehlchen_server):
    """Test that query fiat balances works properly"""

    # Add them in the DB
    ok, _ = rotkehlchen_server.set_fiat_balance('USD', '100.5')
    assert ok
    ok, _ = rotkehlchen_server.set_fiat_balance('CNY', '55.5')
    assert ok

    # and now query fiat balances
    result = rotkehlchen_server.query_fiat_balances()
    # and make sure it works fine
    # (skipping usd value since I don't want to test conversion in this test)
    assert result['USD']['amount'] == '100.5'
    assert result['CNY']['amount'] == '55.5'


def test_query_balances(rotkehlchen_server, function_scope_binance):
    """Test that the query_balances call works properly.

    That means that the balances are all returned in the expected format and
    that they are saved in the DB.

    The test is for a user with fiat balances and with some binance balances.
    """

    # First set the fiat balances
    ok, _ = rotkehlchen_server.set_fiat_balance('USD', '100.5')
    assert ok
    ok, _ = rotkehlchen_server.set_fiat_balance('EUR', '75.5')
    assert ok
    exchanges = rotkehlchen_server.rotkehlchen.exchange_manager.connected_exchanges
    exchanges['binance'] = function_scope_binance

    def mock_binance_balances(url):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

    mock_binance = patch.object(
        exchanges['binance'].session,
        'get',
        side_effect=mock_binance_balances,
    )

    eur_usd_rate = Inquirer().query_fiat_pair(A_EUR, A_USD)

    eth_usd_rate = FVal('100.5')
    btc_usd_rate = FVal('120.1')

    def mock_query_cryptocompare_for_fiat_price(asset: Asset) -> Price:
        if asset == A_ETH:
            return Price(eth_usd_rate)
        elif asset == A_BTC:
            return Price(btc_usd_rate)

        # else
        raise AssertionError(f'Unexpected asset {asset} at mock cryptocompare query')

    mock_find_usd_price = patch(
        'rotkehlchen.inquirer.query_cryptocompare_for_fiat_price',
        side_effect=mock_query_cryptocompare_for_fiat_price,
    )

    now = ts_now()
    with mock_binance, mock_find_usd_price:
        result = rotkehlchen_server.query_balances(save_data=True)

    assert result['USD']['amount'] == '100.5'
    assert result['USD']['usd_value'] == '100.5'
    eur_amount = FVal('75.5')
    assert result['EUR']['amount'] == str(eur_amount)
    eur_usd_value = eur_amount * eur_usd_rate
    assert result['EUR']['usd_value'] == str(eur_usd_value)
    eth_amount = FVal('4763368.68006011')
    assert result['ETH']['amount'] == str(eth_amount)
    eth_usd_value = eth_amount * eth_usd_rate
    assert result['ETH']['usd_value'] == str(eth_usd_value)
    btc_amount = FVal('4723846.89208129')
    assert result['BTC']['amount'] == str(btc_amount)
    btc_usd_value = btc_amount * btc_usd_rate
    assert result['BTC']['usd_value'] == str(btc_usd_value)
    binance_usd_value = btc_usd_value + eth_usd_value
    assert result['location']['binance']['usd_value'] == str(binance_usd_value)
    banks_usd_value = eur_usd_value + FVal('100.5')
    assert result['location']['banks']['usd_value'] == str(banks_usd_value)
    assert result['net_usd'] == str(banks_usd_value + binance_usd_value)

    # make sure that balances also got saved in the DB
    db = rotkehlchen_server.rotkehlchen.data.db
    save_ts = db.get_last_balance_save_time()
    assert save_ts >= now
    assert save_ts - now < 5, 'Saving balances took too long'

    location_data = db.get_latest_location_value_distribution()
    assert len(location_data) == 4

    assert location_data[0].location == 'banks'
    assert location_data[0].usd_value == str(banks_usd_value)
    assert location_data[1].location == 'binance'
    assert location_data[1].usd_value == str(binance_usd_value)
    assert location_data[2].location == 'blockchain'
    assert location_data[3].location == 'total'
    assert location_data[3].usd_value == str(banks_usd_value + binance_usd_value)


def test_query_netvalue_data(rotkehlchen_server):
    """Test that query_netvalue_data API call works as expected"""
    add_starting_balances(rotkehlchen_server.rotkehlchen.data)

    response = rotkehlchen_server.query_netvalue_data()
    times = response['times']
    values = response['data']
    assert len(times) == 3
    assert times[0] == 1451606400
    assert times[1] == 1461606500
    assert times[2] == 1491607800
    assert len(values) == 3
    assert values[0] == '1500'
    assert values[1] == '4500'
    assert values[2] == '10700.5'


def test_query_latest_location_value_distribution(rotkehlchen_server):
    """Test that query_latest_location_value_distribution API call works as expected"""
    add_starting_balances(rotkehlchen_server.rotkehlchen.data)

    response = rotkehlchen_server.query_latest_location_value_distribution()
    assert response['message'] == ''
    distribution = response['result']
    assert all(entry['time'] == Timestamp(1491607800) for entry in distribution)
    assert distribution[0]['location'] == 'banks'
    assert distribution[0]['usd_value'] == '10000'
    assert distribution[1]['location'] == 'blockchain'
    assert distribution[1]['usd_value'] == '200000'
    assert distribution[2]['location'] == 'kraken'
    assert distribution[2]['usd_value'] == '2000'
    assert distribution[3]['location'] == 'poloniex'
    assert distribution[3]['usd_value'] == '100'
    assert distribution[4]['location'] == 'total'
    assert distribution[4]['usd_value'] == '10700.5'


def test_query_latest_asset_value_distribution(rotkehlchen_server):
    """Test that query_latest_asset_value_distribution API call works as expected"""
    add_starting_balances(rotkehlchen_server.rotkehlchen.data)

    response = rotkehlchen_server.query_latest_asset_value_distribution()
    assert response['message'] == ''
    distribution = response['result']
    # should be sorted by usd value
    assert isinstance(distribution[0]['asset'], str)
    assert distribution[0] == {
        'time': 1488326400,
        'asset': 'ETH',
        'amount': '10',
        'usd_value': '4517.4',
    }
    assert isinstance(distribution[1]['asset'], str)
    assert distribution[1] == {
        'time': 1488326400,
        'asset': 'BTC',
        'amount': '1',
        'usd_value': '1222.66',
    }
    assert isinstance(distribution[2]['asset'], str)
    assert distribution[2] == {
        'time': 1488326400,
        'asset': 'XMR',
        'amount': '5',
        'usd_value': '135.6',
    }
    assert distribution[3] == {
        'time': 1488326400,
        'asset': 'EUR',
        'amount': '100',
        'usd_value': '61.5',
    }
    assert isinstance(distribution[3]['asset'], str)


def test_set_settings(rotkehlchen_server):
    # Test that failing to connect to an rpc endpoint returns an error
    given_settings = {
        'eth_rpc_endpoint': 'http://foo.boo.nodes.com:8545',
    }
    response = rotkehlchen_server.set_settings(given_settings)
    assert response['result'] is True
    assert 'Failed to connect to ethereum node at endpoint' in response['message']
    settings = rotkehlchen_server.get_settings()
    assert settings['eth_rpc_endpoint'] == 'http://localhost:8545'

    # Test that when connection is a success all is good with the set value
    given_settings = {
        'eth_rpc_endpoint': 'http://working.nodes.com:8545',
    }
    block_query = patch('rotkehlchen.ethchain.Ethchain.query_eth_highest_block', return_value=0)
    mock_web3 = patch('rotkehlchen.ethchain.Web3', MockWeb3)
    with block_query, mock_web3:
        response = rotkehlchen_server.set_settings(given_settings)
    assert response['result'] is True
    assert response['message'] == ''
    settings = rotkehlchen_server.get_settings()
    assert settings['eth_rpc_endpoint'] == 'http://working.nodes.com:8545'

    # Test that changing the main currency to a valid fiat works
    given_settings = {
        'main_currency': 'CAD',
    }
    response = rotkehlchen_server.set_settings(given_settings)
    assert response['result'] is True
    assert response['message'] == ''
    settings = rotkehlchen_server.get_settings()
    assert settings['main_currency'] == 'CAD'

    # Test that using a nonsence currency for main currencly fails with message
    given_settings = {
        'main_currency': 'XDADADAD',
    }
    response = rotkehlchen_server.set_settings(given_settings)
    assert response['result'] is False
    assert response['message'] == 'Unknown fiat currency XDADADAD provided'
    settings = rotkehlchen_server.get_settings()
    assert settings['main_currency'] == 'CAD'

    # Test that using a crypto currency for main currency fails with message
    given_settings = {
        'main_currency': 'BTC',
    }
    response = rotkehlchen_server.set_settings(given_settings)
    assert response['result'] is False
    assert response['message'] == 'Provided symbol for main currency BTC is not a fiat currency'
    settings = rotkehlchen_server.get_settings()
    assert settings['main_currency'] == 'CAD'


def test_ignored_assets(rotkehlchen_server):
    response = rotkehlchen_server.get_ignored_assets()
    assert response['ignored_assets'] == []

    response = rotkehlchen_server.add_ignored_asset('RDN')
    assert response['result'] is True
    assert response['message'] == ''

    response = rotkehlchen_server.add_ignored_asset('GNO')
    assert response['result'] is True
    assert response['message'] == ''

    response = rotkehlchen_server.get_ignored_assets()
    assert response['ignored_assets'] == ['GNO', 'RDN']

    # Test that adding an unknown asset is an error
    response = rotkehlchen_server.add_ignored_asset('ADSAD')
    assert response['result'] is False
    assert response['message'] == 'Given asset ADSAD for ignoring is not known/supported'

    # Test that adding an already ignored asset is an error
    response = rotkehlchen_server.add_ignored_asset('RDN')
    assert response['result'] is False
    assert response['message'] == 'RDN is already in ignored assets'

    # Test that removing works
    response = rotkehlchen_server.remove_ignored_asset('RDN')
    assert response['result'] is True
    assert response['message'] == ''

    response = rotkehlchen_server.get_ignored_assets()
    assert response['ignored_assets'] == ['GNO']

    # Test that removing an unknown asset is an error
    response = rotkehlchen_server.remove_ignored_asset('DSADAD')
    assert response['result'] is False
    assert response['message'] == 'Given asset DSADAD for ignoring is not known/supported'

    # Test that removing a non-ignored asset is an error
    response = rotkehlchen_server.remove_ignored_asset('BTC')
    assert response['result'] is False
    assert response['message'] == 'BTC is not in ignored assets'


def test_query_exchange_balances(rotkehlchen_server, function_scope_binance):
    """Just test that querying an exchange's balance via the server works

    Here we only have binance registered
    """
    exchanges = rotkehlchen_server.rotkehlchen.exchange_manager.connected_exchanges
    exchanges['binance'] = function_scope_binance

    def mock_binance_balances(url):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

    mock_binance = patch.object(
        exchanges['binance'].session,
        'get',
        side_effect=mock_binance_balances,
    )
    with mock_binance:
        result = rotkehlchen_server.query_exchange_balances('binance')

    # no need to check the exact results, just want to make sure the query works
    assert 'BTC' in result['balances']
    assert 'ETH' in result['balances']

    # also check that querying a non-registered exchange returns an error
    result = rotkehlchen_server.query_exchange_balances('poloniex')
    assert result['error'] == 'Could not query balances for poloniex since it is not registered'


def test_query_trade_history(rotkehlchen_server, function_scope_bittrex, function_scope_poloniex):
    """Just test that querying an exchange's trade history via the server api works

    Here we only have bittrex and poloniex registered
    """
    rotki = rotkehlchen_server.rotkehlchen
    exchanges = rotki.exchange_manager.connected_exchanges
    exchanges['bittrex'] = function_scope_bittrex
    exchanges['poloniex'] = function_scope_poloniex
    exchanges['poloniex'].cache_ttl_secs = 0
    exchanges['bittrex'].cache_ttl_secs = 0

    _, polo_patch, _, bittrex_patch, _ = mock_history_processing_and_exchanges(rotki)

    # only poloniex
    with polo_patch:
        result = rotkehlchen_server.query_trade_history('poloniex', start_ts=0, end_ts=TEST_END_TS)

    assert len(result['result']) == 3
    # And also test serialization of one trade
    trade = result['result'][0]
    assert trade['timestamp'] == 1539713117
    assert trade['location'] == 'poloniex'
    assert trade['pair'] == 'ETH_BTC'
    assert trade['trade_type'] == 'sell'
    assert trade['amount'] == '1.40308443'
    assert trade['rate'] == '0.06935244'
    assert trade['fee'] == '0.0000973073287465092'
    assert trade['fee_currency'] == 'BTC'
    assert trade['link'] == ''
    assert trade['notes'] == ''

    # only bittrex
    with bittrex_patch:
        result = rotkehlchen_server.query_trade_history('bittrex', start_ts=0, end_ts=TEST_END_TS)

    assert len(result['result']) == 2

    # all exchanges (both poloniex and bittrex)
    with polo_patch, bittrex_patch:
        result = rotkehlchen_server.query_trade_history('all', start_ts=0, end_ts=TEST_END_TS)

    assert len(result['result']) == 5

    # also check that querying a non-registered exchange returns an error
    result = rotkehlchen_server.query_trade_history('binance', start_ts=0, end_ts=TEST_END_TS)
    msg = 'Exchange binance provided in query_trade_history is not registered yet for this user'
    assert result['message'] == msg

    # also check that querying an invalid exchange returns an error
    result = rotkehlchen_server.query_trade_history('dasdsd', start_ts=0, end_ts=TEST_END_TS)
    assert result['message'] == 'Unknown exchange dasdsd provided in query_trade_history'
