import contextlib
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.balances import get_asset_balance_total
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.typing import Location
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
    rotki.chain_manager.cache_ttl_secs = 0
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

    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2
    assert len(data['result']['times']) == 1
    assert len(data['result']['data']) == 1


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
    rotki.chain_manager.cache_ttl_secs = 0
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
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsassetbalanceresource",
            asset="ETH",
        ),
    )
    if start_with_valid_premium:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert len(data['result']) == 1
        entry = data['result'][0]
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
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsassetbalanceresource",
            asset="BTC",
        ), json={'from_timestamp': 0, 'to_timestamp': start_time + 60000},
    )
    if start_with_valid_premium:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert len(data['result']) == 1
        entry = data['result'][0]
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
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsassetbalanceresource",
            asset="BTC",
        ), json={'from_timestamp': 0, 'to_timestamp': start_time - 1},
    )
    if start_with_valid_premium:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert len(data['result']) == 0
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
    response = requests.get(f'http://localhost:{rest_api_port}/api/1/statistics/balance')
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Check that an invalid asset given is an error
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "statisticsassetbalanceresource",
            asset="NOTAREALASSSETLOL",
        ), json={'from_timestamp': 0, 'to_timestamp': start_time},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset NOTAREALASSSETLOL provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that giving invalid value for from_timestamp is an error
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "statisticsassetbalanceresource",
            asset="BTC",
        ), json={'from_timestamp': 'dsad', 'to_timestamp': start_time},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string dsad',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that giving invalid value for to_timestamp is an error
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "statisticsassetbalanceresource",
            asset="BTC",
        ), json={'from_timestamp': 0, 'to_timestamp': 53434.32},
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
def test_query_statistics_value_distribution(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        start_with_valid_premium,
):
    """Test that using the statistics value distribution endpoint works"""
    start_time = ts_now()
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    token_balances = {A_RDN: ['111000', '4000000']}
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        token_balances=token_balances,
        manually_tracked_balances=[ManuallyTrackedBalance(
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal('1550'),
            location=Location.BANKS,
            tags=None,
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
            assert_proper_response(response)
            data = response.json()
            assert data['message'] == ''
            assert len(data['result']) == 5
            locations = {'poloniex', 'binance', 'banks', 'blockchain', 'total'}
            for entry in data['result']:
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
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert len(data['result']) == 4
        totals = {
            'ETH': get_asset_balance_total(A_ETH, setup),
            'BTC': get_asset_balance_total(A_BTC, setup),
            'EUR': get_asset_balance_total(A_EUR, setup),
            A_RDN.identifier: get_asset_balance_total(A_RDN, setup),
        }
        for entry in data['result']:
            assert len(entry) == 5
            assert entry['time'] >= start_time
            assert entry['category'] == 'asset'
            assert entry['usd_value'] is not None
            assert FVal(entry['amount']) == totals[entry['asset']]
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
                "statisticsrendererresource",
            ),
        )
    if start_with_valid_premium:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert data['result'] == 'codegoeshere'
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )
