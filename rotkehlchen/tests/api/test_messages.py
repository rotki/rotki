from http import HTTPStatus
from typing import Any, Dict

import pytest
import requests

from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.history import (
    assert_binance_trades_result,
    assert_poloniex_trades_result,
    mock_history_processing_and_exchanges,
)


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_messages(rotkehlchen_api_server_with_exchanges):
    """Test that querying the messages endpoint returns notifications for the user"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    # Query trades of all exchanges to get them saved in the DB. This generates
    # warnings due to unsupported assets found during querying
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "exchangetradesresource"))
    assert_proper_response(response)

    # and now query for the messages
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "messagesresource"),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    errors = data['result']['errors']
    warnings = data['result']['warnings']
    assert len(errors) == 0
    assert len(warnings) == 2
    assert warnings[0] == 'Found poloniex trade with unknown asset NOEXISTINGASSET. Ignoring it.'
    assert warnings[1] == 'Found poloniex trade with unsupported asset BALLS. Ignoring it.'

    # now query for the messages again and make sure that nothing is return, since
    # our previous query should have popped all the messages in the queue
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "messagesresource"),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    errors = data['result']['errors']
    warnings = data['result']['warnings']
    assert len(errors) == 0
    assert len(warnings) == 0
