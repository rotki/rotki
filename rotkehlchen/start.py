from gevent import monkey  # isort:skip
monkey.patch_all()  # isort:skip

import os
import sys
from collections.abc import Callable
from enum import StrEnum, auto
from signal import SIGINT, SIGQUIT, SIGTERM, signal
from subprocess import Popen  # noqa: S404
from types import FrameType

from rotkehlchen.args import app_args  # isort:skip


class ProcessType(StrEnum):
    API_SERVER = auto()
    DB_WRITER = auto()


class ProcessData:
    entrypoint: Callable
    process: Popen | None

    def __init__(self, entrypoint: Callable, process: Popen | None) -> None:
        self.entrypoint = entrypoint
        self.process = process


class ProcessesManager:
    def __init__(self) -> None:
        self.processes: dict[ProcessType, ProcessData] = {
            ProcessType.API_SERVER: ProcessData(
                entrypoint=self.start_api_server,
                process=None,
            ),
            ProcessType.DB_WRITER: ProcessData(
                entrypoint=self.start_db_writer,
                process=None,
            ),
        }

    def start_api_server(self) -> None:
        from rotkehlchen. __main__ import main as backend  # isort:skip  # pylint: disable=import-outside-toplevel  # to make the orchestrator lighter
        backend()

    def start_db_writer(self) -> None:
        from rotkehlchen.db.drivers.server import main as db_writer   # isort:skip  # pylint: disable=import-outside-toplevel  # to make the orchestrator lighter
        db_writer()

    def shutdown(self, signum: int, frame: FrameType | None = None) -> None:  # pylint: disable=unused-argument
        for process_data in self.processes.values():
            if process_data.process is not None:
                process_data.process.send_signal(signum)
                process_data.process.terminate()

        sys.exit(0)


def main() -> None:
    manager = ProcessesManager()

    signal(SIGINT, manager.shutdown)
    if os.name != 'nt':
        signal(SIGTERM, manager.shutdown)
        signal(SIGQUIT, manager.shutdown)
    else:
        # Handle the windows control signal as stated here: https://pyinstaller.org/en/stable/feature-notes.html#signal-handling-in-console-windows-applications-and-onefile-application-cleanup  # noqa: E501
        # This logic handles the signal sent from the bootloader equivalent to sigterm in
        # addition to the signals sent by windows's taskkill.
        # Research documented in https://github.com/yabirgb/rotki-python-research
        import win32api  # pylint: disable=import-outside-toplevel  # isort:skip
        win32api.SetConsoleCtrlHandler(manager.shutdown, True)

    args = app_args(
        prog='rotki orchestrator',
        description='The rotki orchestrator to run other rotki processes.',
    ).parse_args()

    if args.process == 'all':
        executable = [sys.executable] + sys.orig_argv[1:]
        for process_type, process_data in manager.processes.items():
            process_data.process = Popen(executable + ['--process', process_type.value])  # noqa: S603

        if (backend_process := manager.processes[ProcessType.API_SERVER].process) is not None:
            backend_process.wait()
    else:
        manager.processes[ProcessType(args.process)].entrypoint()


if __name__ == '__main__':
    main()
