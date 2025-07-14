import random
from collections import defaultdict
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet, BalanceType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.aggregator import CHAIN_TO_BALANCE_PROTOCOLS
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import MakerdaoVault
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ONE, ZERO
from rotkehlchen.constants.assets import (
    A_AVAX,
    A_BTC,
    A_DAI,
    A_ETH,
    A_EUR,
    A_KSM,
    A_USD,
    A_USDC,
    A_USDT,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.avalanche import AVALANCHE_ACC1_AVAX_ADDR, AVALANCHE_ACC2_AVAX_ADDR
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
from rotkehlchen.tests.utils.substrate import KUSAMA_TEST_NODES, SUBSTRATE_ACC1_KSM_ADDR
from rotkehlchen.types import (
    CHAIN_IDS_WITH_BALANCE_PROTOCOLS,
    SUPPORTED_EVM_CHAINS,
    ChainID,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader
    from rotkehlchen.types import BTCAddress, ChecksumEvmAddress


def assert_all_balances(
        result: dict[str, Any],
        db: 'DBHandler',
        expected_data_in_db: bool,
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

    with db.conn.read_ctx() as cursor:
        eth_tbalances = db.query_timed_balances(cursor=cursor, asset=A_ETH, balance_type=BalanceType.ASSET)  # noqa: E501
        if not expected_data_in_db:
            assert len(eth_tbalances) == 0
        else:
            assert len(eth_tbalances) == 1
            assert FVal(eth_tbalances[0].amount) == total_eth

        btc_tbalances = db.query_timed_balances(cursor=cursor, asset=A_BTC, balance_type=BalanceType.ASSET)  # noqa: E501
        if not expected_data_in_db:
            assert len(btc_tbalances) == 0
        else:
            assert len(btc_tbalances) == 1
            assert FVal(btc_tbalances[0].amount) == total_btc

        rdn_tbalances = db.query_timed_balances(cursor=cursor, asset=A_RDN, balance_type=BalanceType.ASSET)  # noqa: E501
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
                Location.BINANCE.serialize_for_db(),
                Location.TOTAL.serialize_for_db(),
                Location.BLOCKCHAIN.serialize_for_db(),
            }
            if got_external:
                expected_locations.add(Location.EXTERNAL.serialize_for_db())  # pylint: disable=no-member
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
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that using the query all balances endpoint works

    Test that balances from various sources are returned. Such as exchanges,
    blockchain and manually tracked balances"""
    async_query = random.choice([False, True])
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=[ManuallyTrackedBalance(
            identifier=-1,
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal('1550'),
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        )],
    )
    # Test that all balances request saves data on a fresh account
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'async_query': async_query},
        )
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server_with_exchanges,
            async_query=async_query,
        )

    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert_all_balances(
        result=outcome,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )

    with rotki.data.db.conn.read_ctx() as cursor:
        last_save_timestamp = rotki.data.db.get_last_balance_save_time(cursor)
        # now do the same but check to see if the balance save frequency delay works
        # and thus data will not be saved
        with ExitStack() as stack:
            setup.enter_all_patches(stack)
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server_with_exchanges,
                    'allbalancesresource',
                ),
            )
        assert_proper_response(response)
        new_save_timestamp = rotki.data.db.get_last_balance_save_time(cursor)
        assert last_save_timestamp == new_save_timestamp

        # wait for at least 1 second to make sure that new balances can be saved.
        # Can't save balances again if it's the same timestamp
        gevent.sleep(1)
        # now do the same but test that balance are saved since the balance save frequency delay
        # is overridden via `save_data` = True
        with ExitStack() as stack:
            setup.enter_all_patches(stack)
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server_with_exchanges,
                    'allbalancesresource',
                ), json={'save_data': True},
            )
        assert_proper_response(response)
        new_save_timestamp = rotki.data.db.get_last_balance_save_time(cursor)
        assert last_save_timestamp != new_save_timestamp


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_all_balances_ignore_cache(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that using the query all balances endpoint can ignore the cache"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    assert binance is not None
    poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
    assert poloniex is not None
    eth_query_patch = patch.object(
        rotki.chains_aggregator,
        'query_eth_balances',
        wraps=rotki.chains_aggregator.query_eth_balances,
    )
    btc_query_patch = patch.object(
        rotki.chains_aggregator,
        'query_btc_balances',
        wraps=rotki.chains_aggregator.query_btc_balances,
    )
    tokens_query_patch = patch.object(
        rotki.chains_aggregator,
        'query_evm_tokens',
        wraps=rotki.chains_aggregator.query_evm_tokens,
    )
    original_binance_query_dict = binance.api_query_dict
    binance_query_patch = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)
    poloniex_query_patch = patch.object(poloniex, 'api_query_list', wraps=poloniex.api_query_list)
    check_for_new_xpub_addresses_patch = patch(
        'rotkehlchen.chain.bitcoin.xpub.XpubManager.check_for_new_xpub_addresses',
        return_value=None,
    )

    with ExitStack() as stack:
        assert setup.poloniex_patch is not None
        stack.enter_context(setup.poloniex_patch)
        assert setup.binance_patch is not None
        stack.enter_context(setup.binance_patch)
        etherscan_mock = stack.enter_context(setup.etherscan_patch)
        stack.enter_context(setup.bitcoin_patch)
        stack.enter_context(setup.evmtokens_max_chunks_patch)
        stack.enter_context(setup.beaconchain_patch)
        function_call_counters = [
            stack.enter_context(eth_query_patch),
            stack.enter_context(btc_query_patch),
            stack.enter_context(tokens_query_patch),
            stack.enter_context(binance_query_patch),
            stack.enter_context(poloniex_query_patch),
            stack.enter_context(check_for_new_xpub_addresses_patch),
        ]

        # Query all balances for the first time and test it works
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        assert_all_balances(
            result=result,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        for fn in function_call_counters:
            if fn._mock_wraps == original_binance_query_dict:
                assert fn.call_count == 2
            # addresses are not derived from xpubs when `ignore_cache` is False
            elif fn._mock_name == 'check_for_new_xpub_addresses':
                assert fn.call_count == 0
            else:
                assert fn.call_count == 1
        full_query_etherscan_count = etherscan_mock.call_count

        # Query all balances second time and assert cache was used
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        assert_all_balances(
            result=result,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        msg = 'call count should stay the same since cache should have been used'
        for fn in function_call_counters:
            if fn._mock_wraps == original_binance_query_dict:
                assert fn.call_count == 2, msg
            # addresses are not derived from xpubs when `ignore_cache` is False
            elif fn._mock_name == 'check_for_new_xpub_addresses':
                assert fn.call_count == 0, msg
            else:
                assert fn.call_count == 1, msg
        msg = 'etherscan call_count should have remained the same due to no token detection '
        assert etherscan_mock.call_count == full_query_etherscan_count, msg

        # Now query all balances but request cache ignoring
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'ignore_cache': True},
        )
        result = assert_proper_sync_response_with_result(response)
        assert_all_balances(
            result=result,
            db=rotki.data.db,
            expected_data_in_db=True,
            setup=setup,
        )
        msg = 'call count should increase since cache should have been ignored'
        for fn in function_call_counters:
            if fn._mock_wraps == original_binance_query_dict:
                assert fn.call_count == 4, msg
            # addresses are derived from xpubs when `ignore_cache` is True
            elif fn._mock_name == 'check_for_new_xpub_addresses':
                assert fn.call_count == 2, msg  # 2 is for btc + bch
            else:
                assert fn.call_count == 2, msg

        msg = 'etherscan call count should have doubled after forced token detection'
        assert etherscan_mock.call_count == full_query_etherscan_count * 2, msg


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
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        manually_tracked_balances: list[ManuallyTrackedBalance],
) -> None:
    """Test that using the query all balances endpoint also includes manually tracked balances

    This test allows caching of results as is default in production and makes sure
    that result is the same after queryign balances twice and cache is hit. Serves
    as a regression test for https://github.com/rotki/rotki/issues/5847
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    manually_tracked_balances = [ManuallyTrackedBalance(
        identifier=-1,
        asset=A_BTC,
        label='XPUB BTC wallet',
        amount=FVal('10'),
        location=Location.BLOCKCHAIN,
        tags=None,
        balance_type=BalanceType.ASSET,
    ), ManuallyTrackedBalance(
        identifier=-1,
        asset=A_BTC,
        label='BTC in hardware wallet',
        amount=FVal('20'),
        location=Location.BLOCKCHAIN,
        tags=['private'],
        balance_type=BalanceType.ASSET,
    ), ManuallyTrackedBalance(
        identifier=-1,
        asset=A_ETH,
        label='ETH in a not supported exchange wallet',
        amount=FVal('10'),
        location=Location.EXTERNAL,
        tags=['private'],
        balance_type=BalanceType.ASSET,
    ), ManuallyTrackedBalance(
        identifier=-1,
        asset=A_EUR,
        label='N26 account',
        amount=FVal('12500.15'),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    ), ManuallyTrackedBalance(
        identifier=-1,
        asset=A_EUR,
        label='Deutsche Bank account',
        amount=FVal('1337.1337'),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    )]
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=manually_tracked_balances,
    )
    # query all balances first time and see manual balances are also there
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ),
        )
    result = assert_proper_sync_response_with_result(response)
    assert_all_balances(
        result=result,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )
    # query again, hit cache and check result. Test for https://github.com/rotki/rotki/issues/5847
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ),
        )
    result = assert_proper_sync_response_with_result(response)
    assert_all_balances(
        result=result,
        db=rotki.data.db,
        expected_data_in_db=True,
        setup=setup,
    )


