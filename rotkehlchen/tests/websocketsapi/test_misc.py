import json
import platform

import pytest

from rotkehlchen.concurrency import spawn, wait
from rotkehlchen.user_messages import MessagesAggregator


def _send_stuff(msg_aggregator, websocket_connection, string_len):
    for _ in range(10):
        # We need big strings in order to replicate. Small messages do not hit it
        # But not too big since it can cause `WebSocketPayloadException` and that
        # can make this test run forever
        #  <bound method WebsocketReader.read_forever of <rotkehlchen.tests.fixtures.websockets.WebsocketReader object at 0x7ff6f3136f70>>> failed with WebSocketPayloadException  # noqa: E501
        msg_aggregator.add_error('x' * string_len)
        msg_aggregator.add_warning('y' * string_len)
        if websocket_connection.messages_num() != 0:
            websocket_connection.pop_message()


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_websockets_concurrent_use(rotkehlchen_api_server, websocket_connection):
    """Up until 1.26.3 there was no lock per websocket connection and that could under
    very heavy and specific circumstances cause concurrent websocket access from multiple
    greenlets.

    This test replicates that scenario, and it fails before the addition of the lock.
    Serves as a regression test. Should fail if locks are removed in websockets.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    string_len = 27000 if platform.system() == 'Darwin' else 100000
    g1 = spawn(_send_stuff, rotki.msg_aggregator, websocket_connection, string_len)
    _send_stuff(rotki.msg_aggregator, websocket_connection, string_len)
    g2 = spawn(_send_stuff, rotki.msg_aggregator, websocket_connection, string_len)
    # This runs a bit slowly on Windows and needs a generous timeout.
    wait([g1, g2], timeout=20)
    assert g1.dead and g2.dead, 'websocket sender tasks timed out'
    assert all(
        x.exception is None
        for x in [g1, g2] + rotki.task_supervisor.tasks
    ), 'At least one exception happened in a websocket sender or supervised task'


def test_requeue_undelivered_messages():
    """Test that messages queued to a websocket client that disconnected before
    receiving them land in the polling fallback deques if they are error-class,
    and are dropped otherwise"""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'legacy',
        'data': {'verbosity': 'error', 'value': 'an error'},
    }))
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'legacy',
        'data': {'verbosity': 'warning', 'value': 'a warning'},
    }))
    msg_aggregator.requeue_undelivered(snapshot_error_msg := json.dumps({
        'type': 'balance_snapshot_error',
        'data': {'location': 'kraken', 'error': 'oops'},
    }))
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'progress_updates',
        'data': {'total': 10, 'processed': 5},
    }))  # progress is meaningless to a dead client and gets dropped
    msg_aggregator.requeue_undelivered('{not json')  # malformed input is just logged

    assert msg_aggregator.consume_errors() == ['an error', snapshot_error_msg]
    assert msg_aggregator.consume_warnings() == ['a warning']
