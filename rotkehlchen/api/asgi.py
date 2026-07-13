"""The asyncio serving path of the rotki API (phase 4 of the gevent removal
migration, docs/designs/gevent_to_asyncio.md).

One uvicorn server on one port serves both the unchanged Flask REST app --
through a2wsgi's WSGI bridge, which dispatches each request to a worker (a
greenlet-backed "thread" while monkeypatching is active, a real thread after
the flip) -- and a native websocket route at ``/ws``, matching the layout of
the gevent server so the frontend needs no changes.

Websocket subscribers are represented by AsgiWebsocketSubscriber, which
duck-types the small surface of geventwebsocket's WebSocket that RotkiNotifier
uses (``closed`` and ``send()``): broadcasting code enqueues messages onto a
per-client asyncio queue via ``loop.call_soon_threadsafe`` and a per-connection
sender coroutine drains it, so the notifier itself works unchanged in both
serving modes.
"""
import asyncio
import logging
from contextlib import suppress
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, cast

from a2wsgi import WSGIMiddleware

from rotkehlchen.api.session_token import SESSION_COOKIE_NAME, read_session_token
from rotkehlchen.api.websockets.typedefs import WebsocketSendError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from a2wsgi.asgi_typing import ASGIApp, Receive, Scope, Send
    from flask import Flask

    from rotkehlchen.api.rest import RestAPI
    from rotkehlchen.api.websockets.notifier import RotkiNotifier

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Concurrent WSGI dispatches of the bridge -- a hard cap since the flip to real
# threads: requests beyond it queue FIFO in the executor, so once the pool is
# saturated by slow synchronous endpoints even /ping waits. Workers blocked on
# DB or remote IO have released the GIL, so a generous pool is cheap and moves
# that cliff far out; uvicorn's limit_concurrency (see api/server.py) makes
# hitting it fail fast with 503s instead of queueing unboundedly. A dedicated
# worker lane so that /ping, /tasks and /messages can never starve is
# https://github.com/rotki/rotki/issues/12578
WSGI_BRIDGE_WORKERS = 64

# Cap on a client's pending-message queue. Since send() became an enqueue,
# producers never block, so a client that stops reading (frozen renderer,
# suspended laptop, zero-window TCP peer) would otherwise accumulate messages
# unboundedly and invisibly. On overflow the client is disconnected instead:
# the frontend reconnects within seconds and polls /messages while it is
# disconnected, which is strictly better than silent unbounded lag.
WS_QUEUE_MAXSIZE = 4096


