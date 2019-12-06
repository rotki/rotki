import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.history import (
    assert_binance_trades_result,
    assert_poloniex_trades_result,
    mock_history_processing_and_exchanges,
)


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_trades(rotkehlchen_api_server_with_exchanges):
    """Test that querying the trades endpoint works as expected"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    setup = mock_history_processing_and_exchanges(rotki)

    # Query trades of all exchanges to get them saved in the DB
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "exchangetradesresource"))
    assert_proper_response(response)

    # Simply get all trades without any filtering
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 5  # 3 polo and 2 binance trades
    assert_binance_trades_result([t for t in data['result'] if t['location'] == 'binance'])
    assert_poloniex_trades_result([t for t in data['result'] if t['location'] == 'poloniex'])

    # Now filter by location
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'location': 'binance'},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2  # only 2 binance trades
    assert_binance_trades_result([t for t in data['result'] if t['location'] == 'binance'])

    # Now filter by time
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'from_timestamp': 1512561942, 'to_timestamp': 1539713237},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 3  # 1 binance trade and 2 poloniex trades
    assert_binance_trades_result(
        trades=[t for t in data['result'] if t['location'] == 'binance'],
        trades_to_check=(1,),
    )
    assert_poloniex_trades_result(
        trades=[t for t in data['result'] if t['location'] == 'poloniex'],
        trades_to_check=(0, 1),
    )

    # and now filter by both time and location
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'from_timestamp': 1512561942, 'to_timestamp': 1539713237, 'location': 'poloniex'},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2  # only 2/3 poloniex trades
    assert_poloniex_trades_result(
        trades=[t for t in data['result'] if t['location'] == 'poloniex'],
        trades_to_check=(0, 1),
    )
