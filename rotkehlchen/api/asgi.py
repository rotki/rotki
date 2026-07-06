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
    from collections.abc import Iterable

    from a2wsgi.asgi_typing import ASGIApp, Receive, Scope, Send
    from flask import Flask

    from rotkehlchen.api.rest import RestAPI
    from rotkehlchen.api.websockets.notifier import RotkiNotifier

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Concurrent WSGI dispatches of the bridge. While monkeypatching is active the
# "threads" are greenlets so this is not a hard parallelism limit; after the
# flip it becomes the worker pool size decision of phase 5.
WSGI_BRIDGE_WORKERS = 30


class AsgiWebsocketSubscriber:
    """A websocket client of the asyncio server, as seen by RotkiNotifier.

    Duck-types the parts of geventwebsocket's WebSocket that the notifier
    touches: a ``closed`` attribute and a ``send()`` that may be called from
    any greenlet/thread and raises on a dead client.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False

    def send(self, message: str) -> None:
        """Enqueue a message for delivery by the connection's sender coroutine.

        May raise WebsocketSendError if the client is gone or the server's
        event loop has shut down.
        """
        if self.closed:
            raise WebsocketSendError('Websocket subscriber is closed')
        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, message)
        except RuntimeError as e:  # the event loop is closed (server shutdown)
            self.closed = True
            raise WebsocketSendError(str(e)) from e


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
    notifier.subscribe(subscriber)

    async def drain_queue() -> None:
        while True:
            text = await subscriber.queue.get()
            await send({'type': 'websocket.send', 'text': text})

    sender_task = asyncio.create_task(drain_queue())
    try:
        while True:
            message = await receive()
            if message['type'] == 'websocket.disconnect':
                break
            if isinstance(text := message.get('text'), str):
                subscriber.queue.put_nowait(text)  # echo, as the gevent app does
    finally:
        subscriber.closed = True
        notifier.unsubscribe(subscriber)
        sender_task.cancel()
        with suppress(BaseException):  # swallow CancelledError and any send failure
            await sender_task


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
