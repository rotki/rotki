import os
import platform
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

import psutil
import requests
from flask import url_for

from rotkehlchen.api.server import APIServer, RestAPI
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.utils.gevent_compat import Timeout, sleep

if platform.system() == 'Darwin':
    ASYNC_TASK_WAIT_TIMEOUT = 60
else:
    ASYNC_TASK_WAIT_TIMEOUT = 50


def _wait_for_listening_port(
        port_number: int, tries: int = 10, sleep: float = 0.1, pid: int | None = None,
) -> None:
    if pid is None:
        pid = os.getpid()
    for _ in range(tries):
        sleep(sleep)
        # macOS requires root access for the connections api to work
        # so get connections of the current process only
        connections = psutil.Process(pid).net_connections()
        for conn in connections:
            if conn.status == 'LISTEN' and conn.laddr[1] == port_number:
                return

    raise RuntimeError(f'{port_number} is not bound')


def create_api_server(
        rotki: Rotkehlchen,
        rest_port_number: int,
) -> APIServer:
    api_server = APIServer(RestAPI(rotkehlchen=rotki), rotki.rotki_notifier)

    api_server.flask_app.config['SERVER_NAME'] = f'127.0.0.1:{rest_port_number}'
    api_server.start(
        host='127.0.0.1',
        rest_port=rest_port_number,
    )

    # Fixes flaky test, where requests are done prior to the server initializing
    # the listening socket.
    # https://github.com/raiden-network/raiden/issues/389#issuecomment-305551563
    _wait_for_listening_port(rest_port_number)

    return api_server


def api_url_for(api_server: APIServer, endpoint: str, **kwargs) -> str:
    with api_server.flask_app.app_context():
        return url_for(f'v1_resources.{endpoint}', **kwargs)


def assert_proper_response(
        response: requests.Response | None,
        status_code: HTTPStatus | None = HTTPStatus.OK,
) -> None:
    assert (
        response is not None and
        response.headers['Content-Type'] == 'application/json'
    )
    if status_code:
        assert response.status_code == status_code, f'Response contains unexpected status code. Details {response.json()}'  # noqa: E501


def assert_simple_ok_response(response: requests.Response) -> None:
    assert_proper_response(response)
    data = response.json()
    assert data['result'] is True
    assert data['message'] == ''


def assert_proper_sync_response_with_result(
        response: requests.Response | None,
        message: str | None = None,
        status_code: HTTPStatus = HTTPStatus.OK,
) -> Any:
    assert_proper_response(response, status_code)
    data = response.json()  # type: ignore
    assert data['result'] is not None
    if message:
        assert message in data['message']
    else:
        assert data['message'] == ''
    return data['result']


def assert_proper_response_with_result(
        response: requests.Response,
        rotkehlchen_api_server: APIServer,
        async_query: bool = False,
        timeout: int = ASYNC_TASK_WAIT_TIMEOUT,
) -> Any:
    """Asserts that the response (sync or async) is okay and returns the result."""
    return wait_for_async_task_with_result(
        server=rotkehlchen_api_server,
        task_id=assert_ok_async_response(response),
        timeout=timeout,
    ) if async_query else assert_proper_sync_response_with_result(response)


def _check_error_response_properties(
        response_data: dict[str, Any],
        contained_in_msg: str | list[str] | tuple[str] | None,
        status_code: HTTPStatus | None,
        result_exists: bool,
):
    if status_code != HTTPStatus.INTERNAL_SERVER_ERROR:
        if result_exists:
            assert response_data['result'] is not None
        else:
            assert response_data['result'] in (None, False)
    if contained_in_msg:
        if isinstance(contained_in_msg, str):
            assert contained_in_msg in response_data['message']
        elif isinstance(contained_in_msg, list):
            msg = f'Response: {response_data["message"]} does not match what we expected'
            assert any(x in response_data['message'] for x in contained_in_msg), msg


def assert_error_response(
        response: requests.Response | None,
        contained_in_msg: str | list[str] | tuple[str] | None = None,
        status_code: HTTPStatus = HTTPStatus.BAD_REQUEST,
        result_exists: bool = False,
):
    assert (
        response is not None and
        response.status_code == status_code and
        response.headers['Content-Type'] == 'application/json'
    )
    _check_error_response_properties(
        response_data=response.json(),
        contained_in_msg=contained_in_msg,
        status_code=status_code,
        result_exists=result_exists,
    )


def assert_error_async_response(
        response_data: dict[str, Any] | None,
        contained_in_msg: str | list[str] | None = None,
        status_code: HTTPStatus | None = HTTPStatus.BAD_REQUEST,
        result_exists: bool = False,
):
    assert response_data is not None and response_data.get('status_code') == status_code
    _check_error_response_properties(
        response_data=response_data,
        contained_in_msg=contained_in_msg,
        status_code=status_code,
        result_exists=result_exists,
    )


def assert_ok_async_response(response: requests.Response) -> int:
    """Asserts that the response is okay and contains an async task id"""
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 1
    return int(data['result']['task_id'])


def wait_for_async_task(
        server: APIServer,
        task_id: int,
        timeout=ASYNC_TASK_WAIT_TIMEOUT,
) -> dict[str, Any]:
    """Waits until an async task is ready and when it is returns the response's outcome

    If the task's outcome is not ready within timeout seconds then the test fails"""
    with Timeout(timeout):
        while True:
            response = requests.get(
                api_url_for(server, 'specific_async_tasks_resource', task_id=task_id),
            )
            json_data = response.json()
            data = json_data['result']
            if data is None:
                error_msg = json_data.get('message')
                if error_msg:
                    error_msg = f'Error message: {error_msg}'
                raise AssertionError(
                    f'Tried to wait for task id {task_id} but got no result. {error_msg}',
                )
            status = json_data['result']['status']
            if status == 'completed':
                # Move status code to the outcome dict for easier checking
                status_code = json_data['result'].get('status_code')
                json_data['result']['outcome']['status_code'] = status_code
                return json_data['result']['outcome']
            if status == 'not-found':
                raise AssertionError(f'Tried to wait for task id {task_id} but it is not found')
            if status == 'pending':
                sleep(1)
            else:
                raise AssertionError(
                    f'Waiting for task id {task_id} returned unexpected status {status}',
                )


def wait_for_async_tasks(
        server: APIServer,
        task_ids: Sequence[int],
        timeout=ASYNC_TASK_WAIT_TIMEOUT,
) -> None:
    """Waits until a number of async tasks are ready"""
    searching_set = set(task_ids)
    with Timeout(timeout):
        while True:
            response = requests.get(
                api_url_for(server, 'asynctasksresource', task_id=None),
            )
            json_data = response.json()
            data = json_data['result']
            if searching_set - set(data['completed']) == set():
                break
            else:
                sleep(1)


def wait_for_async_task_with_result(
        server: APIServer,
        task_id: int,
        timeout=ASYNC_TASK_WAIT_TIMEOUT,
) -> dict[str, Any]:
    """Same as wait_for_async_task but returns the result part of the dict"""
    result = wait_for_async_task(server=server, task_id=task_id, timeout=timeout)
    assert result['message'] == ''
    return result['result']
