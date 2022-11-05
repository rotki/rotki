import contextlib
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_ETH2, A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.balances import get_asset_balance_total
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_statistics_netvalue(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the statistics netvalue over time endpoint works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    # query balances and save data in DB to have data to test the statistics endpoint
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    # and now test that statistics work fine
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsnetvalueresource",
        ),
    )

    result = assert_proper_response_with_result(response)
    assert len(result) == 2
    assert len(result['times']) == 1
    assert len(result['data']) == 1


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_query_statistics_asset_balance(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        start_with_valid_premium,
):
    """Test that using the statistics asset balance over time endpoint works"""
    start_time = ts_now()
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    # query balances and save data in DB to have data to test the statistics endpoint
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    # and now test that statistics work fine for ETH, with default time range (0 - now)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsassetbalanceresource',
        ),
        json={'asset': 'ETH'},
    )
    if start_with_valid_premium:
        result = assert_proper_response_with_result(response)
        assert len(result) == 1
        entry = result[0]
        assert len(entry) == 4
        assert FVal(entry['amount']) == get_asset_balance_total(A_ETH, setup)
        assert entry['category'] == 'asset'
        assert entry['time'] >= start_time
        assert entry['usd_value'] is not None
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )

    # and now test that statistics work fine for BTC, with given time range
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': start_time + 60000, 'asset': 'BTC'},
    )
    if start_with_valid_premium:
        result = assert_proper_response_with_result(response)
        assert len(result) == 1
        entry = result[0]
        assert len(entry) == 4
        assert FVal(entry['amount']) == get_asset_balance_total(A_BTC, setup)
        assert entry['time'] >= start_time
        assert entry['category'] == 'asset'
        assert entry['usd_value'] is not None
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )

    # finally test that if the time range is not including the saved balances we get nothing back
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': start_time - 1, 'asset': 'BTC'},
    )
    if start_with_valid_premium:
        result = assert_proper_response_with_result(response)
        assert len(result) == 0
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_statistics_asset_balance_errors(rotkehlchen_api_server, rest_api_port):
    """Test that errors at the statistics asset balance over time endpoint are hanled properly"""
    start_time = ts_now()

    # Check that no asset given is an error
    response = requests.post(f'http://localhost:{rest_api_port}/api/1/statistics/balance')
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that an invalid asset given is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': start_time, 'asset': 'NOTAREALASSSETLOL'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset NOTAREALASSSETLOL provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that giving invalid value for from_timestamp is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 'dsad', 'to_timestamp': start_time, 'asset': 'BTC'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string dsad',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that giving invalid value for to_timestamp is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': 53434.32, 'asset': 'BTC'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"Failed to deserialize a timestamp entry. Unexpected type',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
@pytest.mark.parametrize('db_settings', [{'treat_eth2_as_eth': True}, {'treat_eth2_as_eth': False}])  # noqa: E501
def test_query_statistics_value_distribution(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        start_with_valid_premium,
        db_settings,
):
    """Test that using the statistics value distribution endpoint works"""
    start_time = ts_now()
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    token_balances = {A_RDN: ['111000', '4000000']}
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        token_balances=token_balances,
        manually_tracked_balances=[ManuallyTrackedBalance(
            id=-1,
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal('1550'),
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        ), ManuallyTrackedBalance(
            id=2,
            asset=A_ETH2,
            label='John Doe',
            amount=FVal('2.6'),
            location=Location.KRAKEN,
            tags=None,
            balance_type=BalanceType.ASSET,
        )],
    )

    # query balances and save data in DB to have data to test the statistics endpoint
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    def assert_okay_by_location(response):
        """Helper function to run next query and its assertion twice"""
        if start_with_valid_premium:
            result = assert_proper_response_with_result(response)
            assert len(result) == 6
            locations = {'poloniex', 'binance', 'banks', 'blockchain', 'total', 'kraken'}
            for entry in result:
                assert len(entry) == 3
                assert entry['time'] >= start_time
                assert entry['usd_value'] is not None
                assert entry['location'] in locations
                locations.remove(entry['location'])
            assert len(locations) == 0
        else:
            assert_error_response(
                response=response,
                contained_in_msg='logged in user testuser does not have a premium subscription',
                status_code=HTTPStatus.CONFLICT,
            )

    # and now test that statistics work fine for distribution by location for json body
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsvaluedistributionresource",
        ), json={'distribution_by': 'location'},
    )
    assert_okay_by_location(response)
    # and now test that statistics work fine for distribution by location for query params
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsvaluedistributionresource",
        ) + '?distribution_by=location',
    )
    assert_okay_by_location(response)

    # finally test that statistics work fine for distribution by asset
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsvaluedistributionresource",
        ), json={'distribution_by': 'asset'},
    )
    if start_with_valid_premium:
        result = assert_proper_response_with_result(response)
        if db_settings['treat_eth2_as_eth'] is True:
            assert len(result) == 4
            totals = {
                'ETH': get_asset_balance_total(A_ETH, setup) + get_asset_balance_total(A_ETH2, setup),  # noqa: E501
                'BTC': get_asset_balance_total(A_BTC, setup),
                'EUR': get_asset_balance_total(A_EUR, setup),
                A_RDN.identifier: get_asset_balance_total(A_RDN, setup),
            }
            for index, entry in enumerate(result):
                assert len(entry) == 5
                assert entry['time'] >= start_time
                assert entry['category'] == 'asset'
                assert entry['usd_value'] is not None
                assert FVal(entry['amount']) == totals[entry['asset']]
                # check that the usd_value is in descending order
                if index == 0:
                    continue
                assert FVal(result[index - 1]['usd_value']) > FVal(entry['usd_value'])
        else:
            assert len(result) == 5
            totals = {
                'ETH': get_asset_balance_total(A_ETH, setup),
                'ETH2': get_asset_balance_total(A_ETH2, setup),
                'BTC': get_asset_balance_total(A_BTC, setup),
                'EUR': get_asset_balance_total(A_EUR, setup),
                A_RDN.identifier: get_asset_balance_total(A_RDN, setup),
            }
            for index, entry in enumerate(result):
                assert len(entry) == 5
                assert entry['time'] >= start_time
                assert entry['category'] == 'asset'
                assert entry['usd_value'] is not None
                assert FVal(entry['amount']) == totals[entry['asset']]
                # check that the usd_value is in descending order
                if index == 0:
                    continue
                assert FVal(result[index - 1]['usd_value']) > FVal(entry['usd_value'])
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_statistics_value_distribution_errors(rotkehlchen_api_server):
    """Test that the statistics value distribution endpoint handles errors properly"""
    # Test omitting the distribution_by argument
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "statisticsvaluedistributionresource",
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test invalid value for distribution_by
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "statisticsvaluedistributionresource",
        ), json={'distribution_by': 'haircolor'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Must be one of: location, asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_query_statistics_renderer(rotkehlchen_api_server, start_with_valid_premium):
    """Test that the statistics renderer endpoint works when properly queried"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    if start_with_valid_premium:
        def mock_premium_get(url, *_args, **_kwargs):
            if 'last_data_metadata' in url:
                response = (
                    '{"upload_ts": 0, "last_modify_ts": 0, "data_hash": "0x0", "data_size": 0}'
                )
            else:
                response = '{"data": "codegoeshere"}'
            return MockResponse(200, response)
        premium_patch = patch.object(rotki.premium.session, 'get', mock_premium_get)
    else:
        premium_patch = contextlib.nullcontext()

    with premium_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'statisticsrendererresource',
            ),
        )
    if start_with_valid_premium:
        result = assert_proper_response_with_result(response)
        assert result == 'codegoeshere'
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )
