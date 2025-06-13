import random
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('btc_accounts', [['bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3']])  # noqa: E501
def test_query_transactions(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that bitcoin transactions are properly queried via the api."""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)

    assert result is True

    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )

    last_id = events[0].event_identifier
    for event in events:
        if event.event_identifier != last_id:
            print('------')
        print([event])
        last_id = event.event_identifier
