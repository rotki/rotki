from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import requests

from rotkehlchen.api.result import FailResult
from rotkehlchen.concurrency.cancellation import TaskCancelledError
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_request_validation_failure_is_invalid_input(
        rotkehlchen_api_server: APIServer,
) -> None:
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'settingsresource'),
        json={'settings': {'taxfree_after_period': -5}},
    )
    assert_error_response(response=response, status_code=HTTPStatus.BAD_REQUEST)
    assert response.json()['cause'] == FailureCause.INVALID_INPUT


def test_unknown_endpoint_is_not_found(rotkehlchen_api_server: APIServer) -> None:
    settings_url = api_url_for(rotkehlchen_api_server, 'settingsresource')
    response = requests.get(settings_url.replace('/settings', '/no_such_endpoint'))
    assert_error_response(response=response, status_code=HTTPStatus.NOT_FOUND)
    assert response.json()['cause'] == FailureCause.NOT_FOUND


def test_unhandled_exception_is_internal(rotkehlchen_api_server: APIServer) -> None:
    with patch.object(
        rotkehlchen_api_server.rest_api.settings_service,
        'get_settings',
        side_effect=ValueError('boom'),
    ):
        response = requests.get(api_url_for(rotkehlchen_api_server, 'settingsresource'))

    assert_error_response(
        response=response,
        contained_in_msg='boom',
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    assert response.json()['cause'] == FailureCause.INTERNAL


def test_finished_task_failures_carry_their_cause(rotkehlchen_api_server: APIServer) -> None:
    """A cancelled task is not a failure to show, a task that died is a bug to report."""
    rest_api = rotkehlchen_api_server.rest_api
    cancelled = MagicMock(task_id=9001, exception=TaskCancelledError(), cancellation_token=None)
    died = MagicMock(
        task_id=9002,
        exception=(error := ValueError('boom')),
        exc_info=(ValueError, error, None),
        cancellation_token=None,
    )
    with rest_api.task_lock:
        rest_api.rotkehlchen.api_tasks.extend((cancelled, died))
    try:
        rest_api._handle_task_death(cancelled)
        rest_api._handle_task_death(died)
        assert rest_api.task_results[9001] == FailResult(
            '',
            HTTPStatus.OK,
            FailureCause.CANCELLED,
        )
        assert rest_api.task_results[9002] == FailResult(
            'The backend query task died unexpectedly: boom',
            HTTPStatus.INTERNAL_SERVER_ERROR,
            FailureCause.INTERNAL,
        )

        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'specific_async_tasks_resource', task_id=9002),
        )
        assert response.status_code == HTTPStatus.OK
        assert (data := response.json()['result'])['status_code'] == HTTPStatus.INTERNAL_SERVER_ERROR  # noqa: E501
        assert data['outcome']['cause'] == FailureCause.INTERNAL
    finally:
        with rest_api.task_lock:
            rest_api.rotkehlchen.api_tasks[:] = [
                x for x in rest_api.rotkehlchen.api_tasks if x not in (cancelled, died)
            ]
            rest_api.task_results.pop(9001, None)


def test_not_found_task_is_not_found(rotkehlchen_api_server: APIServer) -> None:
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'specific_async_tasks_resource', task_id=424242),
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
        result_exists=True,  # the not-found task status
    )
    assert response.json()['cause'] == FailureCause.NOT_FOUND
