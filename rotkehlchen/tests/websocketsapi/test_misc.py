import asyncio
import json
import platform
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from rotkehlchen.api.asgi import (
    WS_CLOSE_POLICY_VIOLATION,
    WS_CLOSE_TRY_AGAIN_LATER,
    WS_QUEUE_MAXSIZE,
    AsgiWebsocketSubscriber,
)
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.api.websockets.typedefs import UserMessageEntry, UserMessageRecord, WSMessageType
from rotkehlchen.concurrency import spawn, wait
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import Location
from rotkehlchen.user_messages import (
    MAX_POLLED_MESSAGES,
    BadData,
    LocalDbProblem,
    MessagesAggregator,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# A classification for tests about delivery, where which family a message has is irrelevant
_TAG_PROBLEM = LocalDbProblem(entry=UserMessageEntry.TAG)


def _send_stuff(msg_aggregator, websocket_connection, string_len):
    for _ in range(10):
        # We need big strings in order to replicate. Small messages do not hit it
        # But not too big since it can cause `WebSocketPayloadException` and that
        # can make this test run forever
        #  <bound method WebsocketReader.read_forever of <rotkehlchen.tests.fixtures.websockets.WebsocketReader object at 0x7ff6f3136f70>>> failed with WebSocketPayloadException  # noqa: E501
        msg_aggregator.add_error('x' * string_len, classification=_TAG_PROBLEM)
        msg_aggregator.add_warning('y' * string_len, classification=_TAG_PROBLEM)
        with suppress(IndexError):
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
    receiving them land in the polling fallback deques, unless they are live-only
    progress, which is dropped"""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'user_message',
        'data': {'verbosity': 'error', 'value': 'an error'},
    }))
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'user_message',
        'data': {'verbosity': 'warning', 'value': 'a warning'},
    }))
    msg_aggregator.requeue_undelivered(snapshot_error_msg := json.dumps({
        'type': 'balance_snapshot_error',
        'data': {'location': 'kraken', 'error': 'oops'},
    }))
    msg_aggregator.requeue_undelivered(unknown_asset_msg := json.dumps({
        'type': 'exchange_unknown_asset',
        'data': {'location': 'kraken', 'name': 'kraken', 'identifier': 'XYZ'},
    }))
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'progress_updates',
        'data': {'total': 10, 'processed': 5},
    }))  # progress is meaningless to a dead client and gets dropped
    msg_aggregator.requeue_undelivered(json.dumps({'type': 'not_a_type', 'data': {}}))
    msg_aggregator.requeue_undelivered('{not json')  # malformed input is just logged

    assert msg_aggregator.consume_errors() == ['an error', snapshot_error_msg, unknown_asset_msg]
    assert msg_aggregator.consume_warnings() == ['a warning']


def test_polling_fallback_keeps_the_envelope() -> None:
    """Without a socket a user message is queued with its full envelope for the messages
    endpoint, so its classification survives, while tests, tools and logout still read
    the rendered text from the same queue."""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_error(
        msg := 'Failed to deserialize a kucoin balance. Ignoring it.',
        classification=BadData(record=UserMessageRecord.BALANCE, error='Missing key: amount'),
        subject=Location.KUCOIN,
    )
    msg_aggregator.add_warning('a warning', classification=_TAG_PROBLEM)

    assert msg_aggregator.consume_error_payloads() == [{
        'type': 'user_message',
        'data': {
            'verbosity': 'error',
            'value': msg,
            'key': 'bad_data',
            'subject': 'kucoin',
            'fields': {'record': 'balance', 'error': 'Missing key: amount'},
        },
    }]
    assert msg_aggregator.consume_errors() == []  # the payload read drained the queue
    assert msg_aggregator.consume_warnings() == ['a warning']


def test_polling_queues_drop_the_oldest_message_when_full() -> None:
    """A queue nobody polls keeps only the newest MAX_POLLED_MESSAGES, still oldest first."""
    msg_aggregator = MessagesAggregator()
    for index in range(MAX_POLLED_MESSAGES + 2):
        msg_aggregator.add_error(f'error {index}', classification=_TAG_PROBLEM)
        msg_aggregator.add_warning(f'warning {index}', classification=_TAG_PROBLEM)

    kept = range(2, MAX_POLLED_MESSAGES + 2)
    assert msg_aggregator.consume_errors() == [f'error {index}' for index in kept]
    assert msg_aggregator.consume_warnings() == [f'warning {index}' for index in kept]


def test_failed_broadcast_falls_back_by_message_class() -> None:
    """A broadcast that fails queues a user message with its envelope and any other message
    as it was sent, and drops only live-only progress, the same policy requeue_undelivered
    applies to a client that disconnected."""
    def fail_delivery(
            failure_callback: Callable | None = None,
            failure_callback_args: dict[str, Any] | None = None,
            **_kwargs: Any,
    ) -> None:
        if failure_callback is not None:
            failure_callback(**(failure_callback_args or {}))

    msg_aggregator = MessagesAggregator()
    msg_aggregator.rotki_notifier = Mock(broadcast=Mock(side_effect=fail_delivery))
    msg_aggregator.add_error('an error', classification=_TAG_PROBLEM)
    msg_aggregator.add_message(WSMessageType.PROGRESS_UPDATES, {'total': 10, 'processed': 5})
    msg_aggregator.add_message(
        WSMessageType.BALANCE_SNAPSHOT_ERROR,
        snapshot_error := {'location': 'kraken', 'error': 'oops'},
    )
    msg_aggregator.add_message(
        WSMessageType.MISSING_API_KEY,
        missing_key := {'service': 'etherscan'},
    )

    assert msg_aggregator.consume_error_payloads() == [
        {'type': 'user_message', 'data': {
            'verbosity': 'error',
            'value': 'an error',
            'key': 'local_db',
            'subject': None,
            'fields': {'entry': 'tag'},
        }},
        {'type': 'balance_snapshot_error', 'data': snapshot_error},
        {'type': 'missing_api_key', 'data': missing_key},
    ]


def test_user_message_carries_its_classification():
    """The declared family, subject and unrendered fields reach the wire, and a message
    about no single location sends only its subject as null.

    The payload is asserted after process_result and json.dumps because that is where a
    value neither can handle would be swallowed -- broadcast logs and falls back to polling
    rather than raising, so a bad `fields` value fails silently.
    """
    msg_aggregator = MessagesAggregator()
    msg_aggregator.rotki_notifier = (notifier := Mock())

    msg_aggregator.add_error(
        msg := 'Failed to deserialize a kucoin balance. Ignoring it.',
        classification=BadData(record=UserMessageRecord.BALANCE, error='Missing key: amount'),
        subject=Location.KUCOIN,
    )
    assert json.loads(json.dumps(process_result(
        notifier.broadcast.call_args.kwargs['to_send_data'],
    ))) == {
        'verbosity': 'error',
        'value': msg,
        'key': 'bad_data',
        'subject': 'kucoin',
        'fields': {'record': 'balance', 'error': 'Missing key: amount'},
    }

    msg_aggregator.add_warning(msg := 'a message about no location', classification=_TAG_PROBLEM)
    assert json.loads(json.dumps(process_result(
        notifier.broadcast.call_args.kwargs['to_send_data'],
    ))) == {
        'verbosity': 'warning',
        'value': msg,
        'key': 'local_db',
        'subject': None,
        'fields': {'entry': 'tag'},
    }


def test_a_user_message_cannot_be_emitted_unclassified() -> None:
    """Every user message declares its family, so none reaches the frontend as a bare
    sentence it cannot group.

    mypy is the gate that matters, since it fails at the call site. This pins the same
    guarantee at runtime so that giving `classification` a default again cannot quietly
    reopen the lane.
    """
    msg_aggregator = MessagesAggregator()
    with pytest.raises(TypeError):
        msg_aggregator.add_error('an error')  # type: ignore[call-arg]  # classification is required
    with pytest.raises(TypeError):
        msg_aggregator.add_warning('a warning')  # type: ignore[call-arg]  # classification is required
    assert msg_aggregator.consume_errors() == msg_aggregator.consume_warnings() == []


def test_a_family_cannot_be_emitted_without_its_required_data() -> None:
    """The data a family promises is required to construct it, not merely documented.

    mypy is the gate that matters, since it fails at the call site. This pins the same
    guarantee at runtime so that turning a family into a plain class, or giving a required
    field a default to quiet something, cannot drop it silently: a BAD_DATA message with
    no `record` would collapse a failed trade and a failed balance into the same row.
    """
    with pytest.raises(TypeError):
        # pylint: disable-next=no-value-for-parameter
        BadData(record=UserMessageRecord.BALANCE)  # type: ignore[call-arg]  # `error` is not optional


def test_disconnect_deauthorized_drops_only_revoked_connections():
    """The /ws gate runs once, at the handshake, so a revoked session's socket has to
    be dropped from the outside or it keeps receiving broadcasts -- including, after a
    takeover, the next user's. Connections opened with the cookie gate off carry no
    credential and must be left alone."""
    loop = asyncio.new_event_loop()
    try:
        notifier = RotkiNotifier()
        revoked = AsgiWebsocketSubscriber(loop=loop, username='alice', sid='old-sid')
        live = AsgiWebsocketSubscriber(loop=loop, username='bob', sid='live-sid')
        ungated = AsgiWebsocketSubscriber(loop=loop)  # cookie gate off (Electron/dev)
        for subscriber in (revoked, live, ungated):
            subscriber.close_callback = Mock()
            notifier.subscribe(subscriber)

        notifier.disconnect_deauthorized(
            lambda username, sid: (username, sid) in {(None, None), ('bob', 'live-sid')},
        )
        loop.run_until_complete(asyncio.sleep(0))  # flush the scheduled callbacks

        assert revoked.closed is True
        revoked.close_callback.assert_called_once_with(WS_CLOSE_POLICY_VIOLATION)
        assert live.closed is False
        live.close_callback.assert_not_called()
        assert ungated.closed is False
        ungated.close_callback.assert_not_called()

        # and the revoked one receives nothing more, even before its close lands
        notifier.broadcast(message_type='user_message', to_send_data={'value': 'after'})
        loop.run_until_complete(asyncio.sleep(0))  # send() enqueues via the loop too
        assert revoked.queue.qsize() == 0
        assert live.queue.qsize() == 1
    finally:
        loop.close()


def test_queue_overflow_retains_dropped_messages():
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
        close_callback.assert_called_once_with(WS_CLOSE_TRY_AGAIN_LATER)
        # an enqueue already scheduled before the overflow closed it is kept too
        subscriber.enqueue('a message scheduled before the disconnect')

        pending = subscriber.drain_pending()
        assert len(pending) == WS_QUEUE_MAXSIZE + 2
        assert pending[0] == 'message 0'
        assert pending[-2] == 'the overflowing message'
        assert pending[-1] == 'a message scheduled before the disconnect'
    finally:
        loop.close()
