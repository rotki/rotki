import logging
import os
import signal

import gevent

from rotkehlchen.api.server import APIServer, RestAPI
from rotkehlchen.args import app_args
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkehlchenServer():
    def __init__(self) -> None:
        arg_parser = app_args(
            prog='rotkehlchen',
            description='Rotkehlchen Crypto Portfolio Management',
        )
        self.args = arg_parser.parse_args()
        self.rotkehlchen = Rotkehlchen(self.args)
        self.stop_event = gevent.event.Event()
        self.api_server = APIServer(RestAPI(rotkehlchen=self.rotkehlchen))

    def shutdown(self) -> None:
        log.debug('Shutdown initiated')
        self.api_server.stop()
        self.stop_event.set()

    def main(self) -> None:
        if os.name != 'nt':
            gevent.hub.signal(signal.SIGQUIT, self.shutdown)
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        self.api_server.start(host=self.args.api_host, port=self.args.api_port)
        self.stop_event.wait()
