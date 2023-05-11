import json
import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from gevent.lock import Semaphore
from geventwebsocket import WebSocketApplication
from geventwebsocket.exceptions import WebSocketError
from geventwebsocket.websocket import WebSocket

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _ws_send_impl(
        websocket: WebSocket,
        lock: Semaphore,
        to_send_msg: str,
        success_callback: Optional[Callable] = None,
        success_callback_args: Optional[dict[str, Any]] = None,
        failure_callback: Optional[Callable] = None,
        failure_callback_args: Optional[dict[str, Any]] = None,
) -> None:
    try:
        with lock:
            websocket.send(to_send_msg)
    except WebSocketError as e:
        log.error(f'Websocket send with message {to_send_msg} failed due to {str(e)}')

        if failure_callback:
            failure_callback_args = {} if failure_callback_args is None else failure_callback_args  # noqa: E501
            failure_callback(**failure_callback_args)
        return

    if success_callback:  # send success
        success_callback_args = {} if success_callback_args is None else success_callback_args  # noqa: E501
        success_callback(**success_callback_args)


class RotkiNotifier():

    def __init__(self) -> None:
        self.subscribers: list[WebSocket] = []
        self.locks: dict[WebSocket, Semaphore] = {}

    def subscribe(self, websocket: WebSocket) -> None:
        log.info(f'Websocket with hash id {hash(websocket)} subscribed to rotki notifier')
        self.subscribers.append(websocket)
        self.locks[websocket] = Semaphore()

    def unsubscribe(self, websocket: WebSocket) -> None:
        self.locks.pop(websocket, None)
        with suppress(ValueError):
            self.subscribers.remove(websocket)
            log.info(f'Websocket with hash id {hash(websocket)} unsubscribed from rotki notifier')  # noqa: E501

    def broadcast(
            self,
            message_type: 'WSMessageType',
            to_send_data: Union[dict[str, Any], list[Any]],
            success_callback: Optional[Callable] = None,
            success_callback_args: Optional[dict[str, Any]] = None,
            failure_callback: Optional[Callable] = None,
            failure_callback_args: Optional[dict[str, Any]] = None,
    ) -> None:
        """Broadcasts a websocket message

        A callback to run on message success and a callback to run on message
        failure can be optionally provided.
        """
        message_data = {'type': str(message_type), 'data': to_send_data}
        try:
            message = json.dumps(message_data)
        except TypeError as e:
            log.error(f'Failed to broadcast websocket {message_type} message due to {str(e)}')
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
            failure_callback_args = {} if failure_callback_args is None else failure_callback_args  # noqa: E501
            failure_callback(**failure_callback_args)


class RotkiWSApp(WebSocketApplication):
    """The WebSocket app that's instantiated for every message as it seems from the code

    Only way to pass it extra arguments is through "environ" which is why we have
    a different class "RotkiNotifier" handling the bulk of the work
    """

    def on_open(self, *args: Any, **kwargs: Any) -> None:
        rotki_notifier: RotkiNotifier = self.ws.environ['rotki_notifier']
        rotki_notifier.subscribe(self.ws)

    def on_message(self, message: Optional[str], *args: Any, **kwargs: Any) -> None:
        if self.ws.closed:
            return
        try:
            self.ws.send(message, **kwargs)
        except WebSocketError as e:
            log.warning(
                f'Got WebSocketError {str(e)} for sending message {message} to a websocket',
            )

    def on_close(self, *args: Any, **kwargs: Any) -> None:
        if self.ws.environ is not None:
            rotki_notifier: RotkiNotifier = self.ws.environ['rotki_notifier']
            rotki_notifier.unsubscribe(self.ws)
