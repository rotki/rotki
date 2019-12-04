from http import HTTPStatus

import pytest
import requests

from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.blockchain import mock_etherscan_balances_query
from rotkehlchen.tests.utils.constants import A_CNY, A_RDN
from rotkehlchen.tests.utils.exchanges import (
    patch_binance_balances_query,
    patch_poloniex_balances_query,
)
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.typing import Location
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc


def assert_all_balances(
        data,
        db,
        expected_data_in_db,
        eth_balances,
        btc_balances,
        rdn_balances,
        fiat_balances,
        binance_balances,
        poloniex_balances,
) -> None:
    result = data['result']

    total_eth = ZERO
    total_eth += sum(from_wei(FVal(b)) for b in eth_balances)
    total_eth += binance_balances.get('ETH', ZERO)
    total_eth += poloniex_balances.get('ETH', ZERO)

    total_rdn = ZERO
    total_rdn += sum(from_wei(FVal(b)) for b in rdn_balances)
    total_rdn += binance_balances.get('RDN', ZERO)
    total_rdn += poloniex_balances.get('RDN', ZERO)

    total_btc = ZERO
    total_btc += sum(satoshis_to_btc(FVal(b)) for b in btc_balances)
    total_btc += binance_balances.get('BTC', ZERO)
    total_btc += poloniex_balances.get('BTC', ZERO)

    assert FVal(result['ETH']['amount']) == total_eth
    assert result['ETH']['usd_value'] is not None
    assert result['ETH']['percentage_of_net_value'] is not None
    assert FVal(result['RDN']['amount']) == total_rdn
    assert result['RDN']['usd_value'] is not None
    assert result['RDN']['percentage_of_net_value'] is not None
    assert FVal(result['BTC']['amount']) == total_btc
    assert result['BTC']['usd_value'] is not None
    assert result['BTC']['percentage_of_net_value'] is not None
    assert FVal(result['EUR']['amount']) == fiat_balances['EUR']
    assert result['BTC']['usd_value'] is not None
    assert result['EUR']['percentage_of_net_value'] is not None

    assert result['net_usd'] is not None
    # Check that the 4 locations are there
    assert len(result['location']) == 4
    assert result['location']['binance']['usd_value'] is not None
    assert result['location']['binance']['percentage_of_net_value'] is not None
    assert result['location']['poloniex']['usd_value'] is not None
    assert result['location']['poloniex']['percentage_of_net_value'] is not None
    assert result['location']['blockchain']['usd_value'] is not None
    assert result['location']['blockchain']['percentage_of_net_value'] is not None
    assert result['location']['banks']['usd_value'] is not None
    assert result['location']['banks']['percentage_of_net_value'] is not None
    assert len(result) == 6  # 4 assets + location + net_usd

    eth_tbalances = db.query_timed_balances(from_ts=None, to_ts=None, asset=A_ETH)
    if not expected_data_in_db:
        assert len(eth_tbalances) == 0
    else:
        assert len(eth_tbalances) == 1
        assert FVal(eth_tbalances[0].amount) == total_eth

    btc_tbalances = db.query_timed_balances(from_ts=None, to_ts=None, asset=A_BTC)
    if not expected_data_in_db:
        assert len(btc_tbalances) == 0
    else:
        assert len(btc_tbalances) == 1
        assert FVal(btc_tbalances[0].amount) == total_btc

    rdn_tbalances = db.query_timed_balances(from_ts=None, to_ts=None, asset=A_RDN)
    if not expected_data_in_db:
        assert len(rdn_tbalances) == 0
    else:
        assert len(rdn_tbalances) == 1
        assert FVal(rdn_tbalances[0].amount) == total_rdn

    times, net_values = db.get_netvalue_data()
    if not expected_data_in_db:
        assert len(times) == 0
        assert len(net_values) == 0
    else:
        assert len(times) == 1
        assert len(net_values) == 1

    location_data = db.get_latest_location_value_distribution()
    if not expected_data_in_db:
        assert len(location_data) == 0
    else:
        assert len(location_data) == 5
        assert location_data[0].location == Location.POLONIEX.serialize_for_db()
        assert location_data[1].location == Location.BINANCE.serialize_for_db()
        assert location_data[2].location == Location.TOTAL.serialize_for_db()
        assert location_data[3].location == Location.BANKS.serialize_for_db()
        assert location_data[4].location == Location.BLOCKCHAIN.serialize_for_db()


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """Test that using the query all balances endpoint works

    Test that balances from various sources are returned. Such as exchanges,
    blockchain and FIAT"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.blockchain.cache_ttl_secs = 0

    eth_acc1 = ethereum_accounts[0]
    eth_acc2 = ethereum_accounts[1]
    eth_balance1 = '1000000'
    eth_balance2 = '2000000'
    eth_balances = [eth_balance1, eth_balance2]
    btc_balance1 = '3000000'
    btc_balance2 = '5000000'
    btc_balances = [btc_balance1, btc_balance2]
    rdn_balance = '4000000'
    eur_balance = FVal('1550')

    rotki.data.db.add_fiat_balance(A_EUR, eur_balance)
    binance = rotki.exchange_manager.connected_exchanges['binance']
    poloniex = rotki.exchange_manager.connected_exchanges['poloniex']
    poloniex_patch = patch_poloniex_balances_query(poloniex)
    binance_patch = patch_binance_balances_query(binance)
    blockchain_patch = mock_etherscan_balances_query(
        eth_map={
            eth_acc1: {'ETH': eth_balance1},
            eth_acc2: {'ETH': eth_balance2, 'RDN': rdn_balance},
        },
        btc_map={btc_accounts[0]: btc_balance1, btc_accounts[1]: btc_balance2},
        original_requests_get=requests.get,
    )
    # Taken from BINANCE_BALANCES_RESPONSE from tests.utils.exchanges
    binance_balances = {'ETH': FVal('4763368.68006011'), 'BTC': FVal('4723846.89208129')}
    # Taken from POLONIEX_BALANCES_RESPONSE from tests.utils.exchanges
    poloniex_balances = {'ETH': FVal('11.0'), 'BTC': FVal('5.5')}

    # Test all balances request by requesting to not save the data
    with poloniex_patch, binance_patch, blockchain_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': False}
        )

    assert_proper_response(response)
    json_data = response.json()
    assert_all_balances(
        data=json_data,
        db=rotki.data.db,
        expected_data_in_db=False,
        eth_balances=eth_balances,
        btc_balances=btc_balances,
        rdn_balances=[rdn_balance],
        fiat_balances={A_EUR: eur_balance},
        binance_balances=binance_balances,
        poloniex_balances=poloniex_balances,
    )

    # now do the same but save the data in the DB and test it works
    # Omit the argument to test that default value of save_data is True
    with poloniex_patch, binance_patch, blockchain_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            )
        )
    assert_proper_response(response)
    json_data = response.json()
    assert_all_balances(
        data=json_data,
        db=rotki.data.db,
        expected_data_in_db=True,
        eth_balances=eth_balances,
        btc_balances=btc_balances,
        rdn_balances=[rdn_balance],
        fiat_balances={A_EUR: eur_balance},
        binance_balances=binance_balances,
        poloniex_balances=poloniex_balances,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances_async(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """Test that using the query all balances endpoint works with async call"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.blockchain.cache_ttl_secs = 0

    eth_acc1 = ethereum_accounts[0]
    eth_acc2 = ethereum_accounts[1]
    eth_balance1 = '1000000'
    eth_balance2 = '2000000'
    eth_balances = [eth_balance1, eth_balance2]
    btc_balance1 = '3000000'
    btc_balance2 = '5000000'
    btc_balances = [btc_balance1, btc_balance2]
    rdn_balance = '4000000'
    eur_balance = FVal('1550')

    rotki.data.db.add_fiat_balance(A_EUR, eur_balance)
    binance = rotki.exchange_manager.connected_exchanges['binance']
    poloniex = rotki.exchange_manager.connected_exchanges['poloniex']
    poloniex_patch = patch_poloniex_balances_query(poloniex)
    binance_patch = patch_binance_balances_query(binance)
    blockchain_patch = mock_etherscan_balances_query(
        eth_map={
            eth_acc1: {'ETH': eth_balance1},
            eth_acc2: {'ETH': eth_balance2, 'RDN': rdn_balance},
        },
        btc_map={btc_accounts[0]: btc_balance1, btc_accounts[1]: btc_balance2},
        original_requests_get=requests.get,
    )
    # Taken from BINANCE_BALANCES_RESPONSE from tests.utils.exchanges
    binance_balances = {'ETH': FVal('4763368.68006011'), 'BTC': FVal('4723846.89208129')}
    # Taken from POLONIEX_BALANCES_RESPONSE from tests.utils.exchanges
    poloniex_balances = {'ETH': FVal('11.0'), 'BTC': FVal('5.5')}

    # Test all balances request by requesting to not save the data
    with poloniex_patch, binance_patch, blockchain_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'async_query': True}
        )
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)

    assert_all_balances(
        data=outcome,
        db=rotki.data.db,
        expected_data_in_db=True,
        eth_balances=eth_balances,
        btc_balances=btc_balances,
        rdn_balances=[rdn_balance],
        fiat_balances={A_EUR: eur_balance},
        binance_balances=binance_balances,
        poloniex_balances=poloniex_balances,
    )


