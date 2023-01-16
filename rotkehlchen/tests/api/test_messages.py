import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.history import mock_history_processing_and_exchanges
from rotkehlchen.types import Location


@pytest.mark.parametrize('added_exchanges', [(Location.POLONIEX,)])
def test_query_messages(rotkehlchen_api_server_with_exchanges):
    """Test that querying the messages endpoint returns notifications for the user"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    # Query polo trades of to get them saved in the DB. This generates
    # warnings due to unsupported assets found during querying
    with setup.polo_patch:
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, 'tradesresource'))
    assert_proper_response(response)

    # and now query for the messages
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'messagesresource'),
    )
    result = assert_proper_response_with_result(response)
    errors = result['errors']
    warnings = result['warnings']
    assert len(errors) == 0
    assert len(warnings) == 2
    assert warnings[0] == 'Found poloniex trade with unknown asset NOEXISTINGASSET. Ignoring it.'
    assert warnings[1] == 'Found poloniex trade with unsupported asset BALLS. Ignoring it.'

    # now query for the messages again and make sure that nothing is return, since
    # our previous query should have popped all the messages in the queue
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'messagesresource'),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    errors = data['result']['errors']
    warnings = data['result']['warnings']
    assert len(errors) == 0
    assert len(warnings) == 0
