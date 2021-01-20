import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_periodic(rotkehlchen_api_server_with_exchanges):
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts=[], btc_accounts=[])
    start_ts = ts_now()

    # Query trades of an exchange to get them saved in the DB
    with setup.binance_patch, setup.poloniex_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "periodicdataresource"),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 3
    assert data['result']['last_balance_save'] >= start_ts
    assert data['result']['eth_node_connection'] is False
    # Non -1 value tests for these exist in test_history.py::test_query_history_timerange
    assert data['result']['last_data_upload_ts'] == 0
