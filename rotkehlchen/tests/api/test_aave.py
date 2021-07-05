import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.constants.assets import A_ADAI_V1, A_AWBTC_V1, A_WBTC, A_BUSD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.aave import (
    AAVE_TEST_ACC_1,
    AAVE_TEST_ACC_2,
    AAVE_TEST_ACC_3,
    aave_mocked_current_prices,
    aave_mocked_historical_prices,
    expected_aave_deposit_test_events,
    expected_aave_liquidation_test_events,
    expected_aave_v2_events,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup, setup_balances


AAVE_BALANCES_TEST_ACC = '0xC2cB1040220768554cf699b0d863A3cd4324ce32'
AAVE_V2_TEST_ACC = '0x008C00c45D461d7E08acBC4755a4A0a3a94115ee'


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCES_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
def test_query_aave_balances(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the aave balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "aavebalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCES_TEST_ACC} has no aave balances'))  # noqa: E501
        return

    lending = result[AAVE_BALANCES_TEST_ACC]['lending']
    for _, entry in lending.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    borrowing = result[AAVE_BALANCES_TEST_ACC]['borrowing']
    for _, entry in borrowing.items():
        assert len(entry) == 3
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['variable_apr']
        assert '%' in entry['stable_apr']


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_V2_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
@pytest.mark.parametrize('aave_use_graph', [True])
def test_query_aave_history_with_borrowing_v2(rotkehlchen_api_server, ethereum_accounts, aave_use_graph):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    _query_simple_aave_history_test_v2(setup, rotkehlchen_api_server, False)


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCES_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_aave_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "aavebalancesresource",
        ), json={'async_query': async_query})

        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['result'] is None
            assert outcome['message'] == 'aave module is not activated'
        else:
            assert_error_response(
                response=response,
                contained_in_msg='aave module is not activated',
                status_code=HTTPStatus.CONFLICT,
            )


def _query_simple_aave_history_test(
        setup: BalancesTestSetup,
        server: APIServer,
        async_query: bool,
        use_graph: bool,
) -> None:
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Big timeout since this test can take a long time
            outcome = wait_for_async_task(server, task_id, timeout=600)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result[AAVE_TEST_ACC_2]) == 4
    events = result[AAVE_TEST_ACC_2]['events']
    total_earned_interest = result[AAVE_TEST_ACC_2]['total_earned_interest']
    total_lost = result[AAVE_TEST_ACC_2]['total_lost']
    total_earned_liquidations = result[AAVE_TEST_ACC_2]['total_earned_liquidations']
    assert len(total_lost) == 0
    assert len(total_earned_liquidations) == 0
    assert len(total_earned_interest) == 1
    assert len(total_earned_interest[A_ADAI_V1.identifier]) == 2
    assert FVal(total_earned_interest[A_ADAI_V1.identifier]['amount']) >= FVal('24.207179802347627414')  # noqa: E501
    assert FVal(total_earned_interest[A_ADAI_V1.identifier]['usd_value']) >= FVal('24.580592532348742989192')  # noqa: E501

    expected_events = process_result_list(expected_aave_deposit_test_events)
    if use_graph:
        expected_events = expected_events[:7] + expected_events[8:]

    assert_serialized_lists_equal(
        a=events[:len(expected_events)],
        b=expected_events,
        ignore_keys=['log_index', 'block_number'] if use_graph else None,
    )


def _query_simple_aave_history_test_v2(
        setup: BalancesTestSetup,
        server: APIServer,
        async_query: bool,
) -> None:
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Big timeout since this test can take a long time
            outcome = wait_for_async_task(server, task_id, timeout=600)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result[AAVE_V2_TEST_ACC]) == 4
    events = result[AAVE_V2_TEST_ACC]['events']
    total_earned_interest = result[AAVE_V2_TEST_ACC]['total_earned_interest']
    total_lost = result[AAVE_V2_TEST_ACC]['total_lost']
    total_earned_liquidations = result[AAVE_V2_TEST_ACC]['total_earned_liquidations']
    assert len(total_lost) == 1
    assert len(total_earned_liquidations) == 0
    assert len(total_earned_interest) == 1
    assert len(total_earned_interest['_ceth_0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84']) == 2
    assert FVal(total_earned_interest['_ceth_0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84']['amount']) >= FVal('0.09')  # noqa: E501
    assert FVal(total_earned_interest['_ceth_0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84']['usd_value']) >= FVal('0.09248')  # noqa: E501

    assert_serialized_lists_equal(
        a=events[:len(expected_aave_v2_events)],
        b=process_result_list(expected_aave_v2_events),
        ignore_keys=None,
    )


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_2]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
@pytest.mark.parametrize('aave_use_graph', [True, False])  # Try both with blockchain and graph
def test_query_aave_history(rotkehlchen_api_server, ethereum_accounts, aave_use_graph):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data.

    Since this actually queries real blockchain data for aave it is a very slow test
    due to the sheer amount of log queries. We also use graph in 2nd version of test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    # Since this test is slow we don't run both async and sync in the same test run
    # Instead we randomly choose one. Eventually both cases will be covered.
    async_query = random.choice([True, False])

    _query_simple_aave_history_test(setup, rotkehlchen_api_server, async_query, aave_use_graph)

    if aave_use_graph:  # run it once more for graph to make sure DB querying gives same results
        _query_simple_aave_history_test(setup, rotkehlchen_api_server, async_query, aave_use_graph)


def _query_borrowing_aave_history_test(setup: BalancesTestSetup, server: APIServer) -> None:
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ))
        result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result[AAVE_TEST_ACC_3]) == 4
    events = result[AAVE_TEST_ACC_3]['events']
    total_earned_interest = result[AAVE_TEST_ACC_3]['total_earned_interest']
    total_lost = result[AAVE_TEST_ACC_3]['total_lost']
    total_earned_liquidations = result[AAVE_TEST_ACC_3]['total_earned_liquidations']

    assert len(total_earned_interest) >= 1
    assert len(total_earned_interest[A_AWBTC_V1.identifier]) == 2
    assert FVal(total_earned_interest[A_AWBTC_V1.identifier]['amount']) >= FVal('0.00000833')
    assert FVal(total_earned_interest[A_AWBTC_V1.identifier]['usd_value']) >= ZERO

    assert len(total_earned_liquidations) == 1
    assert len(total_earned_liquidations['ETH']) == 2
    assert FVal(total_earned_liquidations['ETH']['amount']) >= FVal('9.251070299427409111')
    assert FVal(total_earned_liquidations['ETH']['usd_value']) >= ZERO

    assert len(total_lost) == 3
    eth_lost = total_lost['ETH']
    assert len(eth_lost) == 2
    assert FVal(eth_lost['amount']) >= FVal('0.004452186358507873')
    assert FVal(eth_lost['usd_value']) >= ZERO
    busd_lost = total_lost[A_BUSD.identifier]
    assert len(busd_lost) == 2
    assert FVal(busd_lost['amount']) >= FVal('21.605824443625747553')
    assert FVal(busd_lost['usd_value']) >= ZERO
    wbtc_lost = total_lost[A_WBTC.identifier]
    assert len(wbtc_lost) == 2
    assert FVal(wbtc_lost['amount']) >= FVal('0.41590034')  # ouch
    assert FVal(wbtc_lost['usd_value']) >= ZERO

    expected_events = process_result_list(expected_aave_liquidation_test_events)

    assert_serialized_lists_equal(
        a=events[:len(expected_events)],
        b=expected_events,
        ignore_keys=None,
    )


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_3]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
@pytest.mark.parametrize('aave_use_graph', [True])
def test_query_aave_history_with_borrowing(rotkehlchen_api_server, ethereum_accounts, aave_use_graph):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    _query_borrowing_aave_history_test(setup, rotkehlchen_api_server)
    # Run it 2 times to make sure that data can be queried properly from the DB
    _query_borrowing_aave_history_test(setup, rotkehlchen_api_server)

    # Make sure events end up in the DB
    assert len(rotki.data.db.get_aave_events(AAVE_TEST_ACC_3)) != 0
    # test aave data purging from the db works
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'namedethereummoduledataresource',
        module_name='aave',
    ))
    assert_simple_ok_response(response)
    assert len(rotki.data.db.get_aave_events(AAVE_TEST_ACC_3)) == 0


def _test_for_duplicates_and_negatives(setup: BalancesTestSetup, server: APIServer) -> None:
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ))
        result = assert_proper_response_with_result(response)

    assert len(result) == 1
    result = result[AAVE_TEST_ACC_1]
    assert len(result) == 4

    for asset, entry in result['total_earned_interest'].items():
        if asset == ('aAAVE'):
            # TODO: This test for this address fails due to LEND and AAVE
            # Investigate and fix.
            continue
        assert FVal(entry['amount']) > ZERO
    for _, entry in result['total_lost'].items():
        assert FVal(entry['amount']) > ZERO
    for _, entry in result['total_earned_liquidations'].items():
        assert FVal(entry['amount']) > ZERO

    events = result['events']
    events_set = set()
    for idx, event in enumerate(events):
        msg = f'event {event} at index {idx} found twice in the returned events'
        event_hash = hash(event['event_type'] + event['tx_hash'] + str(event['log_index']))
        assert event_hash not in events_set, msg
        events_set.add(event_hash)


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_1]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
@pytest.mark.parametrize('aave_use_graph', [True])
def test_query_aave_history_no_duplicates(rotkehlchen_api_server, ethereum_accounts, aave_use_graph):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy avoids duplicate event data and keeps totals positive"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )

    _test_for_duplicates_and_negatives(setup, rotkehlchen_api_server)
    # Test that we still don't get duplicates at the 2nd query which hits the DB
    _test_for_duplicates_and_negatives(setup, rotkehlchen_api_server)


@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_query_aave_history_non_premium(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "aavehistoryresource",
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.CONFLICT,
    )
