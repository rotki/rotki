from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.balances import get_asset_balance_total
from rotkehlchen.tests.utils.blockchain import assert_eth_balances_result
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.exchanges import assert_binance_balances_result
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup, setup_balances
from rotkehlchen.typing import Location


def assert_all_balances(
        data,
        db,
        expected_data_in_db,
        setup: BalancesTestSetup,
) -> None:
    result = data['result']
    total_eth = get_asset_balance_total('ETH', setup)
    total_rdn = get_asset_balance_total('RDN', setup)
    total_btc = get_asset_balance_total('BTC', setup)
    total_eur = get_asset_balance_total('EUR', setup)

    got_external = any(x.location == Location.EXTERNAL for x in setup.manually_tracked_balances)

    expected_result_keys = 5
    assert FVal(result['ETH']['amount']) == total_eth
    assert result['ETH']['usd_value'] is not None
    assert result['ETH']['percentage_of_net_value'] is not None
    assert FVal(result['RDN']['amount']) == total_rdn
    assert result['RDN']['usd_value'] is not None
    assert result['RDN']['percentage_of_net_value'] is not None
    assert FVal(result['BTC']['amount']) == total_btc
    assert result['BTC']['usd_value'] is not None
    assert result['BTC']['percentage_of_net_value'] is not None
    if total_eur != ZERO:
        assert FVal(result['EUR']['amount']) == total_eur
        assert result['EUR']['percentage_of_net_value'] is not None
        expected_result_keys += 1

    assert result['net_usd'] is not None
    # Check that the 4 locations are there
    assert len(result['location']) == 5 if got_external else 4
    assert result['location']['binance']['usd_value'] is not None
    assert result['location']['binance']['percentage_of_net_value'] is not None
    assert result['location']['poloniex']['usd_value'] is not None
    assert result['location']['poloniex']['percentage_of_net_value'] is not None
    assert result['location']['blockchain']['usd_value'] is not None
    assert result['location']['blockchain']['percentage_of_net_value'] is not None
    if total_eur != ZERO:
        assert result['location']['banks']['usd_value'] is not None
        assert result['location']['banks']['percentage_of_net_value'] is not None
    if got_external:
        assert result['location']['external']['usd_value'] is not None
        assert result['location']['external']['percentage_of_net_value'] is not None

    assert len(result) == expected_result_keys  # 3 or 4 assets + location + net_usd

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
        expected_locations = {
            Location.POLONIEX.serialize_for_db(),
            Location.BINANCE.serialize_for_db(),
            Location.TOTAL.serialize_for_db(),
            Location.BLOCKCHAIN.serialize_for_db(),
        }
        if got_external:
            expected_locations.add(Location.EXTERNAL.serialize_for_db())
        if total_eur != ZERO:
            expected_locations.add(Location.BANKS.serialize_for_db())
        locations = {x.location for x in location_data}
        assert locations == expected_locations


