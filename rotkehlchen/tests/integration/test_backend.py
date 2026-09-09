import queue
import re
import subprocess  # noqa: S404
import sys
import threading
import time
from http import HTTPStatus
from typing import IO

import requests


def _read_lines(stream: IO[bytes], lines: queue.Queue[str | None]) -> None:
    """Feed the child's output lines into the queue, None once the stream closes"""
    for raw in iter(stream.readline, b''):
        lines.put(raw.decode('utf-8'))
    lines.put(None)


def test_backend():
    """Just runs the backend code to make sure `python -m rotkehlchen` works.

    The child's stdout is read by a thread so that a backend which hangs at startup fails
    this test at its deadline, with the output captured so far, instead of blocking the
    read forever and taking the whole test job down with it.
    """
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
    deadline = time.monotonic() + timeout
    lines: queue.Queue[str | None] = queue.Queue()
    threading.Thread(target=_read_lines, args=(proc.stdout, lines), daemon=True).start()
    seen_output: list[str] = []
    try:
        while True:
            try:
                output = lines.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                output = None
            assert output is not None, (
                f'Did not get all expected output in the stdout after {timeout} seconds. '
                f'Output so far:\n{"".join(seen_output)}'
            )
            seen_output.append(output)
            if 'rotki is running in __debug__ mode' in output:
                continue

            if 'rotki REST API server is running at' in output:
                break

        if (match := re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', output)) is None:
            raise AssertionError(f'Could not parse API endpoint from output: {output!r}')

        url = f'http://{match.group(1)}/api/1/info'
        response = None
        # API startup log is emitted before the server is listening, so seeing "server is
        # running at ..." does not guarantee the socket is already accepting connections.
        # Poll until `/api/1/info` succeeds to avoid connection-refused flakes in
        # slower/contended CI workers.
        while True:
            assert time.monotonic() < deadline, f'The API did not respond with OK within {timeout} seconds'  # noqa: E501
            try:
                response = requests.get(url, timeout=2)
            except requests.RequestException:
                time.sleep(0.1)
                continue

            if response.status_code == HTTPStatus.OK:
                break

            time.sleep(0.1)

        assert response is not None
        assert 'data_directory' in response.json()['result']

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
