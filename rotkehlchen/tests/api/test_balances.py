import random
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.bitcoin import get_bitcoin_addresses_balances
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.balances import get_asset_balance_total
from rotkehlchen.tests.utils.blockchain import (
    assert_btc_balances_result,
    assert_eth_balances_result,
)
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.exchanges import (
    assert_binance_balances_result,
    try_get_first_exchange,
)
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup, setup_balances
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_TEST_NODES,
    SUBSTRATE_ACC1_KSM_ADDR,
    SUBSTRATE_ACC2_KSM_ADDR,
)
from rotkehlchen.typing import Location, SupportedBlockchain, Timestamp


def assert_all_balances(
        result,
        db,
        expected_data_in_db,
        setup: BalancesTestSetup,
) -> None:
    total_eth = get_asset_balance_total(A_ETH, setup)
    total_rdn = get_asset_balance_total(A_RDN, setup)
    total_btc = get_asset_balance_total(A_BTC, setup)
    total_eur = get_asset_balance_total(A_EUR, setup)

    got_external = any(x.location == Location.EXTERNAL for x in setup.manually_tracked_balances)

    assert len(result) == 4
    assert result['liabilities'] == {}
    assets = result['assets']
    assert FVal(assets['ETH']['amount']) == total_eth
    assert assets['ETH']['usd_value'] is not None
    assert assets['ETH']['percentage_of_net_value'] is not None
    assert FVal(assets[A_RDN.identifier]['amount']) == total_rdn
    assert assets[A_RDN.identifier]['usd_value'] is not None
    assert assets[A_RDN.identifier]['percentage_of_net_value'] is not None
    assert FVal(assets['BTC']['amount']) == total_btc
    assert assets['BTC']['usd_value'] is not None
    assert assets['BTC']['percentage_of_net_value'] is not None
    if total_eur != ZERO:
        assert FVal(assets['EUR']['amount']) == total_eur
        assert assets['EUR']['percentage_of_net_value'] is not None

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

    eth_tbalances = db.query_timed_balances(asset=A_ETH)
    if not expected_data_in_db:
        assert len(eth_tbalances) == 0
    else:
        assert len(eth_tbalances) == 1
        assert FVal(eth_tbalances[0].amount) == total_eth

    btc_tbalances = db.query_timed_balances(asset=A_BTC)
    if not expected_data_in_db:
        assert len(btc_tbalances) == 0
    else:
        assert len(btc_tbalances) == 1
        assert FVal(btc_tbalances[0].amount) == total_btc

    rdn_tbalances = db.query_timed_balances(asset=A_RDN)
    if not expected_data_in_db:
        assert len(rdn_tbalances) == 0
    else:
        assert len(rdn_tbalances) == 1
        assert FVal(rdn_tbalances[0].amount) == total_rdn

    times, net_values = db.get_netvalue_data(Timestamp(0))
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
            Location.POLONIEX.serialize_for_db(),  # pylint: disable=no-member
            Location.BINANCE.serialize_for_db(),  # pylint: disable=no-member
            Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
            Location.BLOCKCHAIN.serialize_for_db(),  # pylint: disable=no-member
        }
        if got_external:
            expected_locations.add(Location.EXTERNAL.serialize_for_db())  # pylint: disable=no-member  # noqa: E501
        if total_eur != ZERO:
            expected_locations.add(Location.BANKS.serialize_for_db())  # pylint: disable=no-member
        locations = {x.location for x in location_data}
        assert locations == expected_locations


