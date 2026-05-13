from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response

if TYPE_CHECKING:
    import pytest

    from rotkehlchen.api.server import APIServer


def test_async_task_death_traceback(
        rotkehlchen_api_server: 'APIServer',
        caplog: 'pytest.LogCaptureFixture',
) -> None:
    """Test that the exception traceback appears in the logs for dead async tasks

    Note that there still can be some tasks for which the task's gevent has saved
    no exception info for some reason.
    """
    with patch('rotkehlchen.inquirer.Inquirer.find_usd_price', side_effect=ValueError('Boom')):
        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'exchangeratesresource'),
            json={'async_query': True, 'currencies': ['ETH']},
        )

    assert_proper_response(response)
    assert ' Greenlet for task 0 dies with exception: Boom' in caplog.text
    assert "Exception Name: <class 'ValueError'>" in caplog.text
    assert 'Exception Info: Boom' in caplog.text
    assert 'Traceback:' in caplog.text
    tb_start = caplog.text.find('Traceback:')  # Check there is stuff after Traceack
    file_count = caplog.text.count('File', tb_start)
    assert file_count > 2, 'Traceback should involve more than 2 files'


def test_unhandled_external_exception_logs_traceback(
        rotkehlchen_api_server: 'APIServer',
        caplog: 'pytest.LogCaptureFixture',
) -> None:
    with patch.object(
        rotkehlchen_api_server.rest_api,
        'get_exchange_rates',
        side_effect=TypeError("expected string or bytes-like object, got 'NoneType'"),
    ):
        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'exchangeratesresource'),
            json={'currencies': ['ETH'], 'async_query': False},
        )

    assert_error_response(
        response,
        contained_in_msg="expected string or bytes-like object, got 'NoneType'",
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    assert 'Unhandled exception when processing endpoint request' in caplog.text
    assert 'Traceback (most recent call last):' in caplog.text
