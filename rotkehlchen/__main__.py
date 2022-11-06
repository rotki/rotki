from gevent import monkey  # isort:skip
monkey.patch_all()  # isort:skip
import logging
import sys
import traceback

from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.server import RotkehlchenServer

# monkey patch web3's non-thread safe lru cache with our own version
from rotkehlchen.chain.ethereum import patch_web3  # isort:skip # pylint: disable=unused-import # lgtm[py/unused-import] # noqa

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def main() -> None:
    try:
        rotkehlchen_server = RotkehlchenServer()
    except SystemPermissionError as e:
        print(f'ERROR at initialization: {str(e)}')
        sys.exit(1)
    except SystemExit as e:
        if e.code is None or e.code == 0 or e.code == 2:
            # exit_code 2 is for invalid arguments
            exit_code = 0 if e.code is None else e.code
            sys.exit(exit_code)
        else:
            tb = traceback.format_exc()
            logging.critical(tb)
            print("Failed to start rotkehlchen backend:\n{}".format(tb))
            sys.exit(1)
    except: # noqa  # pylint: disable=bare-except
        tb = traceback.format_exc()
        logging.critical(tb)
        print("Failed to start rotkehlchen backend:\n{}".format(tb))
        sys.exit(1)

    rotkehlchen_server.main()


if __name__ == '__main__':
    main()
