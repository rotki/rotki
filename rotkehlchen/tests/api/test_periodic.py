import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_periodic(rotkehlchen_api_server_with_exchanges):
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
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
    result = assert_proper_response_with_result(response)
    assert len(result) == 3
    assert result['last_balance_save'] >= start_ts
    assert result['connected_eth_nodes'] == []
    # Non -1 value tests for these exist in test_history.py::test_query_history_timerange
    assert result['last_data_upload_ts'] == 0
