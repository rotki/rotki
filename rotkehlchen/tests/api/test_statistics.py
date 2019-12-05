from http import HTTPStatus

import gevent
import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.balances import get_asset_balance_total
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_query_statistics_netvalue(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
        start_with_valid_premium,
):
    """Test that using the statistics netvalue over time endpoint works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.blockchain.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    # query balances and save data in DB to have data to test the statistics endpoint
    with setup.poloniex_patch, setup.binance_patch, setup.blockchain_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': True}
        )
    assert_proper_response(response)

    # and now test that statistics work fine
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "statisticsnetvalueresource",
        )
    )
    if start_with_valid_premium:
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        assert len(data['result']) == 2
        assert len(data['result']['times']) == 1
        assert len(data['result']['data']) == 1
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_query_statistics_asset_balance(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
        start_with_valid_premium,
):
    """Test that using the statistics asset balance over time endpoint works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.blockchain.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)
    start_time = ts_now()

    # query balances and save data in DB to have data to test the statistics endpoint
    with setup.poloniex_patch, setup.binance_patch, setup.blockchain_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': True}
        )
    assert_proper_response(response)

    # and now test that statistics work fine for ETH
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
        assert len(entry) == 3
        assert FVal(entry['amount']) == get_asset_balance_total('ETH', setup)
        assert entry['time'] > start_time
        assert entry['usd_value'] is not None
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )
