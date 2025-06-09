import platform
from rotkehlchen.utils.concurrency import timeout as Timeout, Timeout, joinall, spawn

import pytest


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
    with Timeout(10):
        g1 = spawn(_send_stuff, rotki.msg_aggregator, websocket_connection, string_len)
        _send_stuff(rotki.msg_aggregator, websocket_connection, string_len)
        g2 = spawn(_send_stuff, rotki.msg_aggregator, websocket_connection, string_len)
        joinall([g1, g2])
        assert all(
            isinstance(x.exception, ConcurrentObjectUseError) is False
            for x in [g1, g2] + rotki.greenlet_manager.greenlets
        ), 'At least one ConcurrentObjectUseError exception happened'
