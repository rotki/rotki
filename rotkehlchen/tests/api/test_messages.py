from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.tests.fixtures.websockets import WebsocketReader
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.history import mock_history_processing_and_exchanges
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('added_exchanges', [(Location.POLONIEX,)])
def test_query_messages(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        websocket_connection: WebsocketReader,
    ) -> None:
    """Test that querying the messages endpoint returns notifications for the user"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    # Query polo trades of to get them saved in the DB. This generates
    # warnings due to unsupported assets found during querying
    with setup.polo_patch:
        response = requests.post(
            api_url_for(rotkehlchen_api_server_with_exchanges, 'exchangeeventsqueryresource'),
            json={'location': Location.POLONIEX.serialize()},
        )
    assert_proper_response(response)

    # and now query for the messages
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'messagesresource'),
    )
    assert_proper_sync_response_with_result(response)
    websocket_connection.wait_until_messages_num(num=9, timeout=10)
    assert [msg for msg in websocket_connection.messages if msg['type'] != 'history_events_status'] == [  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'Found poloniex trade with unsupported asset BALLS. Ignoring it.'}},  # noqa: E501
        {'type': 'exchange_unknown_asset', 'data': {'location': 'poloniex', 'name': 'poloniex', 'identifier': 'NOEXISTINGASSET', 'details': 'trade'}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'Found deposit of unsupported poloniex asset EBT. Ignoring it.'}},  # noqa: E501
        {'type': 'exchange_unknown_asset', 'data': {'location': 'poloniex', 'name': 'poloniex', 'identifier': 'IDONTEXIST', 'details': 'asset movement'}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'Found withdrawal of unsupported poloniex asset BALLS. Ignoring it.'}},  # noqa: E501
        {'type': 'exchange_unknown_asset', 'data': {'location': 'poloniex', 'name': 'poloniex', 'identifier': 'IDONTEXIST', 'details': 'asset movement'}},  # noqa: E501
    ]

    # now query for the messages again and make sure that nothing is return, since
    # our previous query should have popped all the messages in the queue
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, 'messagesresource'),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert websocket_connection.messages_num() == 9  # no more than the messages found above.
