import subprocess
import gevent
import requests

from http import HTTPStatus


def test_backend():
    """Just runs the backend code to make sure `python -m rotkehlchen` works"""
    proc = subprocess.Popen(
        # Only works with --logtarget stdout. Figure out why it does not work
        # without it. The message should be printed and logged, so it should not
        # make a difference: https://github.com/rotki/rotki/blob/8830172fe3f46c0ec56f1e32a1c24be67018c1bf/rotkehlchen/api/server.py#L280-L282  # noqa: E501
        ['python', '-m', 'rotkehlchen', '--logtarget', 'stdout'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    timeout = 10
    with gevent.Timeout(timeout):
        try:
            while True:
                output = proc.stdout.readline().decode('utf-8')
                if 'Rotki API server is running at' in output:
                    break

            url = f'http://{output.split()[-1]}/api/1/version'
            response = requests.get(url)
            assert response.status_code == HTTPStatus.OK
            assert 'latest_version' in response.json()['result']

        except gevent.Timeout as e:
            raise AssertionError(
                f'Did not get anything in the stdout after {timeout} seconds',
            ) from e
        finally:
            proc.terminate()
            proc.wait()