# Use real current price querying in this test since it's very extensive
# and we can make sure that we can query current prices properly in the real app
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_all_balances(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the query all balances endpoint works

    Test that balances from various sources are returned. Such as exchanges,
    blockchain and manually tracked balances"""
    async_query = random.choice([False, True])
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
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(
                rotkehlchen_api_server_with_exchanges,
                task_id,
            )
        else:
            outcome = assert_proper_response_with_result(response)

    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert_all_balances(
        result=outcome,
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
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_all_balances_ignore_cache(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the query all balances endpoint can ignore the cache"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
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
    original_binance_query_dict = binance.api_query_dict
    binance_query_patch = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)
    poloniex_query_patch = patch.object(poloniex, 'api_query_dict', wraps=poloniex.api_query_dict)

    with ExitStack() as stack:
        stack.enter_context(setup.poloniex_patch)
        stack.enter_context(setup.binance_patch)
        etherscan_mock = stack.enter_context(setup.etherscan_patch)
        stack.enter_context(setup.bitcoin_patch)
        stack.enter_context(setup.ethtokens_max_chunks_patch)
        stack.enter_context(setup.beaconchain_patch)
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
        result = assert_proper_response_with_result(response)
        assert_all_balances(
            result=result,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        for fn in function_call_counters:
            if fn._mock_wraps == original_binance_query_dict:
                assert fn.call_count == 3
            else:
                assert fn.call_count == 1
        full_query_etherscan_count = etherscan_mock.call_count

        # Query all balances second time and assert cache was used
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ),
        )
        result = assert_proper_response_with_result(response)
        assert_all_balances(
            result=result,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        msg = 'call count should stay the same since cache should have been used'
        for fn in function_call_counters:
            if fn._mock_wraps == original_binance_query_dict:
                assert fn.call_count == 3, msg
            else:
                assert fn.call_count == 1, msg
        msg = 'etherscan call_count should have remained the same due to no token detection '
        assert etherscan_mock.call_count == full_query_etherscan_count, msg

        # Now query all balances but request cache ignoring
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        assert_all_balances(
            result=result,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        msg = 'call count should increase since cache should have been ignored'
        for fn in function_call_counters:
            if fn._mock_wraps == original_binance_query_dict:
                assert fn.call_count == 6, msg
            else:
                assert fn.call_count == 2, msg
        msg = 'etherscan call count should have doubled after forced token detection'
        # TODO: Figure out a correct formula for this
        expected_count = full_query_etherscan_count * 2 - 1
        assert etherscan_mock.call_count == expected_count, msg


@pytest.mark.parametrize('tags', [[{
    'name': 'private',
    'description': 'My private accounts',
    'background_color': 'ffffff',
    'foreground_color': '000000',
}]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
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
    result = assert_proper_response_with_result(response)
    assert_all_balances(
        result=result,
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
@pytest.mark.parametrize('separate_blockchain_calls', [True, False])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_multiple_balance_queries_not_concurrent(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        separate_blockchain_calls,
):
    """Test multiple different balance query requests happening concurrently

    This tests that if multiple balance query requests happen concurrently we
    do not end up doing them multiple times, but reuse the results thanks to cache.

    Try running both all blockchain balances in one call and each blockchain call separately.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    multieth_balance_patch = patch.object(
        rotki.chain_manager.ethereum,
        'get_multieth_balance',
        wraps=rotki.chain_manager.ethereum.get_multieth_balance,
    )
    btc_balances_patch = patch(
        'rotkehlchen.chain.manager.get_bitcoin_addresses_balances',
        wraps=get_bitcoin_addresses_balances,
    )
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    binance_querydict_patch = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)

    # Test all balances request by requesting to not save the data
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        eth = stack.enter_context(multieth_balance_patch)
        btc = stack.enter_context(btc_balances_patch)
        bn = stack.enter_context(binance_querydict_patch)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'async_query': True},
        )
        task_id_all = assert_ok_async_response(response)
        response = requests.get(api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "named_exchanges_balances_resource",
            location='binance',
        ), json={'async_query': True})
        task_id_one_exchange = assert_ok_async_response(response)
        if separate_blockchain_calls:
            response = requests.get(api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "blockchainbalancesresource",
            ), json={'async_query': True, 'blockchain': 'ETH'})
            task_id_blockchain_eth = assert_ok_async_response(response)
            response = requests.get(api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "blockchainbalancesresource",
            ), json={'async_query': True, 'blockchain': 'BTC'})
            task_id_blockchain_btc = assert_ok_async_response(response)
        else:
            response = requests.get(api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "blockchainbalancesresource",
            ), json={'async_query': True})
            task_id_blockchain = assert_ok_async_response(response)

        outcome_all = wait_for_async_task_with_result(
            rotkehlchen_api_server_with_exchanges,
            task_id_all,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 2,
        )
        outcome_one_exchange = wait_for_async_task(
            rotkehlchen_api_server_with_exchanges,
            task_id_one_exchange,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 2,
        )
        if separate_blockchain_calls:
            outcome_eth = wait_for_async_task_with_result(
                rotkehlchen_api_server_with_exchanges,
                task_id_blockchain_eth,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 2,
            )
            outcome_btc = wait_for_async_task_with_result(
                rotkehlchen_api_server_with_exchanges,
                task_id_blockchain_btc,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 2,
            )
        else:
            outcome_blockchain = wait_for_async_task_with_result(
                rotkehlchen_api_server_with_exchanges,
                task_id_blockchain,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 2,
            )
        assert eth.call_count == 1, 'eth balance query should only fire once'
        assert btc.call_count == 1, 'btc balance query should only happen once'
        assert bn.call_count == 3, 'binance balance query should do 2 calls'

    assert_all_balances(
        result=outcome_all,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )
    assert_binance_balances_result(outcome_one_exchange['result'])
    if not separate_blockchain_calls:
        outcome_eth = outcome_blockchain
        outcome_btc = outcome_blockchain

    assert_eth_balances_result(
        rotki=rotki,
        result=outcome_eth,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=not separate_blockchain_calls,
    )
    assert_btc_balances_result(
        result=outcome_btc,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=not separate_blockchain_calls,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [1])
