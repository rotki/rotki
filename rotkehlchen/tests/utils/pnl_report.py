import random
from contextlib import ExitStack
from unittest.mock import patch

import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test
from rotkehlchen.types import Timestamp


def query_api_create_and_get_report(
        server,
        start_ts: Timestamp,
        end_ts: Timestamp,
        prepare_mocks: bool,
        events_offset: int | None = None,
        events_limit: int | None = None,
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
        stack.enter_context(patch(
            'rotkehlchen.chain.evm.node_inquirer.EvmNodeInquirer.is_safe_proxy_or_eoa',
            return_value=False,
        ))
        response = requests.get(
            api_url_for(server, 'historyprocessingresource'),
            json={'from_timestamp': start_ts, 'to_timestamp': end_ts, 'async_query': async_query},
        )
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=server,
            async_query=async_query,
        )

    report_id = outcome
    response = requests.get(
        api_url_for(server, 'per_report_resource', report_id=report_id),
    )
    report_result = assert_proper_sync_response_with_result(response)

    response = requests.post(
        api_url_for(server, 'per_report_data_resource', report_id=report_id),
        json={
            'offset': events_offset,
            'limit': events_limit,
            'order_by_attributes': ['timestamp'],
            'ascending': [events_ascending_timestamp],
        },
    )
    events_result = assert_proper_sync_response_with_result(response)
    return report_id, report_result, events_result
