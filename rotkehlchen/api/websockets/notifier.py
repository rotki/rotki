import json
import logging
import threading
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.typedefs import WebsocketSendError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.api.asgi import AsgiWebsocketSubscriber
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _ws_send_impl(
        websocket: AsgiWebsocketSubscriber,
        lock: threading.Lock,
        to_send_msg: str,
        success_callback: Callable | None = None,
        success_callback_args: dict[str, Any] | None = None,
        failure_callback: Callable | None = None,
        failure_callback_args: dict[str, Any] | None = None,
) -> None:
    try:
        with lock:
            websocket.send(to_send_msg)
    except WebsocketSendError as e:
        log.error(f'Websocket send with message {to_send_msg} failed due to {e!s}')

        if failure_callback:
            failure_callback_args = {} if failure_callback_args is None else failure_callback_args
            failure_callback(**failure_callback_args)
        return

    if success_callback:  # send success
        success_callback_args = {} if success_callback_args is None else success_callback_args
        success_callback(**success_callback_args)


class RotkiNotifier:

    def __init__(self) -> None:
        # Guards subscribers and locks: subscribe/unsubscribe run on the event-loop
        # thread while broadcast runs on any thread. Without it a broadcast can look
        # up the per-websocket lock of a concurrently unsubscribed websocket and
        # crash with KeyError inside a task done-callback.
        self.subscribers_lock = threading.Lock()
        self.subscribers: list[AsgiWebsocketSubscriber] = []
        self.locks: dict[AsgiWebsocketSubscriber, threading.Lock] = {}
        # Invoked with each message that was still queued for a client when its
        # connection died, so error-class messages reach the polling fallback
        # instead of vanishing. Wired to the messages aggregator at startup.
        self.undelivered_callback: Callable[[str], None] | None = None

    def requeue_undelivered(self, messages: list[str]) -> None:
        """Hand messages a dead client never received to the undelivered callback"""
        if self.undelivered_callback is None:
            return
        for message in messages:
            self.undelivered_callback(message)

    def subscribe(self, websocket: AsgiWebsocketSubscriber) -> None:
        log.info('Websocket with hash id %s subscribed to rotki notifier', hash(websocket))
        with self.subscribers_lock:
            self.subscribers.append(websocket)
            self.locks[websocket] = threading.Lock()

    def unsubscribe(self, websocket: AsgiWebsocketSubscriber) -> None:
        with self.subscribers_lock:
            self.locks.pop(websocket, None)
            try:
                self.subscribers.remove(websocket)
            except ValueError:
                return  # already removed, e.g. by a broadcast that saw it closed

        log.info('Websocket with hash id %s unsubscribed from rotki notifier', hash(websocket))

    def disconnect_deauthorized(
            self,
            is_authorized: Callable[[str | None, str | None], bool],
    ) -> None:
        """Close every connection whose handshake credential no longer authorizes it.

        The /ws gate runs once, at the handshake, and nothing re-reads the cookie for
        the life of the socket. Without this an accepted connection outlives the
        session that opened it and keeps receiving every broadcast -- including, after
        a takeover, the next user's. Asking the predicate per connection means one
        path covers logout, same-user takeover and displacement by a different user.

        Connections drop themselves from the subscriber list through their normal
        teardown once the close lands, so nothing is unsubscribed here.
        """
        with self.subscribers_lock:
            subscribers = list(self.subscribers)

        for websocket in subscribers:
            if is_authorized(websocket.username, websocket.sid):
                continue

            log.info(
                'Disconnecting websocket with hash id %s: its session is no longer active',
                hash(websocket),
            )
            websocket.disconnect()

    def broadcast(
            self,
            message_type: WSMessageType,
            to_send_data: dict[str, Any] | list[Any],
            success_callback: Callable | None = None,
            success_callback_args: dict[str, Any] | None = None,
            failure_callback: Callable | None = None,
            failure_callback_args: dict[str, Any] | None = None,
    ) -> None:
        """Broadcasts a websocket message

        A callback to run on message success and a callback to run on message
        failure can be optionally provided.
        """
        message_data = process_result({'type': message_type, 'data': to_send_data})
        try:
            message = json.dumps(message_data)
        except TypeError as e:
            log.error(f'Failed to broadcast websocket {message_type} message due to {e!s}')
            if failure_callback is not None:
                failure_callback_args = {} if failure_callback_args is None else failure_callback_args  # noqa: E501
                failure_callback(**failure_callback_args)

            return  # get out of the broadcast

        with self.subscribers_lock:  # snapshot with the matching per-websocket locks
            subscribers_with_locks = [
                (websocket, ws_lock) for websocket in self.subscribers
                if (ws_lock := self.locks.get(websocket)) is not None
            ]

        to_remove = []
        spawned_one_broadcast = False
        for websocket, ws_lock in subscribers_with_locks:
            if websocket.closed is True:
                to_remove.append(websocket)
                continue

            _ws_send_impl(
                websocket=websocket,
                lock=ws_lock,
                to_send_msg=message,
                success_callback=success_callback,
                success_callback_args=success_callback_args,
                failure_callback=failure_callback,
                failure_callback_args=failure_callback_args,
            )
            spawned_one_broadcast = True

        if len(to_remove) != 0:  # remove closed websockets from the list, by identity
            with self.subscribers_lock:  # since a concurrent broadcast/unsubscribe shifts indices
                for websocket in to_remove:
                    self.locks.pop(websocket, None)
                    with suppress(ValueError):  # may have been removed concurrently
                        self.subscribers.remove(websocket)
        if spawned_one_broadcast is False and failure_callback is not None:
            failure_callback_args = {} if failure_callback_args is None else failure_callback_args
            failure_callback(**failure_callback_args)