class AsgiWebsocketSubscriber:
    """A websocket client of the asyncio server, as seen by RotkiNotifier.

    Duck-types the parts of geventwebsocket's WebSocket that the notifier
    touches: a ``closed`` attribute and a ``send()`` that may be called from
    any greenlet/thread and raises on a dead client.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=WS_QUEUE_MAXSIZE)
        self.closed = False
        # set by _serve_websocket; invoked on the event-loop thread when the
        # queue overflows, to tear the lagging connection down
        self.overflow_callback: Callable[[], None] | None = None
        # messages that found the queue full, retained so teardown hands them to
        # the notifier along with the queued ones instead of losing them
        self._overflowed: list[str] = []

    def enqueue(self, message: str) -> None:
        """Put a message on the queue. Must run on the event-loop thread.

        On overflow the client has not consumed WS_QUEUE_MAXSIZE messages: mark
        it closed -- broadcasts skip and remove closed subscribers, with their
        failure callbacks routing error messages to the polling fallback -- and
        let the overflow callback disconnect it so the frontend reconnects. The
        overflowing message is retained for drain_pending, so an error-class one
        still reaches the polling fallback through the teardown requeue.
        """
        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            self._overflowed.append(message)
            self.closed = True
            if self.overflow_callback is not None:
                self.overflow_callback()

    def send(self, message: str) -> None:
        """Enqueue a message for delivery by the connection's sender coroutine.

        May raise WebsocketSendError if the client is gone or the server's
        event loop has shut down.
        """
        if self.closed:
            raise WebsocketSendError('Websocket subscriber is closed')
        try:
            self.loop.call_soon_threadsafe(self.enqueue, message)
        except RuntimeError as e:  # the event loop is closed (server shutdown)
            self.closed = True
            raise WebsocketSendError(str(e)) from e

    def drain_pending(self) -> list[str]:
        """Return and clear the messages still queued plus the ones dropped on
        queue overflow (queued first: the overflowed ones are newer). To be
        called on the event-loop thread during connection teardown, after closed
        is set, so undelivered messages can be given back to the notifier."""
        pending = []
        while True:
            try:
                pending.append(self.queue.get_nowait())
            except asyncio.QueueEmpty:
                pending.extend(self._overflowed)
                self._overflowed.clear()
                return pending


async def _serve_websocket(
        notifier: 'RotkiNotifier',
        receive: 'Receive',
        send: 'Send',
) -> None:
    """Serve one websocket connection: subscribe it to the notifier, drain its
    queue into the socket and echo back any client messages (parity with the
    gevent websocket app)"""
    message = await receive()
    if message['type'] != 'websocket.connect':
        return
    await send({'type': 'websocket.accept'})
    subscriber = AsgiWebsocketSubscriber(loop=asyncio.get_running_loop())

    async def drain_queue() -> None:
        while True:
            text = await subscriber.queue.get()
            await send({'type': 'websocket.send', 'text': text})

    sender_task = asyncio.create_task(drain_queue())

    async def disconnect_lagging_client() -> None:
        sender_task.cancel()
        with suppress(BaseException):  # swallow CancelledError and any send failure
            await sender_task
        with suppress(Exception):  # the client may be gone already
            await send({'type': 'websocket.close', 'code': 1013})  # 1013: try again later

    def on_overflow() -> None:  # runs on the event-loop thread
        log.warning('Disconnecting a websocket client that stopped consuming messages')
        asyncio.get_running_loop().create_task(disconnect_lagging_client())

    subscriber.overflow_callback = on_overflow
    notifier.subscribe(subscriber)
    try:
        while True:
            message = await receive()
            if message['type'] == 'websocket.disconnect':
                break
            if isinstance(text := message.get('text'), str):
                subscriber.enqueue(text)  # echo, as the gevent app does
    finally:
        subscriber.closed = True
        notifier.unsubscribe(subscriber)
        sender_task.cancel()
        with suppress(BaseException):  # swallow CancelledError and any send failure
            await sender_task
        # give messages the client never received back to the notifier, so
        # error-class ones reach the /messages polling fallback instead of
        # vanishing with the queue
        notifier.requeue_undelivered(subscriber.drain_pending())


async def _handle_lifespan(receive: 'Receive', send: 'Send') -> None:
    while True:
        message = await receive()
        if message['type'] == 'lifespan.startup':
            await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'lifespan.shutdown':
            await send({'type': 'lifespan.shutdown.complete'})
            return


def _ws_session_allowed(rest_api: 'RestAPI', scope: 'Scope') -> bool:
    """Docker session-cookie gate for the /ws handshake (the ASGI equivalent of the
    Flask before_request gate, which does not see websocket upgrades). Inert without a
    key; otherwise the same-origin `rotki_session` cookie rides the handshake and must
    carry the user's active `sid` (a newer login kicks it — #3156). Rejected here
    *before* accept, so an unauthenticated client never completes the handshake."""
    if rest_api.session_key is None:
        return True  # feature off (Electron/dev)
    if rest_api.session_store is None:
        return False
    raw_cookie = ''
    # ASGI scope headers are an iterable of (name, value) byte pairs; the Scope union
    # types `.get` as `object`, so narrow it for the loop below.
    headers = cast('Iterable[tuple[bytes, bytes]]', scope.get('headers', []))
    for name, value in headers:
        if name == b'cookie':
            raw_cookie = value.decode('latin-1')
            break
    morsel = SimpleCookie(raw_cookie).get(SESSION_COOKIE_NAME)
    claims = read_session_token(rest_api.session_key, morsel.value if morsel is not None else '')
    return claims is not None and rest_api.session_store.is_active(claims.username, claims.sid)


def create_asgi_app(
        flask_app: 'Flask',
        rotki_notifier: 'RotkiNotifier',
        rest_api: 'RestAPI',
) -> 'ASGIApp':
    """Compose the rotki ASGI app: /ws and /ws/ go to the native websocket handler,
    everything else to the Flask REST app through the WSGI bridge"""
    wsgi_app = WSGIMiddleware(
        flask_app,  # type: ignore[arg-type]  # Flask is a WSGI callable, mypy can't see it
        workers=WSGI_BRIDGE_WORKERS,
    )

    async def rotki_asgi_app(
            scope: 'Scope',
            receive: 'Receive',
            send: 'Send',
    ) -> None:
        if scope['type'] == 'lifespan':
            await _handle_lifespan(receive=receive, send=send)
        elif scope['type'] == 'websocket':
            if scope['path'] not in {'/ws', '/ws/'} or not _ws_session_allowed(rest_api, scope):
                await send({'type': 'websocket.close'})  # reject the handshake
                return
            await _serve_websocket(notifier=rotki_notifier, receive=receive, send=send)
        else:
            await wsgi_app(scope, receive, send)

    return rotki_asgi_app
