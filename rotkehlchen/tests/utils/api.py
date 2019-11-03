import os

import gevent
import psutil
from flask import url_for

from rotkehlchen.api.server import APIServer, RestAPI
from rotkehlchen.rotkehlchen import Rotkehlchen


def _wait_for_listening_port(
        port_number: int, tries: int = 10, sleep: float = 0.1, pid: int = None,
) -> None:
    if pid is None:
        pid = os.getpid()
    for _ in range(tries):
        gevent.sleep(sleep)
        # macoOS requires root access for the connections api to work
        # so get connections of the current process only
        connections = psutil.Process(pid).connections()
        for conn in connections:
            if conn.status == "LISTEN" and conn.laddr[1] == port_number:
                return

    raise RuntimeError(f"{port_number} is not bound")


def create_api_server(rotki: Rotkehlchen, port_number: int) -> APIServer:
    api_server = APIServer(RestAPI(rotkehlchen=rotki))

    api_server.flask_app.config["SERVER_NAME"] = f"localhost:{port_number}"
    api_server.start(host='127.0.0.1', port=port_number)

    # Fixes flaky test, were requests are done prior to the server initializing
    # the listening socket.
    # https://github.com/raiden-network/raiden/issues/389#issuecomment-305551563
    _wait_for_listening_port(port_number)

    return api_server


def api_url_for(api_server: APIServer, endpoint: str, **kwargs) -> str:
    # url_for() expects binary address so we have to convert here
    # for key, val in kwargs.items():
    #     if isinstance(val, str) and val.startswith("0x"):
    #         kwargs[key] = to_canonical_address(val)
    with api_server.flask_app.app_context():
        return url_for(f"v1_resources.{endpoint}", **kwargs)
