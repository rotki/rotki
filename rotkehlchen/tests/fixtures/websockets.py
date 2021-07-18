import json
from collections import deque
from typing import Any, Deque, Dict, Generator

import gevent
import pytest
from websocket import create_connection


class WebsocketReader():

    def __init__(self, websocket) -> None:
        self.messages: Deque = deque()
        self.ws = websocket
        self.should_read = True

    def read_forever(self) -> None:
        while self.should_read:
            msg = self.ws.recv()
            if msg != '':
                data = json.loads(msg)
                self.messages.appendleft(data)
            gevent.sleep(0.5)

        # cleanup
        self.ws.close()

    def pop_message(self) -> Dict[str, Any]:
        return self.messages.pop()

    def close(self) -> None:
        self.should_read = False

    def messages_num(self) -> int:
        return len(self.messages)

    def wait_until_messages_num(self, num: int, timeout: int) -> None:
        try:
            with gevent.Timeout(timeout):
                while self.messages_num() != num:
                    gevent.sleep(0.2)
        except gevent.Timeout as e:
            msg = f'Websocket reader did not contain {num} messages within {timeout} seconds'
            raise AssertionError(msg) from e


@pytest.fixture(name='websocket_connection')
def fixture_websocket_connection_reader(
        rotkehlchen_api_server,  # pylint: disable=unused-argument
        websockets_api_port,
) -> Generator[WebsocketReader, None, None]:
    ws = create_connection(f'ws://127.0.0.1:{websockets_api_port}')
    websocket_reader = WebsocketReader(ws)
    ws.send('{}')  # whatever -- just to subscribe
    greenlet = gevent.spawn(websocket_reader.read_forever)
    yield websocket_reader
    websocket_reader.close()
    gevent.joinall([greenlet], timeout=10)