def test_query_all_balances_errors(rotkehlchen_api_server):
    """Test that errors are handled correctly by the all balances endpoint"""
    # invoke the endpoint with non boolean save_data
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "allbalancesresource",
        ), json={'save_data': 14545}
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # invoke the endpoint with non boolean async_query
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "allbalancesresource",
        ), json={'async_query': 14545}
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def assert_fiat_balances(data, eur_balance, cny_balance, usd_balance, cny_deleted=False):
    """Convenience assertion function for the fiat balance tests"""
    assert data['message'] == ''
    if cny_deleted:
        assert len(data['result']) == 2
    else:
        assert len(data['result']) == 3
    assert FVal(data['result']['EUR']['amount']) == eur_balance
    assert data['result']['EUR']['usd_value'] is not None
    assert FVal(data['result']['USD']['amount']) == usd_balance
    assert data['result']['USD']['usd_value'] is not None
    if not cny_deleted:
        assert FVal(data['result']['CNY']['amount']) == cny_balance
        assert data['result']['CNY']['usd_value'] is not None


def test_query_fiat_balances(rotkehlchen_api_server):
    """Test that querying FIAT balances works"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    eur_balance = FVal('1550')
    cny_balance = FVal('250500.51')
    usd_balance = FVal('4520.32')

    # Have the balances set already in the DB
    rotki.data.db.add_fiat_balance(A_EUR, eur_balance)
    rotki.data.db.add_fiat_balance(A_CNY, cny_balance)
    rotki.data.db.add_fiat_balance(A_USD, usd_balance)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        )
    )

    # Check that the DB balances match what is returned
    assert_proper_response(response)
    assert_fiat_balances(response.json(), eur_balance, cny_balance, usd_balance)


def test_settting_fiat_balances(rotkehlchen_api_server):
    """Test that setting FIAT balances works"""
    eur_balance = FVal('1550')
    cny_balance = FVal('250500.51')
    usd_balance = FVal('4520.32')

    # Check that setting the fiat balances via the API works
    balances = {'EUR': str(eur_balance), 'CNY': str(cny_balance), 'USD': str(usd_balance)}
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'balances': balances},
    )
    assert_proper_response(response)
    assert_fiat_balances(response.json(), eur_balance, cny_balance, usd_balance)

    # Check that requesting the set balances works
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        )
    )
    assert_proper_response(response)
    assert_fiat_balances(response.json(), eur_balance, cny_balance, usd_balance)

    # Check that setting a balance to 0 deletes the entry
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'balances': {'CNY': '0'}},
    )
    assert_proper_response(response)
    assert_fiat_balances(response.json(), eur_balance, cny_balance, usd_balance, cny_deleted=True)

    # Also check it's not in the DB
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert 'CNY' not in rotki.data.db.get_fiat_balances()


def test_settting_fiat_balances_errors(rotkehlchen_api_server):
    """Test for error handling of the FIAT balances endpoint"""
    # Check that not setting the balances results in failure
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'ddsaad': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that not non-dict balances result in failure
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'balances': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid mapping type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that non-valid amount is properly handled
    balances = {'EUR': '1500', 'CNY': 'dasdsad'}
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'balances': balances},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize an amount entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that non-valid asset is properly handled
    balances = {'EUR': '1500', 'DSADSDADASD': '55'}
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'balances': balances},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset DSADSDADASD provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that non-FIAT asset is an error and properly handled
    balances = {'EUR': '1500', 'ETH': '55'}
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "fiatbalancesresource",
        ), json={'balances': balances},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Asset ETH is not a FIAT asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )
