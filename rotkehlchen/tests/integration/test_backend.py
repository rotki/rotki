import subprocess  # noqa: S404
import sys
from http import HTTPStatus

import gevent
import requests


def test_backend():
    """Just runs the backend code to make sure `python -m rotkehlchen.start` works"""
    proc = subprocess.Popen(
        # Only works with --logtarget stdout. Figure out why it does not work
        # without it. The message should be printed and logged, so it should not
        # make a difference: https://github.com/rotki/rotki/blob/8830172fe3f46c0ec56f1e32a1c24be67018c1bf/rotkehlchen/api/server.py#L280-L282  # noqa: E501
        ['python', '-m', 'rotkehlchen.start', '--logtarget', 'stdout', '--db-api-port', '5556'],
    )
    timeout = 10
    if sys.platform == 'darwin':
        timeout = 30  # in macos the backend may take a long time to start
    with gevent.Timeout(timeout):
        try:
            while True:
                try:
                    response = requests.get('http://127.0.0.1:5042/api/1/info')
                    break
                except requests.exceptions.ConnectionError:
                    gevent.sleep(1)

            assert response.status_code == HTTPStatus.OK
            assert 'data_directory' in response.json()['result']

        except gevent.Timeout as e:
            raise AssertionError(
                f'Could not start the server within {timeout} seconds',
            ) from e
        finally:
            proc.terminate()
            proc.wait()
