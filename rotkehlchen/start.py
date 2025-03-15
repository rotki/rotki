from gevent import Greenlet, lock, monkey, spawn, subprocess, wait

monkey.patch_all()  # isort:skip

import os
import platform
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum, auto
from types import FrameType

from rotkehlchen.args import app_args
from rotkehlchen.logging import TRACE, add_logging_level
from rotkehlchen.utils.misc import set_signal_handlers

add_logging_level('TRACE', TRACE)


class ProcessType(StrEnum):
    """The processes that are started by the orchestrator."""
    BG_WORKER = auto()
    API_SERVER = auto()
    DB_WRITER = auto()


@dataclass
class ProcessData:
    """Data about a process that is started by the orchestrator.
    entrypoint: The function that should be called to start the process.
    process: Greenlet to handle the Popen instance that is started by the orchestrator."""
    entrypoint: Callable
    greenlet: Greenlet | None
    process: subprocess.Popen | None


class ProcessesManager:
    """Manages the processes that are started by the orchestrator."""
    def __init__(self) -> None:
        self.active = lock.Semaphore(len(ProcessType))
        self.processes: dict[ProcessType, ProcessData] = {
            ProcessType.BG_WORKER: ProcessData(
                entrypoint=self.start_bg_worker,
                greenlet=None,
                process=None,
            ),
            ProcessType.API_SERVER: ProcessData(
                entrypoint=self.start_api_server,
                greenlet=None,
                process=None,
            ),
            ProcessType.DB_WRITER: ProcessData(
                entrypoint=self.start_db_writer,
                greenlet=None,
                process=None,
            ),
        }

    def start_api_server(self) -> None:
        from rotkehlchen. __main__ import main as backend  # isort:skip  # pylint: disable=import-outside-toplevel  # to make the orchestrator lighter
        backend()

    def start_db_writer(self) -> None:
        from rotkehlchen.db.drivers.server import main as db_writer   # isort:skip  # pylint: disable=import-outside-toplevel  # to make the orchestrator lighter
        db_writer()

    def start_bg_worker(self) -> None:
        from rotkehlchen.tasks.server import main as bg_worker  # isort:skip  # pylint: disable=import-outside-toplevel  # to make the orchestrator lighter
        bg_worker()

    def _shutdown(self, signum: int) -> None:
        """Shut down the processes that are started by the orchestrator."""
        for process_type in ProcessType:
            process = self.processes[process_type]
            if process.process is not None:
                with suppress(OSError):
                    process.process.send_signal(signum)
                    if platform.system() == 'Darwin':
                        os.killpg(os.getpgid(process.process.pid), signum)
                process.process.terminate()
                with suppress(subprocess.TimeoutExpired):
                    process.process.wait(timeout=10)
                process.process.kill()
            self.active.release()

    def shutdown(self, signum: int, frame: FrameType | None = None) -> None:  # pylint: disable=unused-argument
        """Start shutdown sequence asynchronously."""
        spawn(self._shutdown, signum)


def _start_process(
        executable: list[str],
        manager: ProcessesManager,
        process_type: ProcessType,
) -> None:
    """Start a fault tolerant process."""
    process = subprocess.Popen(
        executable + ['--process', process_type.value],
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    manager.processes[process_type].process = process
    process.wait()
    if process.stderr is not None:
        sys.stderr.write(process.stderr.read())
        process.stderr.close()
    if process.returncode != 0:
        manager.shutdown(process.returncode)


def main() -> None:
    manager = ProcessesManager()
    args = app_args(
        prog='rotki orchestrator',
        description='The rotki orchestrator to run other rotki processes.',
    ).parse_args()

    if args.process == 'all':
        executable = [sys.executable] + sys.orig_argv[1:]
        for process_type, process_data in manager.processes.items():
            manager.active.acquire()
            process_data.greenlet = spawn(
                _start_process,
                executable,
                manager,
                process_type,
            )

        set_signal_handlers(manager.shutdown)
        wait([manager.active])
    else:
        manager.processes[ProcessType(args.process)].entrypoint()


if __name__ == '__main__':
    main()
