import json
from rotkehlchen.utils.gevent_compat import Timeout, joinall, sleep, spawn
from collections import deque
from collections.abc import Generator
from typing import Any

import pytest
from websocket import create_connection


class WebsocketReader:

    def __init__(self, websocket) -> None:
        self.messages: deque = deque()
        self.ws = websocket
        self.should_read = True

    def read_forever(self) -> None:
        while self.should_read:
            msg = self.ws.recv()
            if msg not in {'', '{}'}:
                data = json.loads(msg)
                self.messages.appendleft(data)
            sleep(0.2)

        # cleanup
        self.ws.close()

    def pop_message(self) -> dict[str, Any]:
        return self.messages.pop()

    def close(self) -> None:
        self.should_read = False

    def messages_num(self) -> int:
        return len(self.messages)

    def wait_until_messages_num(self, num: int, timeout: int) -> None:
        try:
            with Timeout(timeout):
                while self.messages_num() < num:
                    sleep(0.2)
        except Timeout as e:
            msg = f'Websocket reader did not contain {num} messages within {timeout} seconds. Only found {self.messages_num()}'  # noqa: E501
            raise AssertionError(msg) from e


@pytest.fixture(name='websocket_connection')
def fixture_websocket_connection_reader(
        rest_api_port,
) -> Generator[WebsocketReader, None, None]:
    ws = create_connection(f'ws://127.0.0.1:{rest_api_port}/ws')
    websocket_reader = WebsocketReader(ws)
    ws.send('{}')  # whatever -- just to subscribe
    greenlet = spawn(websocket_reader.read_forever)
    yield websocket_reader
    websocket_reader.close()
    joinall([greenlet], timeout=10)