# Use real current price querying in this test since it's very extensive
# and we can make sure that we can query current prices properly in the real app
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the query all balances endpoint works

    Test that balances from various sources are returned. Such as exchanges,
    blockchain and manually tracked balances"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=[ManuallyTrackedBalance(
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal('1550'),
            location=Location.BANKS,
            tags=None,
        )],
    )
    # Test that all balances request saves data on a fresh account
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ),
        )

    assert_proper_response(response)
    json_data = response.json()
    assert_all_balances(
        data=json_data,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )

    last_save_timestamp = rotki.data.db.get_last_balance_save_time()

    # now do the same but check to see if the balance save frequency delay works
    # and thus data will not be saved
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ),
        )
    assert_proper_response(response)
    new_save_timestamp = rotki.data.db.get_last_balance_save_time()
    assert last_save_timestamp == new_save_timestamp

    # wait for at least 1 second to make sure that new balances can be saved.
    # Can't save balances again if it's the same timestamp
    gevent.sleep(1)
    # now do the same but test that balance are saved since the balance save frequency delay
    # is overriden via `save_data` = True
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': True},
        )
    assert_proper_response(response)
    new_save_timestamp = rotki.data.db.get_last_balance_save_time()
    assert last_save_timestamp != new_save_timestamp


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances_async(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the query all balances endpoint works with async call"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    # Test all balances request by requesting to not save the data
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'async_query': True},
        )
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)

    assert_all_balances(
        data=outcome,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances_ignore_cache(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the query all balances endpoint can ignore the cache"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)
    binance = rotki.exchange_manager.connected_exchanges['binance']
    poloniex = rotki.exchange_manager.connected_exchanges['poloniex']
    eth_query_patch = patch.object(
        rotki.chain_manager,
        'query_ethereum_balances',
        wraps=rotki.chain_manager.query_ethereum_balances,
    )
    btc_query_patch = patch.object(
        rotki.chain_manager,
        'query_btc_balances',
        wraps=rotki.chain_manager.query_btc_balances,
    )
    tokens_query_patch = patch.object(
        rotki.chain_manager,
        'query_ethereum_tokens',
        wraps=rotki.chain_manager.query_ethereum_tokens,
    )
    binance_query_patch = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)
    poloniex_query_patch = patch.object(poloniex, 'api_query_dict', wraps=poloniex.api_query_dict)

    with ExitStack() as stack:
        stack.enter_context(setup.poloniex_patch)
        stack.enter_context(setup.binance_patch)
        etherscan_mock = stack.enter_context(setup.etherscan_patch)
        stack.enter_context(setup.bitcoin_patch)
        function_call_counters = []
        function_call_counters.append(stack.enter_context(eth_query_patch))
        function_call_counters.append(stack.enter_context(btc_query_patch))
        function_call_counters.append(stack.enter_context(tokens_query_patch))
        function_call_counters.append(stack.enter_context(binance_query_patch))
        function_call_counters.append(stack.enter_context(poloniex_query_patch))

        # Query all balances for the first time and test it works
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ),
        )
        assert_proper_response(response)
        json_data = response.json()
        assert_all_balances(
            data=json_data,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        assert all(fn.call_count == 1 for fn in function_call_counters)
        full_query_etherscan_count = etherscan_mock.call_count

        # Query all balances second time and assert cache was used
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ),
        )
        assert_proper_response(response)
        json_data = response.json()
        assert_all_balances(
            data=json_data,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        msg = 'call count should stay the same since cache should have been used'
        assert all(fn.call_count == 1 for fn in function_call_counters), msg
        msg = 'etherscan call_count should have remained the same due to no token detection '
        assert etherscan_mock.call_count == full_query_etherscan_count, msg

        # Now query all balances but request cache ignoring
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'ignore_cache': True},
        )
        assert_proper_response(response)
        json_data = response.json()
        assert_all_balances(
            data=json_data,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        msg = 'call count should increase since cache should have been ignored'
        assert all(fn.call_count == 2 for fn in function_call_counters), msg
        msg = 'etherscan call count should have doubled after forced token detection'
        expected_count = full_query_etherscan_count * 2 - len(ethereum_accounts)
        assert etherscan_mock.call_count == expected_count, msg


@pytest.mark.parametrize('tags', [[{
    'name': 'private',
    'description': 'My private accounts',
    'background_color': 'ffffff',
    'foreground_color': '000000',
}]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances_with_manually_tracked_balances(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        manually_tracked_balances,
):
    """Test that using the query all balances endpoint also includes manually tracked balances"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    manually_tracked_balances = [ManuallyTrackedBalance(
        asset=A_BTC,
        label='XPUB BTC wallet',
        amount=FVal('10'),
        location=Location.BLOCKCHAIN,
        tags=None,
    ), ManuallyTrackedBalance(
        asset=A_BTC,
        label='BTC in hardware wallet',
        amount=FVal('20'),
        location=Location.BLOCKCHAIN,
        tags=['private'],
    ), ManuallyTrackedBalance(
        asset=A_ETH,
        label='ETH in a not supported exchange wallet',
        amount=FVal('10'),
        location=Location.EXTERNAL,
        tags=['private'],
    ), ManuallyTrackedBalance(
        asset=A_EUR,
        label='N26 account',
        amount=FVal('12500.15'),
        location=Location.BANKS,
        tags=None,
    ), ManuallyTrackedBalance(
        asset=A_EUR,
        label='Deutsche Bank account',
        amount=FVal('1337.1337'),
        location=Location.BANKS,
        tags=None,
    )]
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=manually_tracked_balances,
    )
    # now do the same but save the data in the DB and test it works
    # `save_data` is False by default but data will save since this is a fresh account
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ),
        )
    assert_proper_response(response)
    json_data = response.json()
    assert_all_balances(
        data=json_data,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )


def test_query_all_balances_errors(rotkehlchen_api_server):
    """Test that errors are handled correctly by the all balances endpoint"""
    # invoke the endpoint with non boolean save_data
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "allbalancesresource",
        ), json={'save_data': 14545},
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
        ), json={'async_query': 14545},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_multiple_balance_queries_not_concurrent(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test multiple different balance query requests happening concurrently

    This tests that if multiple balance query requests happen concurrently we
    do not end up doing them multiple times, but reuse the results thanks to cache.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    multieth_balance_patch = patch.object(
        rotki.chain_manager.ethereum,
        'get_multieth_balance',
        wraps=rotki.chain_manager.ethereum.get_multieth_balance,
    )
    binance = rotki.exchange_manager.connected_exchanges['binance']
    binance_querydict_patch = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)

    # Test all balances request by requesting to not save the data
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        eth = stack.enter_context(multieth_balance_patch)
        bn = stack.enter_context(binance_querydict_patch)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'async_query': True},
        )
        task_id_all = assert_ok_async_response(response)
        response = requests.get(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "named_exchanges_balances_resource",
            name='binance',
        ), json={'async_query': True})
        task_id_one_exchange = assert_ok_async_response(response)
        response = requests.get(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "blockchainbalancesresource",
        ), json={'async_query': True})
        task_id_blockchain = assert_ok_async_response(response)
        outcome_all = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id_all)
        outcome_one_exchange = wait_for_async_task(
            rotkehlchen_api_server_with_exchanges,
            task_id_one_exchange,
        )
        outcome_blockchain = wait_for_async_task_with_result(
            rotkehlchen_api_server_with_exchanges,
            task_id_blockchain,
        )
        assert eth.call_count == 1, 'blockchain balance call should not happen concurrently'
        assert bn.call_count == 1, 'binance balance call should not happen concurrently'

    assert_all_balances(
        data=outcome_all,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )
    assert_binance_balances_result(outcome_one_exchange['result'])
    assert_eth_balances_result(
        rotki=rotki,
        result=outcome_blockchain,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )
