import json
import time
from collections import deque
from typing import TYPE_CHECKING, Any

import pytest
from websocket import WebSocketConnectionClosedException, create_connection

from rotkehlchen.concurrency import spawn, wait

if TYPE_CHECKING:
    from collections.abc import Generator


class WebsocketReader:

    def __init__(self, websocket) -> None:
        self.messages: deque = deque()
        self.ws = websocket
        self.should_read = True
        self.died_early = False

    def read_forever(self) -> None:
        while self.should_read:
            try:
                msg = self.ws.recv()
            except (WebSocketConnectionClosedException, OSError):
                # expected when close() closes the socket under us to end the
                # blocking recv -- anything earlier is surfaced via died_early
                self.died_early = self.should_read
                break
            if msg not in {'', '{}'}:
                data = json.loads(msg)
                self.messages.appendleft(data)

    def pop_message(self) -> dict[str, Any]:
        return self.messages.pop()

    def close(self) -> None:
        self.should_read = False
        self.ws.close()  # also unblocks the reader task waiting in recv()

    def messages_num(self) -> int:
        return len(self.messages)

    def wait_until_messages_num(self, num: int, timeout: int) -> None:
        deadline = time.monotonic() + timeout
        while self.messages_num() < num:
            assert self.died_early is False, 'the websocket reader lost its connection'
            assert time.monotonic() < deadline, f'Websocket reader did not contain {num} messages within {timeout} seconds. Only found {self.messages_num()}'  # noqa: E501
            time.sleep(0.2)


@pytest.fixture(name='websocket_connection')
def fixture_websocket_connection_reader(
        rest_api_port,
) -> Generator[WebsocketReader]:
    ws = create_connection(f'ws://127.0.0.1:{rest_api_port}/ws/')
    websocket_reader = WebsocketReader(ws)
    ws.send('{}')  # whatever -- just to subscribe
    reader_task = spawn(websocket_reader.read_forever)
    yield websocket_reader
    websocket_reader.close()
    wait([reader_task], timeout=10)
