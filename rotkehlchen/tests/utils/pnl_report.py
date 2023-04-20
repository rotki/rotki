import random
from contextlib import ExitStack

import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test
from rotkehlchen.types import Optional, Timestamp


def query_api_create_and_get_report(
        server,
        start_ts: Timestamp,
        end_ts: Timestamp,
        prepare_mocks: bool,
        events_offset: Optional[int] = None,
        events_limit: Optional[int] = None,
        events_ascending_timestamp: bool = False,
):
    async_query = random.choice([False, True])
    rotki = server.rest_api.rotkehlchen
    setup = None
    if prepare_mocks is True:
        setup = prepare_rotki_for_history_processing_test(
            rotki=rotki,
            should_mock_history_processing=False,
            history_start_ts=start_ts,
            history_end_ts=end_ts,
        )

    # Query history processing to start the history processing
    with ExitStack() as stack:
        if setup is not None:
            for manager in setup:
                stack.enter_context(manager)
        response = requests.get(
            api_url_for(server, 'historyprocessingresource'),
            json={'from_timestamp': start_ts, 'to_timestamp': end_ts, 'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)

    report_id = outcome
    response = requests.get(
        api_url_for(server, 'per_report_resource', report_id=report_id),
    )
    report_result = assert_proper_response_with_result(response)

    response = requests.post(
        api_url_for(server, 'per_report_data_resource', report_id=report_id),
        json={
            'offset': events_offset,
            'limit': events_limit,
            'order_by_attributes': ['timestamp'],
            'ascending': [events_ascending_timestamp],
        },
    )
    events_result = assert_proper_response_with_result(response)
    return report_id, report_result, events_result