def test_query_all_balances_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that errors are handled correctly by the all balances endpoint"""
    # invoke the endpoint with non boolean save_data
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'allbalancesresource',
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
            'allbalancesresource',
        ), json={'async_query': 14545},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_protocol_balances_all_chains(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that all chains in CHAIN_TO_BALANCE_PROTOCOLS get their protocol balances queried.
    Regression test for https://github.com/rotki/rotki/pull/9173
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    for chain in SUPPORTED_EVM_CHAINS:
        rotki.chains_aggregator.accounts.add(
            blockchain=chain,
            address=string_to_evm_address('0x706A70067BE19BdadBea3600Db0626859Ff25D74'),
        )

    queried_chains = []

    def mock_query_protocols_with_balance(chain_id: CHAIN_IDS_WITH_BALANCE_PROTOCOLS) -> None:
        queried_chains.append(chain_id)

    # patch _query_protocols_with_balance to record chains queried,
    # and also patch a couple other functions since we don't need them taking time here.
    with (patch.object(
            rotki.chains_aggregator,
            '_query_protocols_with_balance',
            side_effect=mock_query_protocols_with_balance,
        ),
        patch.object(rotki.chains_aggregator, 'query_evm_chain_balances'),
    ):
        rotki.chains_aggregator.query_balances()

    for key in CHAIN_TO_BALANCE_PROTOCOLS:
        assert key in queried_chains


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE,)])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_balance_snapshot_error_message(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        websocket_connection: 'WebsocketReader',
) -> None:
    """
    Test that an error in the general balance snapshot is caught and a websocket message is sent
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)

    def mock_binance_method() -> None:
        raise RemoteError('Made a booboo')

    binance_patch = patch.object(binance, 'first_connection', side_effect=mock_binance_method)
    with binance_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ),
        )

    result = assert_proper_sync_response_with_result(response)
    assert result == {'assets': {}, 'liabilities': {}, 'location': {}, 'net_usd': '0'}
    websocket_connection.wait_until_messages_num(num=2, timeout=10)
    assert websocket_connection.messages_num() == 2
    msg = websocket_connection.pop_message()
    assert msg == {
        'type': 'legacy',
        'data': {
            'value': 'binance account API request failed. Could not reach binance due to Made a booboo',  # noqa: E501
            'verbosity': 'error',
        },
    }
    assert websocket_connection.messages_num() == 1
    msg = websocket_connection.pop_message()
    assert msg == {
        'type': 'balance_snapshot_error',
        'data': {
            'location': 'binance',
            'error': 'binance account API request failed. Could not reach binance due to Made a booboo',  # noqa: E501
        },
    }
    assert websocket_connection.messages_num() == 0


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('separate_blockchain_calls', [True, False])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_multiple_balance_queries_not_concurrent(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        separate_blockchain_calls: bool,
) -> None:
    """Test multiple different balance query requests happening concurrently

    This tests that if multiple balance query requests happen concurrently we
    do not end up doing them multiple times, but reuse the results thanks to cache.

    Try running both all blockchain balances in one call and each blockchain call separately.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    multieth_balance_patch = patch.object(
        rotki.chains_aggregator.ethereum.node_inquirer,
        'get_multi_balance',
        wraps=rotki.chains_aggregator.ethereum.node_inquirer.get_multi_balance,
    )
    btc_balances_patch = patch(
        'rotkehlchen.chain.bitcoin.btc.manager.BitcoinManager.get_balances',
        wraps=rotki.chains_aggregator.bitcoin.get_balances,
    )
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    assert binance is not None
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
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'async_query': True})
        task_id_one_exchange = assert_ok_async_response(response)
        if separate_blockchain_calls:
            response = requests.get(api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'blockchainbalancesresource',
            ), json={'async_query': True, 'blockchain': 'ETH'})
            task_id_blockchain_eth = assert_ok_async_response(response)
            response = requests.get(api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'blockchainbalancesresource',
            ), json={'async_query': True, 'blockchain': 'BTC'})
            task_id_blockchain_btc = assert_ok_async_response(response)
        else:
            response = requests.get(api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'blockchainbalancesresource',
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
        assert bn.call_count == 2, 'binance balance query should do 2 calls'

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
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that querying the balances in a specific order does not mix up the caches.

    This tests for the problem seen where the bitcoin balances being empty and
    queried first returned an empty result for the ethereum balances.
    Note: It is hard to VCR because https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=70913478
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=['1000000000000000000'],
        token_balances={A_RDN.resolve_to_evm_token(): ['2000000000000000000']},
        original_queries=['zerion'],
    )

    # Test all balances request by requesting to not save the data
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response_btc = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=SupportedBlockchain.BITCOIN.serialize(),
        ), json={'async_query': True})
        eth_chain_key = SupportedBlockchain.ETHEREUM.serialize()
        response_eth = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=eth_chain_key,
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
        assert result_eth['per_account'][eth_chain_key][ethereum_accounts[0]]['assets'][A_ETH.identifier][DEFAULT_BALANCE_LABEL]['amount'] == '1'  # noqa: E501
        assert result_eth['per_account'][eth_chain_key][ethereum_accounts[0]]['assets'][A_RDN.identifier][DEFAULT_BALANCE_LABEL]['amount'] == '2'  # noqa: E501
        assert result_eth['totals']['assets'][A_ETH.identifier][DEFAULT_BALANCE_LABEL]['amount'] == '1'  # noqa: E501
        assert result_eth['totals']['assets'][A_RDN.identifier][DEFAULT_BALANCE_LABEL]['amount'] == '2'  # noqa: E501
        assert result_eth['per_account'][eth_chain_key][ethereum_accounts[0]]['assets'][A_RDN.identifier][DEFAULT_BALANCE_LABEL]['amount'] == '2'  # noqa: E501
        assert result_btc['per_account'] == {}
        assert result_btc['totals']['assets'] == {}
        assert result_btc['totals']['liabilities'] == {}


@pytest.mark.vcr(match_on=['uri', 'method', 'raw_body'], allow_playback_repeats=True)
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [[KUSAMA_TEST_NODES[0]]])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, 'Hyn23aznM9sRZEkMXDQXePi81iYTZLQRveLU5JNA5oxkuyD']])  # noqa: E501
def test_query_ksm_balances(rotkehlchen_api_server: 'APIServer', ksm_accounts: list[str]) -> None:
    """Test query the KSM balances when multiple accounts are set up works as
    expected.
    """
    ksm_chain_key = SupportedBlockchain.KUSAMA.serialize()
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=ksm_chain_key,
        ),
        json={'async_query': True},
    )
    task_id = assert_ok_async_response(response)
    result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)

    # Check per account
    account_1_balances = result['per_account'][ksm_chain_key][ksm_accounts[0]]
    assert 'liabilities' in account_1_balances
    asset_ksm = account_1_balances['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    account_2_balances = result['per_account'][ksm_chain_key][ksm_accounts[1]]
    assert 'liabilities' in account_2_balances
    asset_ksm = account_2_balances['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets'][A_KSM.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('avax_accounts', [[AVALANCHE_ACC1_AVAX_ADDR, AVALANCHE_ACC2_AVAX_ADDR]])
def test_query_avax_balances(rotkehlchen_api_server: 'APIServer') -> None:
    """Test query the AVAX balances when multiple accounts are set up works as
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
    avax_chain_key = SupportedBlockchain.AVALANCHE.serialize()
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'named_blockchain_balances_resource',
                blockchain=avax_chain_key,
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_sync_response_with_result(response)

    # Check per account
    account_1_balances = result['per_account'][avax_chain_key][AVALANCHE_ACC1_AVAX_ADDR]
    assert 'liabilities' in account_1_balances
    asset_avax = account_1_balances['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_avax['amount']) >= ZERO
    assert FVal(asset_avax['usd_value']) >= ZERO

    account_2_balances = result['per_account'][avax_chain_key][AVALANCHE_ACC2_AVAX_ADDR]
    assert 'liabilities' in account_2_balances
    asset_avax = account_2_balances['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_avax['amount']) >= ZERO
    assert FVal(asset_avax['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_avax = result['totals']['assets'][A_AVAX.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_avax['amount']) >= ZERO
    assert FVal(total_avax['usd_value']) >= ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2025-06-23 08:00:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_ethereum_tokens_detection(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    account = ethereum_accounts[0]

    def query_detect_eth_tokens() -> dict[str, Any]:
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'detecttokensresource',
                blockchain=SupportedBlockchain.ETHEREUM.serialize(),
            ), json={
                'async_query': False,
                'only_cache': True,
                'addresses': ethereum_accounts,
            },
        )
        return assert_proper_sync_response_with_result(response)

    empty_tokens_result = {
        account: {
            'tokens': None,
            'last_update_timestamp': None,
        },
    }
    assert query_detect_eth_tokens() == empty_tokens_result

    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    cur_time = ts_now()
    with db.user_write() as write_cursor:
        db.save_tokens_for_address(
            write_cursor=write_cursor,
            address=account,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[A_RDN, A_DAI],
        )
    result = query_detect_eth_tokens()
    assert set(result[account]['tokens']) == {A_DAI.identifier, A_RDN.identifier}
    assert result[account]['last_update_timestamp'] >= cur_time


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('ignore_mocked_prices_for', [['ETH', 'eip155:1/erc20:0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6']])  # noqa: E501
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.5)])
def test_balances_behaviour_with_manual_current_prices(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Checks that manual current price is used in balances querying endpoints"""
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=[str(int(1e18)), str(2 * int(1e18))],
        token_balances={A_RDN.resolve_to_evm_token(): [str(int(1e18)), str(int(4e18))]},
        manual_current_prices=[(A_ETH, A_BTC, Price(FVal(10))), (A_RDN, A_ETH, Price(FVal(2)))],
    )
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'allbalancesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        # (3 ETH) * (10 BTC per ETH) * (1,5 USD per BTC) = 45 USD of ETH
        eth_result = result['assets'][A_ETH.identifier]
        assert eth_result['amount'] == '3'
        assert eth_result['usd_value'] == '45.0'
        # (5 RDN) * (2 ETH per RDN) * (10 BTC per RDN) * (1,5 USD per BTC) = 150 USD of RDN
        rdn_result = result['assets']['eip155:1/erc20:0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6']
        assert rdn_result['amount'] == '5'


@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('ethereum_accounts', [['0x7e574e063903b1D6DFf54A9C8B1260e6E068d35e']])
def test_blockchain_balances_refresh(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Checks that blockchain balances are refreshed properly when the endpoint is called"""
    chains_aggregator = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator
    makerdao_vault = [MakerdaoVault(
        identifier=0,
        collateral_type='ctype',
        owner=ethereum_accounts[0],
        collateral_asset=A_USDT.resolve_to_crypto_asset(),
        collateral=Balance(FVal(3), FVal(54)),
        debt=Balance(ZERO),
        collateralization_ratio=None,
        liquidation_ratio=ZERO,
        liquidation_price=None,
        urn=ethereum_accounts[0],
        stability_fee=ZERO,
    )]
    vaults_patch = patch('rotkehlchen.chain.ethereum.modules.makerdao.vaults.MakerdaoVaults.get_vaults', side_effect=lambda: makerdao_vault)  # noqa: E501

    a_usdc = A_USDC.resolve_to_evm_token()
    a_dai = A_DAI.resolve_to_evm_token()
    account_balance = {ethereum_accounts[0]: BalanceSheet(
        assets=defaultdict(lambda: defaultdict(Balance), {
            a_usdc: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(ONE, FVal(24))}),
            a_dai: defaultdict(Balance, {DEFAULT_BALANCE_LABEL: Balance(FVal(2), FVal(42))}),
        }),
    )}
    account_balance_patch = patch.object(chains_aggregator.balances, 'eth', account_balance)

    def mock_query_tokens(addresses: list['ChecksumEvmAddress']) -> tuple[dict, dict]:
        mock_balances = {ethereum_accounts[0]: {a_usdc: FVal(23), a_dai: FVal(3)}}
        mock_prices = {a_usdc: Price(FVal(10)), a_dai: Price(FVal(11))}
        return (mock_balances, mock_prices) if len(addresses) != 0 else ({}, {})

    query_tokens_patch = patch('rotkehlchen.chain.evm.tokens.EvmTokens.query_tokens_for_addresses', side_effect=mock_query_tokens)  # noqa: E501
    price_inquirer_patch = patch('rotkehlchen.inquirer.Inquirer.find_usd_price', side_effect=lambda _: Price(ZERO))  # noqa: E501
    proxies_inquirer_patch = patch('rotkehlchen.chain.evm.proxies_inquirer.EvmProxiesInquirer.get_accounts_having_proxy', side_effect=dict)  # noqa: E501
    multieth_balance_patch = patch.object(chains_aggregator.ethereum.node_inquirer, 'get_multi_balance', lambda accounts: {ethereum_accounts[0]: ZERO})  # noqa: E501
    protocols_patch = patch('rotkehlchen.chain.aggregator.CHAIN_TO_BALANCE_PROTOCOLS', side_effect={ChainID.ETHEREUM: ()})  # noqa: E501

    with account_balance_patch, query_tokens_patch, price_inquirer_patch, vaults_patch, multieth_balance_patch, protocols_patch, proxies_inquirer_patch:  # noqa: E501

        def query_blockchain_balance(num: int) -> Any:
            """Refreshes blockchain balances `num` number of times"""
            result = None
            for _ in range(num):
                response = requests.get(api_url_for(
                    rotkehlchen_api_server,
                    'blockchainbalancesresource',
                ), json={'async_query': False, 'blockchain': 'ETH', 'ignore_cache': True})
                result = assert_proper_sync_response_with_result(response)
            assert result is not None
            return result

        one_time_query_result = query_blockchain_balance(1)
        assert one_time_query_result['per_account']['eth'][ethereum_accounts[0]]['assets'] == {
            A_USDC.identifier: {DEFAULT_BALANCE_LABEL: {'amount': '23', 'usd_value': '230'}},
            A_DAI.identifier: {DEFAULT_BALANCE_LABEL: {'amount': '3', 'usd_value': '33'}},
            A_USDT.identifier: {'makerdao vault': {'amount': '3', 'usd_value': '54'}},
        }
        assert one_time_query_result == query_blockchain_balance(4)


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_balances_with_threshold(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that balance filtering by USD value threshold works for all balance types"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    manually_tracked_balances = [
        ManuallyTrackedBalance(
            identifier=-1,
            asset=A_EUR,
            label='Small EUR',
            amount=ONE,
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        ),
        ManuallyTrackedBalance(
            identifier=-2,
            asset=A_USD,
            label='USD',
            amount=FVal('10'),
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        ),
        ManuallyTrackedBalance(
            identifier=-3,
            asset=A_BTC,
            label='Large BTC',
            amount=ONE,
            location=Location.EXTERNAL,
            tags=None,
            balance_type=BalanceType.ASSET,
        ),
    ]

    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=manually_tracked_balances,
        eth_balances=['100000000000000000', '200000000000000000'],  # 0.1 and 0.2 ETH
        token_balances={
            A_DAI.resolve_to_evm_token(): ['5000000000000000000', '0'],  # 5 DAI and 0 DAI
            A_USDC.resolve_to_evm_token(): ['1000000', '2000000'],  # 1 USDC and 2 USDC
        },
        liabilities={
            A_DAI.resolve_to_evm_token(): ['15000000000000000000', '10'],
        },
        btc_balances=['1000000000000', '1'],
    )

    threshold = FVal(10)  # Set threshold to 10 USD
    with ExitStack() as stack:
        setup.enter_all_patches(stack)

        results = []
        for endpoint in (
            'blockchainbalancesresource',
            'exchangebalancesresource',
            'manuallytrackedbalancesresource',
        ):
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server_with_exchanges,
                    endpoint,
                ),
               params={'usd_value_threshold': threshold.to_int(exact=True)},
            )
            results.append(assert_proper_sync_response_with_result(response))

        blockchain_result, exchange_result, manual_result = results

        # Assert blockchain balances
        for chain, chain_balances in blockchain_result['per_account'].items():
            for address, balances in chain_balances.items():
                if chain == 'btc':
                    for balance in balances.values():
                        assert FVal(balance['usd_value']) > threshold
                else:
                    assets = balances['assets']
                    for balance in assets.values():
                        assert FVal(balance['usd_value']) > threshold

                    if address == ethereum_accounts[0]:
                        assert balances['liabilies'] == {A_DAI: FVal(15)}
                    else:
                        assert balances['liabilies'] == {}  # value gets filtered

        # Assert exchange balances
        assert len(exchange_result) != 0
        for exchange in exchange_result:
            assert len(exchange_result[exchange]) != 0
            for balance in exchange_result[exchange].values():
                assert FVal(balance['usd_value']) > threshold

        # Assert manual balances
        assert len(manual_result['balances']) != 0
        for balance in manual_result['balances']:
            assert FVal(balance['usd_value']) > threshold
