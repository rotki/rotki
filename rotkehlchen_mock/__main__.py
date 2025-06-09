from gevent import monkey

monkey.patch_all()  # isort:skip

import logging
from http import HTTPStatus
from typing import Any

from rotkehlchen.utils.gevent_compat import Event
from flask import Response

from rotkehlchen.api.rest import RestAPI, api_response
from rotkehlchen.api.server import APIServer
from rotkehlchen.args import app_args
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.server import RotkehlchenServer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
add_logging_level('TRACE', TRACE)


def get_well_formed_response(*_: Any) -> Response:
    """
    Gets a valid OK api response.

    Arguments passed to this function are ignored.
    """
    return api_response(result={'result': {}}, status_code=HTTPStatus.OK)


class RotkehlchenServerMock(RotkehlchenServer):
    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        # mock entry point inherits all the cmd args of normal entry point
        arg_parser = app_args(prog='rotkehlchen_mock', description='mocked rotki server')

        # you can add additional cmd args
        args = arg_parser.parse_args()

        configure_logging(args)

        rotkehlchen = Rotkehlchen(args)
        rest_api = RestAPI(rotkehlchen)
        if ',' in args.api_cors:
            domain_list = [str(domain) for domain in args.api_cors.split(',')]
        else:
            domain_list = [str(args.api_cors)]

        self.args = args
        self.rotkehlchen = rotkehlchen
        self.stop_event = Event()

        self.api_server = APIServer(
            rest_api=rest_api,
            ws_notifier=self.rotkehlchen.rotki_notifier,
            cors_domain_list=domain_list,
        )

        # patch all methods except special ones and those managing state of the app
        functions_to_patch = (
            member_name
            for member_name in dir(rest_api)
            if callable(getattr(rest_api, member_name)) and
            not member_name.startswith('__') and
            member_name != 'stop'
        )

        for function_name in functions_to_patch:
            setattr(rest_api, function_name, get_well_formed_response)


if __name__ == '__main__':
    RotkehlchenServerMock().main()
