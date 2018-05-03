from gevent import monkey
monkey.patch_all()
import logging
logger = logging.getLogger(__name__)


def main():
    import traceback
    import sys
    from rotkehlchen.server import RotkehlchenServer
    try:
        rotkehlchen_server = RotkehlchenServer()
    except SystemExit as e:
        if e.code is None or e.code == 0:
            sys.exit(0)
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
