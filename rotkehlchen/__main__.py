from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa
import logging

from rotkehlchen.errors import SystemPermissionError

logger = logging.getLogger(__name__)


def main() -> None:
    import traceback
    import sys
    from rotkehlchen.server import RotkehlchenServer
    try:
        rotkehlchen_server = RotkehlchenServer()
    except SystemPermissionError as e:
        print(f'ERROR at initialization: {str(e)}')
        sys.exit(1)
    except SystemExit as e:
        # Mypy here thinks e.code is always None which is not correct according to the docs:
        # https://docs.python.org/3/library/exceptions.html#SystemExit
        if e.code is None or e.code == 0 or e.code == 2:  # type: ignore
            # exit_code 2 is for invalid arguments
            exit_code = 0 if e.code is None else e.code  # type: ignore
            sys.exit(exit_code)
        else:
            tb = traceback.format_exc()
            logging.critical(tb)
            print("Failed to start rotkehlchen backend:\n{}".format(tb))
            sys.exit(1)
    except: # noqa
        tb = traceback.format_exc()
        logging.critical(tb)
        print("Failed to start rotkehlchen backend:\n{}".format(tb))
        sys.exit(1)

    rotkehlchen_server.main()


if __name__ == '__main__':
    main()