def test_balances_caching_mixup(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that querying the balances in a specific order does not mix up the caches.

    This tests for the problem seen where the bitcoin balances being empty and
    queried first returned an empty result for the ethereum balances.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=['1000000000000000000'],
        token_balances={A_RDN: ['2000000000000000000']},
        original_queries=['zerion'],
    )

    # Test all balances request by requesting to not save the data
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response_btc = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='BTC',
        ), json={'async_query': True})
        response_eth = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ), json={'async_query': True})
        task_id_btc = assert_ok_async_response(response_btc)
        task_id_eth = assert_ok_async_response(response_eth)
        result_btc = wait_for_async_task_with_result(
            rotkehlchen_api_server,
            task_id_btc,
        )
        result_eth = wait_for_async_task_with_result(
            server=rotkehlchen_api_server,
            task_id=task_id_eth,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 2,
        )
        assert result_eth['per_account']['ETH'][ethereum_accounts[0]]['assets']['ETH']['amount'] == '1'  # noqa: E501
        assert result_eth['per_account']['ETH'][ethereum_accounts[0]]['assets'][A_RDN.identifier]['amount'] == '2'  # noqa: E501
        assert result_eth['totals']['assets']['ETH']['amount'] == '1'
        assert result_eth['totals']['assets'][A_RDN.identifier]['amount'] == '2'
        assert result_eth['per_account']['ETH'][ethereum_accounts[0]]['assets'][A_RDN.identifier]['amount'] == '2'  # noqa: E501
        assert result_btc['per_account'] == {}
        assert result_btc['totals']['assets'] == {}
        assert result_btc['totals']['liabilities'] == {}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, SUBSTRATE_ACC2_KSM_ADDR]])
def test_query_ksm_balances(rotkehlchen_api_server):
    """Test query the KSM balances when multiple accounts are set up works as
    expected.
    """
    async_query = random.choice([False, True])
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                "named_blockchain_balances_resource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    # Check per account
    account_1_balances = result['per_account']['KSM'][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_1_balances
    asset_ksm = account_1_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    account_2_balances = result['per_account']['KSM'][SUBSTRATE_ACC2_KSM_ADDR]
    assert 'liabilities' in account_2_balances
    asset_ksm = account_2_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO
