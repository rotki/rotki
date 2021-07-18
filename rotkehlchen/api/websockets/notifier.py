import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from geventwebsocket import WebSocketApplication
from geventwebsocket.exceptions import WebSocketError
from geventwebsocket.websocket import WebSocket

from rotkehlchen.greenlets import GreenletManager

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)


def _ws_send_impl(
        websocket: WebSocket,
        to_send_msg: str,
        success_callback: Optional[Callable] = None,
        success_callback_args: Optional[Dict[str, Any]] = None,
        failure_callback: Optional[Callable] = None,
        failure_callback_args: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        websocket.send(to_send_msg)
    except WebSocketError as e:
        logger.error(f'Websocket send with message {to_send_msg} failed due to {str(e)}')

        if failure_callback:
            failure_callback_args = {} if failure_callback_args is None else failure_callback_args  # noqa: E501
            failure_callback(**failure_callback_args)
        return

    if success_callback:  # send success
        success_callback_args = {} if success_callback_args is None else success_callback_args  # noqa: E501
        success_callback(**success_callback_args)


class RotkiNotifier():

    def __init__(
            self,
            greenlet_manager: GreenletManager,
    ) -> None:
        self.greenlet_manager = greenlet_manager
        self.subscribers: List[WebSocket] = []

    def subscribe(self, websocket: WebSocket) -> None:
        logger.info(f'Websocket with hash id {hash(websocket)} subscribed to rotki notifier')
        self.subscribers.append(websocket)

    def unsubscribe(self, websocket: WebSocket) -> None:
        try:
            self.subscribers.remove(websocket)
            logger.info(f'Websocket with hash id {hash(websocket)} unsubscribed from rotki notifier')  # noqa: E501
        except ValueError:
            pass

    def broadcast(
            self,
            message_type: 'WSMessageType',
            to_send_data: Dict[str, Any],
            success_callback: Optional[Callable] = None,
            success_callback_args: Optional[Dict[str, Any]] = None,
            failure_callback: Optional[Callable] = None,
            failure_callback_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        message_data = {'type': str(message_type), 'data': to_send_data}
        message = json.dumps(message_data)  # TODO: Check for dumps error
        to_remove_indices = set()
        for idx, websocket in enumerate(self.subscribers):
            if websocket.closed is True:
                to_remove_indices.add(idx)
                continue

            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Websocket send for {str(message_type)}',
                exception_is_error=True,
                method=_ws_send_impl,
                websocket=websocket,
                to_send_msg=message,
                success_callback=success_callback,
                success_callback_args=success_callback_args,
                failure_callback=failure_callback,
                failure_callback_args=failure_callback_args,
            )

        if len(to_remove_indices) != 0:  # removed closed websockets from the list
            self.subscribers = [
                i for j, i in enumerate(self.subscribers) if j not in to_remove_indices
            ]


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
            logger.warning(
                f'Got WebSocketError {str(e)} for sending message {message} to a websocket',
            )

    def on_close(self, *args: Any, **kwargs: Any) -> None:
        if self.ws.environ is not None:
            rotki_notifier: RotkiNotifier = self.ws.environ['rotki_notifier']
            rotki_notifier.unsubscribe(self.ws)
