import logging
import os
import signal

import gevent

from rotkehlchen.api.server import APIServer, RestAPI
from rotkehlchen.args import app_args
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkehlchenServer():
    def __init__(self) -> None:
        """Initializes the backend server
        May raise:
        - SystemPermissionError due to the given args containing a datadir
        that does not have the correct permissions
        """
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
        self.stop_event = gevent.event.Event()
        domain_list = []
        if self.args.api_cors:
            if ',' in self.args.api_cors:
                for domain in self.args.api_cors.split(','):
                    domain_list.append(str(domain))
            else:
                domain_list.append(str(self.args.api_cors))
        self.api_server = APIServer(
            rest_api=RestAPI(rotkehlchen=self.rotkehlchen),
            ws_notifier=self.rotkehlchen.rotki_notifier,
            cors_domain_list=domain_list,
        )

    def shutdown(self) -> None:
        log.debug('Shutdown initiated')
        self.api_server.stop()
        self.stop_event.set()

    def main(self) -> None:
        # disable printing hub exceptions in stderr. With using the hub to do various
        # tasks that should raise exceptions and have them handled outside the hub
        # printing them in stdout is now too much spam (and would worry users too)
        hub = gevent.hub.get_hub()
        hub.exception_stream = None
        # we don't use threadpool much so go to 2 instead of default 10
        hub.threadpool_size = 2
        hub.threadpool.maxsize = 2
        if os.name != 'nt':
            gevent.hub.signal(signal.SIGQUIT, self.shutdown)
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        # The api server's RestAPI starts rotki main loop
        self.api_server.start(
            host=self.args.api_host,
            rest_port=self.args.rest_api_port,
        )
        self.stop_event.wait()
