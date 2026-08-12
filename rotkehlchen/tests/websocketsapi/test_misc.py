import asyncio
import json
import platform
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from rotkehlchen.api.asgi import (
    WS_CLOSE_POLICY_VIOLATION,
    WS_CLOSE_TRY_AGAIN_LATER,
    WS_QUEUE_MAXSIZE,
    AsgiWebsocketSubscriber,
)
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.concurrency import spawn, wait
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader


def _send_stuff(
        msg_aggregator: MessagesAggregator,
        websocket_connection: WebsocketReader,
        string_len: int,
) -> None:
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
def test_websockets_concurrent_use(
        rotkehlchen_api_server: APIServer,
        websocket_connection: WebsocketReader,
) -> None:
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


def test_requeue_undelivered_messages() -> None:
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


def test_disconnect_deauthorized_drops_only_revoked_connections() -> None:
    """The /ws gate runs once, at the handshake, so a revoked session's socket has to
    be dropped from the outside or it keeps receiving broadcasts -- including, after a
    takeover, the next user's. Connections opened with the cookie gate off carry no
    credential and must be left alone."""
    loop = asyncio.new_event_loop()
    try:
        notifier = RotkiNotifier()
        revoked = AsgiWebsocketSubscriber(loop=loop, username='alice', sid='old-sid')
        revoked.close_callback = (revoked_close := Mock())
        live = AsgiWebsocketSubscriber(loop=loop, username='bob', sid='live-sid')
        live.close_callback = (live_close := Mock())
        ungated = AsgiWebsocketSubscriber(loop=loop)  # cookie gate off (Electron/dev)
        ungated.close_callback = (ungated_close := Mock())
        for subscriber in (revoked, live, ungated):
            notifier.subscribe(subscriber)

        notifier.disconnect_deauthorized(
            lambda username, sid: (username, sid) in {(None, None), ('bob', 'live-sid')},
        )
        loop.run_until_complete(asyncio.sleep(0))  # flush the scheduled callbacks

        assert revoked.closed is True
        revoked_close.assert_called_once_with(WS_CLOSE_POLICY_VIOLATION)
        assert live.closed is False
        live_close.assert_not_called()
        assert ungated.closed is False
        ungated_close.assert_not_called()

        # and the revoked one receives nothing more, even before its close lands
        notifier.broadcast(message_type=WSMessageType.LEGACY, to_send_data={'value': 'after'})
        loop.run_until_complete(asyncio.sleep(0))  # send() enqueues via the loop too
        assert revoked.queue.qsize() == 0
        assert live.queue.qsize() == 1
    finally:
        loop.close()


def test_queue_overflow_retains_dropped_messages() -> None:
    """The message that finds the queue full must be kept for teardown: it is
    handed back to the notifier by drain_pending along with the queued ones, so
    an error-class message still reaches the /messages polling fallback"""
    loop = asyncio.new_event_loop()
    try:
        subscriber = AsgiWebsocketSubscriber(loop=loop)
        subscriber.close_callback = (close_callback := Mock())
        for i in range(WS_QUEUE_MAXSIZE):
            subscriber.enqueue(f'message {i}')
        assert subscriber.closed is False

        subscriber.enqueue('the overflowing message')
        assert subscriber.closed is True
        close_callback.assert_called_once_with(WS_CLOSE_TRY_AGAIN_LATER)  # type: ignore[unreachable]  # mypy doesn't invalidate the closed=False narrowing across enqueue()
        # an enqueue already scheduled before the overflow closed it is kept too
        subscriber.enqueue('a message scheduled before the disconnect')

        pending = subscriber.drain_pending()
        assert len(pending) == WS_QUEUE_MAXSIZE + 2
        assert pending[0] == 'message 0'
        assert pending[-2] == 'the overflowing message'
        assert pending[-1] == 'a message scheduled before the disconnect'
    finally:
        loop.close()
