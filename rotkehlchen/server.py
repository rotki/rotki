import importlib.metadata
import logging
import os
import signal
import sys
import threading
from typing import Any

import rsqlite

from rotkehlchen.api.server import APIServer, RestAPI
from rotkehlchen.args import app_args
from rotkehlchen.db.misc import get_sqlcipher_version_string
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkehlchenServer:
    def __init__(self) -> None:
        """Initializes the backend server
        May raise:
        - SystemPermissionError due to the given args containing a datadir
        that does not have the correct permissions
        """
        # Since the gevent removal business logic runs on preemptive threads sharing
        # the GIL. A thread waiting for the GIL (e.g. a DB read stepping sqlite rows,
        # or the api server's event loop) waits up to the switch interval per
        # acquisition while a CPU-bound thread (decoding, PnL processing) runs, so at
        # the 5ms default a row fetch degrades to ~200 rows/s next to two busy
        # threads. 0.5ms recovers more than 20x of that for ~1% CPU-bound throughput
        # cost (measured; see docs/designs/gevent_to_asyncio.md risk #6).
        sys.setswitchinterval(0.0005)
        arg_parser = app_args(
            prog='rotki',
            description=(
                'rotki, the portfolio tracker and accounting tool that respects your privacy'
            ),
        )
        self.args = arg_parser.parse_args()
        add_logging_level('TRACE', TRACE)
        configure_logging(self.args)
        self.rotkehlchen = Rotkehlchen(self.args)
        self.stop_event = threading.Event()
        # never released: makes shutdown() run once even when two signal paths
        # fire together (e.g. the windows console ctrl handler and SIGINT)
        self._shutdown_lock = threading.Lock()
        if ',' in self.args.api_cors:
            domain_list = [str(domain) for domain in self.args.api_cors.split(',')]
        else:
            domain_list = [str(self.args.api_cors)]
        self.api_server = APIServer(
            rest_api=RestAPI(rotkehlchen=self.rotkehlchen),
            ws_notifier=self.rotkehlchen.rotki_notifier,
            cors_domain_list=domain_list,
        )

    def shutdown(self, *args: Any) -> None:
        """Shut the server down. Also used as a signal/console-ctrl handler,
        hence the unused extra arguments."""
        if self._shutdown_lock.acquire(blocking=False) is False:
            return  # a concurrent signal already runs the shutdown

        log.debug('Shutdown initiated')
        self.api_server.stop()
        self.stop_event.set()

    def main(self) -> None:
        # log version of some special dependencies
        log.info(f'sqlite version: {rsqlite.sqlite_version}')
        log.info(f'rotki-pysqlcipher version: {importlib.metadata.version("sqlcipher3")}')
        log.info(f'SQLCipher version: {get_sqlcipher_version_string()}')
        log.info(f'GIL disabled: {not sys._is_gil_enabled()}')
        if os.name != 'nt':
            signal.signal(signal.SIGQUIT, self.shutdown)
            signal.signal(signal.SIGTERM, self.shutdown)
        else:
            # Handle the windows control signal as stated here: https://pyinstaller.org/en/stable/feature-notes.html#signal-handling-in-console-windows-applications-and-onefile-application-cleanup
            # This logic handles the signal sent from the bootloader equivalent to sigterm in
            # addition to the signals sent by windows's taskkill.
            # Research documented in https://github.com/yabirgb/rotki-python-research
            import win32api  # pylint: disable=import-outside-toplevel  # isort:skip
            win32api.SetConsoleCtrlHandler(self.shutdown, True)

        signal.signal(signal.SIGINT, self.shutdown)
        # The api server's RestAPI starts rotki main loop
        self.api_server.start(
            host=self.args.api_host,
            rest_port=self.args.rest_api_port,
        )
        self.stop_event.wait()
        # Exit without running interpreter shutdown. All rotki task threads are
        # daemons, but the WSGI bridge's executor threads are not and the
        # interpreter joins non-daemon threads at exit -- a single request handler
        # wedged in a remote call would keep the process alive (appearing to
        # ignore SIGTERM) indefinitely. State is already persisted and logging
        # flushed by rest_api.stop() before stop_event is set.
        os._exit(0)
