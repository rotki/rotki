import asyncio
import json
import logging
import platform
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from unittest.mock import ANY, Mock, patch

import pytest

from rotkehlchen.api.asgi import (
    WS_CLOSE_POLICY_VIOLATION,
    WS_CLOSE_TRY_AGAIN_LATER,
    WS_QUEUE_MAXSIZE,
    AsgiWebsocketSubscriber,
)
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.api.websockets.typedefs import (
    DeliveryPolicy,
    UserMessageEntry,
    UserMessageFeature,
    UserMessageOperation,
    UserMessageRecord,
    WebsocketSendError,
    WSMessageType,
    delivery_of,
)
from rotkehlchen.concurrency import spawn, wait
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.tests.utils.messages import (
    consume_error_payloads,
    consume_errors,
    consume_warnings,
)
from rotkehlchen.types import Location
from rotkehlchen.user_messages import (
    MAX_HELD_EVENTS,
    MAX_HELD_REPORTS,
    MAX_HELD_STATES,
    MAX_HELD_USER_MESSAGES,
    AuthFailure,
    BadData,
    Internal,
    LocalDbProblem,
    MessageClassification,
    MessagesAggregator,
    MissingPrice,
    NetworkFailure,
    UnknownAssetSeen,
    Unsupported,
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
        'data': {
            'verbosity': 'error',
            'value': 'an error',
            'group': ['error', 'local_db', None, 'tag'],
        },
    }))
    msg_aggregator.requeue_undelivered(json.dumps({
        'type': 'user_message',
        'data': {
            'verbosity': 'warning',
            'value': 'a warning',
            'group': ['warning', 'local_db', None, 'tag'],
        },
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

    assert consume_errors(msg_aggregator) == ['an error', snapshot_error_msg, unknown_asset_msg]
    assert consume_warnings(msg_aggregator) == ['a warning']


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

    assert consume_error_payloads(msg_aggregator) == [{
        'type': 'user_message',
        'data': {
            'verbosity': 'error',
            'value': msg,
            'key': 'bad_data',
            'subject': 'kucoin',
            'fields': {'record': 'balance', 'error': 'Missing key: amount'},
            'group': ['error', 'bad_data', 'kucoin', 'balance'],
        },
    }]
    assert consume_errors(msg_aggregator) == []  # the payload read drained the queue
    assert consume_warnings(msg_aggregator) == ['a warning']


def test_every_message_type_has_a_delivery_policy() -> None:
    """delivery_of answers for every type at runtime too, not only under mypy."""
    for message_type in WSMessageType:
        assert delivery_of(message_type, {}).policy in DeliveryPolicy


def test_repeats_of_one_problem_are_held_once_with_a_count() -> None:
    """Messages with one identity are one held entry that counts every send and keeps the
    newest sentence, however the text varies; a different identity is a separate entry.
    Text readers still see the entry once per send."""
    msg_aggregator = MessagesAggregator()
    for index in range(3):
        msg_aggregator.add_error(
            f'Binance rejected the API key of main ({index})',
            classification=AuthFailure(service='binance', account='main'),
            subject=Location.BINANCE,
        )
    msg_aggregator.add_error(
        'Binance rejected the API key of other',
        classification=AuthFailure(service='binance', account='other'),
        subject=Location.BINANCE,
    )

    messages, dropped = msg_aggregator.consume_held()
    assert [(message['data']['value'], message['count']) for message in messages] == [
        ('Binance rejected the API key of main (2)', 3),
        ('Binance rejected the API key of other', 1),
    ]
    assert dropped == 0

    for _ in range(2):
        msg_aggregator.add_error('kucoin is down', classification=_TAG_PROBLEM)
    assert consume_errors(msg_aggregator) == ['kucoin is down', 'kucoin is down']


def test_state_keeps_only_the_latest_message_per_key() -> None:
    msg_aggregator = MessagesAggregator()
    for blockchain in ('eth', 'optimism', 'eth'):
        msg_aggregator.add_message(
            WSMessageType.REFRESH_BALANCES,
            {'type': 'blockchain_balances', 'blockchain': blockchain},
        )
    msg_aggregator.add_message(WSMessageType.PREMIUM_STATUS_UPDATE, {'is_premium_active': True})
    msg_aggregator.add_message(WSMessageType.PREMIUM_STATUS_UPDATE, {'is_premium_active': False})

    messages, _ = msg_aggregator.consume_held()
    assert [(message['type'], message['data']) for message in messages] == [
        ('refresh_balances', {'type': 'blockchain_balances', 'blockchain': 'optimism'}),
        ('refresh_balances', {'type': 'blockchain_balances', 'blockchain': 'eth'}),
        ('premium_status_update', {'is_premium_active': False}),
    ]


def test_indexer_notices_for_one_chain_are_kept_per_reason() -> None:
    """A temporary incomplete-response notice must not replace a key notice for the chain."""
    msg_aggregator = MessagesAggregator()
    for reason in ('etherscan_paid_key_required', *['blockscout_incomplete'] * 2):
        msg_aggregator.add_message(
            WSMessageType.NO_AVAILABLE_INDEXERS,
            {'chain': 'base', 'reason': reason},
        )

    messages, _ = msg_aggregator.consume_held()
    assert [message['data']['reason'] for message in messages] == [
        'etherscan_paid_key_required',
        'blockscout_incomplete',
    ]


def test_errors_read_only_the_failures() -> None:
    """Reading the errors leaves an import result and a state change held for the client."""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_message(
        WSMessageType.PROGRESS_UPDATES,
        {'subtype': 'csv_import_result', 'total': 2, 'processed': 2},
    )
    msg_aggregator.add_message(WSMessageType.PREMIUM_STATUS_UPDATE, {'is_premium_active': True})
    msg_aggregator.add_error('kucoin is down', classification=_TAG_PROBLEM)
    msg_aggregator.add_message(WSMessageType.ORACLE_PENALIZED, {'oracle': 'coingecko'})

    assert [error['type'] for error in consume_error_payloads(msg_aggregator)] == [
        'user_message',
        'oracle_penalized',
    ]
    messages, _ = msg_aggregator.consume_held()
    assert [message['type'] for message in messages] == [
        'progress_updates',
        'premium_status_update',
    ]


def test_import_result_is_held_while_other_progress_is_dropped() -> None:
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_message(
        WSMessageType.PROGRESS_UPDATES,
        {'subtype': 'undecoded_transactions', 'total': 10, 'processed': 5},
    )
    msg_aggregator.add_message(
        WSMessageType.PROGRESS_UPDATES,
        import_result := {'subtype': 'csv_import_result', 'total': 2, 'processed': 2},
    )

    messages, _ = msg_aggregator.consume_held()
    assert messages == [{
        'type': 'progress_updates',
        'data': import_result,
        'count': 1,
        'last_sent': ANY,
    }]


def test_held_message_carries_when_it_was_last_sent() -> None:
    """A client reading a held message later can tell when it happened, and a repeat moves
    that time forward."""
    msg_aggregator = MessagesAggregator()
    with patch('rotkehlchen.user_messages.ts_now', side_effect=[1000, 1600]):
        for _ in range(2):
            msg_aggregator.add_error('kucoin is down', classification=_TAG_PROBLEM)

    messages, _ = msg_aggregator.consume_held()
    assert [(message['count'], message['last_sent']) for message in messages] == [(2, 1600)]


def test_dropped_message_is_logged_in_full(caplog: pytest.LogCaptureFixture) -> None:
    """The client is told only how many messages were dropped, so the log keeps each one."""
    msg_aggregator = MessagesAggregator()
    for index in range(MAX_HELD_REPORTS + 1):
        msg_aggregator.add_message(WSMessageType.ORACLE_PENALIZED, {'oracle': f'oracle{index}'})

    dropped_logs = [
        record.getMessage() for record in caplog.records
        if record.levelno == logging.WARNING and 'Dropped a held' in record.getMessage()
    ]
    assert len(dropped_logs) == 1
    assert 'oracle_penalized' in dropped_logs[0]
    assert '"oracle": "oracle0"' in dropped_logs[0]


@pytest.mark.parametrize(('message_type', 'limit', 'data_of'), [
    (WSMessageType.NEW_TOKEN_DETECTED, MAX_HELD_EVENTS, lambda index: {'token_identifier': str(index)}),  # noqa: E501
    (WSMessageType.NEGATIVE_BALANCE_DETECTED, MAX_HELD_STATES, lambda index: {'event_identifier': index}),  # noqa: E501
    (WSMessageType.ORACLE_PENALIZED, MAX_HELD_REPORTS, lambda index: {'oracle': str(index)}),
])
def test_full_store_drops_its_oldest_entry_and_counts_it(
        message_type: WSMessageType,
        limit: int,
        data_of: Callable[[int], dict[str, Any]],
) -> None:
    msg_aggregator = MessagesAggregator()
    for index in range(limit + 2):
        msg_aggregator.add_message(message_type, data_of(index))

    messages, dropped = msg_aggregator.consume_held()
    assert [message['data'] for message in messages] == [
        data_of(index) for index in range(2, limit + 2)
    ]
    assert dropped == 2
    assert msg_aggregator.consume_held() == ([], 0)


def test_repeating_failures_cannot_push_out_an_event_or_a_state() -> None:
    """Each store is bounded on its own, so a storm of distinct failures only ever drops
    older failures."""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_message(
        WSMessageType.NEW_TOKEN_DETECTED,
        token := {'token_identifier': 'A'},
    )
    msg_aggregator.add_message(
        WSMessageType.PREMIUM_STATUS_UPDATE,
        premium := {'is_premium_active': True},
    )
    for index in range(MAX_HELD_USER_MESSAGES + 10):
        msg_aggregator.add_error(
            f'unknown asset {index}',
            classification=UnknownAssetSeen(identifier=str(index)),
        )

    messages, dropped = msg_aggregator.consume_held()
    assert [message['data'] for message in messages[:2]] == [token, premium]
    assert len(messages) == 2 + MAX_HELD_USER_MESSAGES
    assert dropped == 10


def test_a_storm_of_one_failure_is_one_entry_beside_reports_and_credentials() -> None:
    """A failure that repeats with varying text is one held entry, so it cannot push out
    rejected credentials; and user messages are bounded in a store of their own, apart
    from the structured reports."""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_error(
        'Binance rejected the API key of main',
        classification=AuthFailure(service='binance', account='main'),
    )
    msg_aggregator.add_message(WSMessageType.ORACLE_PENALIZED, oracle := {'oracle': 'coingecko'})
    for index in range(MAX_HELD_USER_MESSAGES + 10):
        msg_aggregator.add_error(f'Skipping transaction {index}', classification=_TAG_PROBLEM)

    messages, dropped = msg_aggregator.consume_held()
    assert [(message['data'].get('value'), message['count']) for message in messages] == [
        ('Binance rejected the API key of main', 1),
        (None, 1),
        (f'Skipping transaction {MAX_HELD_USER_MESSAGES + 9}', MAX_HELD_USER_MESSAGES + 10),
    ]
    assert messages[1]['data'] == oracle
    assert dropped == 0


def test_a_message_that_does_not_serialize_is_dropped_not_raised(
        caplog: pytest.LogCaptureFixture,
) -> None:
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_message(WSMessageType.ORACLE_PENALIZED, {'oracle': object()})

    assert msg_aggregator.consume_held() == ([], 0)
    assert 'Could not hold a oracle_penalized message' in caplog.text


def test_clear_drops_everything_held() -> None:
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_error('an error', classification=_TAG_PROBLEM)
    msg_aggregator.add_message(WSMessageType.NEW_TOKEN_DETECTED, {'token_identifier': 'A'})
    for index in range(MAX_HELD_REPORTS + 1):
        msg_aggregator.add_warning(f'warning {index}', classification=_TAG_PROBLEM)

    msg_aggregator.clear()
    assert msg_aggregator.consume_held() == ([], 0)


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

    messages, _ = msg_aggregator.consume_held()
    assert [{'type': message['type'], 'data': message['data']} for message in messages] == [
        {'type': 'user_message', 'data': {
            'verbosity': 'error',
            'value': 'an error',
            'key': 'local_db',
            'subject': None,
            'fields': {'entry': 'tag'},
            'group': ['error', 'local_db', None, 'tag'],
        }},
        {'type': 'balance_snapshot_error', 'data': snapshot_error},
        {'type': 'missing_api_key', 'data': missing_key},
    ]


@pytest.mark.parametrize(('classification', 'subject', 'group'), [
    # unreadable data and unreachable remotes fold per location and record
    (BadData(record=UserMessageRecord.TRADE, error='x'), Location.KUCOIN, ['error', 'bad_data', 'kucoin', 'trade']),  # noqa: E501
    (NetworkFailure(record=UserMessageRecord.BALANCE, error='x'), Location.KRAKEN, ['error', 'network', 'kraken', 'balance']),  # noqa: E501
    # rejected credentials stay per account, so the key that needs replacing stays visible
    (AuthFailure(service='binance', account='main'), Location.BINANCE, ['error', 'auth', 'binance', 'binance', 'main']),  # noqa: E501
    # unknown assets stay per asset, so each one that needs adding stays visible
    (UnknownAssetSeen(identifier='FOO'), None, ['error', 'unknown_asset', None, 'FOO']),
    (LocalDbProblem(entry=UserMessageEntry.TAG), None, ['error', 'local_db', None, 'tag']),
    (MissingPrice(asset='ETH', timestamp=1), Location.KRAKEN, ['error', 'price', 'kraken']),
    (Unsupported(feature=UserMessageFeature.ASSET), Location.KRAKEN, ['error', 'unsupported', 'kraken', 'asset']),  # noqa: E501
    (Internal(operation=UserMessageOperation.BACKGROUND_TASK), None, ['error', 'internal', None, 'background_task']),  # noqa: E501
])
def test_each_family_declares_its_identity(
        classification: MessageClassification,
        subject: Location | None,
        group: list[str | None],
) -> None:
    """`group` is the one definition of which messages are one problem: the free-text
    `error` and asset/timestamp details never take part."""
    msg_aggregator = MessagesAggregator()
    msg_aggregator.add_error('a sentence', classification=classification, subject=subject)
    messages, _ = msg_aggregator.consume_held()
    assert json.loads(json.dumps(messages[0]['data']['group'])) == group


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
        'group': ['error', 'bad_data', 'kucoin', 'balance'],
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
        'group': ['warning', 'local_db', None, 'tag'],
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
    assert consume_errors(msg_aggregator) == consume_warnings(msg_aggregator) == []


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


def test_broadcast_falls_back_only_when_no_client_accepted_the_message() -> None:
    """A message one client received must not also be held for polling because another
    client's send failed, or the first client would see it twice."""
    def client(accepts: bool) -> Mock:
        send = Mock(side_effect=None if accepts else WebsocketSendError('gone'))
        return Mock(closed=False, send=send)

    for clients, expected_calls in (
            ((client(accepts=True), client(accepts=False)), 0),
            ((client(accepts=False), client(accepts=False)), 1),
    ):
        notifier = RotkiNotifier()
        for subscriber in clients:
            notifier.subscribe(subscriber)
        notifier.broadcast(
            message_type=WSMessageType.USER_MESSAGE,
            to_send_data={'value': 'a message'},
            failure_callback=(failure_callback := Mock()),
        )
        assert failure_callback.call_count == expected_calls


def test_revoked_websocket_gives_back_no_undelivered_messages() -> None:
    """Logout clears what is held before a revoked socket finishes tearing down, so what
    that socket never delivered must not be held again for the next session. A socket
    closed for falling behind still gives its messages back."""
    loop = asyncio.new_event_loop()
    try:
        revoked, lagging = AsgiWebsocketSubscriber(loop=loop), AsgiWebsocketSubscriber(loop=loop)
        for subscriber in (revoked, lagging):
            subscriber.enqueue('undelivered')

        revoked.disconnect()
        lagging.disconnect(WS_CLOSE_TRY_AGAIN_LATER)

        assert revoked.take_undelivered() == []
        assert lagging.take_undelivered() == ['undelivered']
    finally:
        loop.close()
