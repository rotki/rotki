import re
import subprocess  # noqa: S404
import sys
from http import HTTPStatus

import gevent
import requests


def test_backend():
    """Just runs the backend code to make sure `python -m rotkehlchen` works"""
    proc = subprocess.Popen(
        # Only works with --logtarget stdout. Figure out why it does not work
        # without it. The message should be printed and logged, so it should not
        # make a difference: https://github.com/rotki/rotki/blob/8830172fe3f46c0ec56f1e32a1c24be67018c1bf/rotkehlchen/api/server.py#L280-L282
        ['uv', 'run', 'python', '-m', 'rotkehlchen', '--logtarget', 'stdout'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    timeout = 10
    if sys.platform == 'darwin':
        timeout = 45  # in macos the backend may take a long time to start
    with gevent.Timeout(timeout):
        try:
            while True:
                output = proc.stdout.readline().decode('utf-8')
                if 'rotki is running in __debug__ mode' in output:
                    continue

                if 'rotki REST API server is running at' in output:
                    break

            if (match := re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', output)) is None:
                raise AssertionError(f'Could not parse API endpoint from output: {output!r}')

            url = f'http://{match.group(1)}/api/1/info'
            response = None
            # API startup log is emitted before `WSGIServer.start()` is called, so
            # seeing "server is running at ..." does not guarantee the socket is
            # already accepting connections. Poll until `/api/1/info` succeeds to
            # avoid connection-refused flakes in slower/contended CI workers.
            while True:
                try:
                    response = requests.get(url, timeout=2)
                except requests.RequestException:
                    gevent.sleep(0.1)
                    continue

                if response.status_code == HTTPStatus.OK:
                    break

                gevent.sleep(0.1)

            assert response is not None
            assert 'data_directory' in response.json()['result']

        except gevent.Timeout as e:
            raise AssertionError(
                f'Did not get all expected output in the stdout after {timeout} seconds',
            ) from e
        finally:
            proc.terminate()
            proc.wait()
