import asyncio
import re
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from flask import Flask

from rotkehlchen.api.asgi import LIVENESS_LANE_PATHS, create_asgi_app
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.v1.resources import AsyncTasksResource, MessagesResource, PingResource

if TYPE_CHECKING:
    from a2wsgi.asgi_typing import ASGIApp, HTTPRequestEvent, HTTPScope, SendEvent


async def _get(app: ASGIApp, path: str) -> tuple[int, bytes]:
    """Send a GET request through the ASGI app and return its status and body"""
    scope: HTTPScope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.3'},
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode(),
        'query_string': b'',
        'root_path': '',
        'headers': [],
        'client': ('127.0.0.1', 50000),
        'server': ('127.0.0.1', 4242),
        'extensions': {},
    }
    messages: list[SendEvent] = []

    async def receive() -> HTTPRequestEvent:  # noqa: RUF029  -- the ASGI receive callable
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message: SendEvent) -> None:  # noqa: RUF029  -- the ASGI send callable
        messages.append(message)

    await app(scope, receive, send)
    status = next(x['status'] for x in messages if x['type'] == 'http.response.start')
    body = b''.join(x['body'] for x in messages if x['type'] == 'http.response.body')
    return status, body


def test_liveness_lane_paths() -> None:
    """Only the routes of /ping, /messages and /tasks(/<id>) take the liveness lane"""
    api_server = APIServer(rest_api=MagicMock(session_key=None), ws_notifier=MagicMock())
    lane_resources = set()
    for rule in api_server.flask_app.url_map.iter_rules():
        path = re.sub(r'<[^>]+>', '42', rule.rule)  # a value every converter accepts
        if LIVENESS_LANE_PATHS.fullmatch(path) is not None:
            view_class = getattr(api_server.flask_app.view_functions[rule.endpoint], 'view_class')  # noqa: B009
            lane_resources.add((rule.rule, view_class))

    assert lane_resources == {
        ('/api/1/ping', PingResource),
        ('/api/1/messages', MessagesResource),
        ('/api/1/tasks', AsyncTasksResource),
        ('/api/1/tasks/<int:task_id>', AsyncTasksResource),
    }


def test_liveness_lane_answers_with_main_pool_saturated() -> None:
    """With every worker of the main pool held by a slow request and more queued
    behind them, the liveness endpoints still answer and other requests wait"""
    flask_app = Flask(__name__)
    release, slow_started = threading.Event(), threading.Semaphore(0)

    @flask_app.route('/api/1/history/events')
    def slow() -> str:
        slow_started.release()
        release.wait(timeout=30)
        return 'slow'

    for rule in ('/api/1/ping', '/api/1/messages', '/api/1/tasks', '/api/1/tasks/<int:task_id>'):
        flask_app.add_url_rule(rule, view_func=lambda **_: 'alive', endpoint=rule)

    liveness_paths = ('/api/1/ping', '/api/1/messages', '/api/1/tasks', '/api/1/tasks/1')

    async def run() -> None:
        with patch('rotkehlchen.api.asgi.WSGI_BRIDGE_WORKERS', 2):
            app = create_asgi_app(flask_app=flask_app, rotki_notifier=MagicMock(), rest_api=MagicMock())  # noqa: E501

        slow_requests = [asyncio.create_task(_get(app, '/api/1/history/events')) for _ in range(3)]
        liveness_requests = []
        try:
            for _ in range(2):  # both workers of the main pool are busy
                assert await asyncio.to_thread(slow_started.acquire, timeout=10) is True

            liveness_requests = [asyncio.create_task(_get(app, path)) for path in liveness_paths]
            _, liveness_pending = await asyncio.wait(liveness_requests, timeout=5)
            slow_done = [x.done() for x in slow_requests]
        finally:  # every request is awaited, so none is left to a closed loop
            release.set()
            outcomes = await asyncio.wait_for(asyncio.gather(*slow_requests, *liveness_requests), timeout=10)  # noqa: E501

        assert liveness_pending == set()
        assert slow_done == [False] * 3  # the third one is still queued behind the first two
        assert slow_started.acquire(blocking=False) is True  # and it ran only after the release
        assert outcomes == [(200, b'slow')] * 3 + [(200, b'alive')] * 4

    asyncio.run(run())
