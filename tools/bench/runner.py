"""Boots and talks to a real rotki backend process for benchmarking"""
import socket
import subprocess  # noqa: S404
import time
from pathlib import Path
from types import TracebackType
from typing import Any, Final, Self

import requests

PING_POLL_SECONDS: Final = 0.05
DEFAULT_START_TIMEOUT: Final = 120
REQUEST_TIMEOUT: Final = 300


class BenchError(RuntimeError):
    """Any failure that invalidates a benchmark run"""


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class BackendRunner:
    """One backend process bound to a data directory.

    The task manager stays enabled on purpose (design §3.3): real runs never
    disable it, so neither do benchmarks.
    """

    def __init__(self, repo_root: Path, data_dir: Path, log_dir: Path) -> None:
        self.repo_root = repo_root
        self.data_dir = data_dir
        self.log_dir = log_dir
        self.port = free_port()
        self.process: subprocess.Popen | None = None
        self.session = requests.Session()

    def url(self, path: str) -> str:
        return f'http://127.0.0.1:{self.port}/api/1{path}'

    def start(self, timeout: float = DEFAULT_START_TIMEOUT) -> float:
        """Start the backend and wait for the first successful ping.
        Returns the boot duration in milliseconds."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with (self.log_dir / 'stdout.log').open('ab') as stdout:
            self.process = subprocess.Popen(  # noqa: S603  # trusted args
                [  # noqa: S607
                    'uv', 'run', 'python', '-m', 'rotkehlchen',
                    '--rest-api-port', str(self.port),
                    '--api-cors', 'http://localhost:*',
                    '--data-dir', str(self.data_dir),
                    '--logfile', str(self.log_dir / 'rotki.log'),
                ],
                cwd=self.repo_root,
                stdout=stdout,
                stderr=subprocess.STDOUT,
            )
        start = time.perf_counter()
        deadline = start + timeout
        while time.perf_counter() < deadline:
            if self.process.poll() is not None:
                raise BenchError(
                    f'backend exited with code {self.process.returncode} during startup. '
                    f'See {self.log_dir / "stdout.log"}',
                )
            try:
                if self.session.get(self.url('/ping'), timeout=2).status_code == 200:
                    return (time.perf_counter() - start) * 1000
            except requests.RequestException:
                time.sleep(PING_POLL_SECONDS)
        raise BenchError(f'backend did not answer ping within {timeout}s')

    def stop(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=15)
        self.process = None

    def request(self, method: str, path: str, json: dict | None = None) -> dict[str, Any]:
        """Perform an API call and return the response 'result'. Raises
        BenchError on transport errors or API-level errors so a failing
        operation can never be silently timed as fast."""
        try:
            response = self.session.request(
                method=method,
                url=self.url(path),
                json=json,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            raise BenchError(f'{method} {path} failed: {e}') from e
        payload = response.json()
        if payload.get('result') is None:
            raise BenchError(f'{method} {path} returned error: {payload.get("message")}')
        return payload['result']

    def __enter__(self) -> Self:
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
    ) -> None:
        self.stop()
