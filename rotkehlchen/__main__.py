import logging

from gevent import monkey

monkey.patch_all()
logger = logging.getLogger(__name__)


def main():
    import traceback
    import sys
    from rotkehlchen.server import RotkehlchenServer
    try:
        rotkehlchen_server = RotkehlchenServer()
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
    except: # noqa
        tb = traceback.format_exc()
        logging.critical(tb)
        print("Failed to start rotkehlchen backend:\n{}".format(tb))
        sys.exit(1)

    rotkehlchen_server.main()


if __name__ == '__main__':
    main()
