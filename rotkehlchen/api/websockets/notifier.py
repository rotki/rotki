import json
import logging
import threading
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.typedefs import WebsocketSendError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from rotkehlchen.api.asgi import AsgiWebsocketSubscriber
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _ws_send_impl(
        websocket: 'AsgiWebsocketSubscriber',
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
        self.subscribers: list[AsgiWebsocketSubscriber] = []
        self.locks: dict[AsgiWebsocketSubscriber, threading.Lock] = {}

    def subscribe(self, websocket: 'AsgiWebsocketSubscriber') -> None:
        log.info('Websocket with hash id %s subscribed to rotki notifier', hash(websocket))
        self.subscribers.append(websocket)
        self.locks[websocket] = threading.Lock()

    def unsubscribe(self, websocket: 'AsgiWebsocketSubscriber') -> None:
        self.locks.pop(websocket, None)
        with suppress(ValueError):
            self.subscribers.remove(websocket)
            log.info('Websocket with hash id %s unsubscribed from rotki notifier', hash(websocket))

    def broadcast(
            self,
            message_type: 'WSMessageType',
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

        to_remove_indices = set()
        spawned_one_broadcast = False
        for idx, websocket in enumerate(self.subscribers):
            if websocket.closed is True:
                to_remove_indices.add(idx)
                continue

            _ws_send_impl(
                websocket=websocket,
                lock=self.locks[websocket],
                to_send_msg=message,
                success_callback=success_callback,
                success_callback_args=success_callback_args,
                failure_callback=failure_callback,
                failure_callback_args=failure_callback_args,
            )
            spawned_one_broadcast = True

        if len(to_remove_indices) != 0:  # removed closed websockets from the list
            self.subscribers = [
                i for j, i in enumerate(self.subscribers) if j not in to_remove_indices
            ]
        if spawned_one_broadcast is False and failure_callback is not None:
            failure_callback_args = {} if failure_callback_args is None else failure_callback_args
            failure_callback(**failure_callback_args)
