from gevent import monkey
monkey.patch_all()
import logging
logger = logging.getLogger(__name__)


def main():
    import traceback
    import sys
    from rotkelchen.server import RotkelchenServer
    try:
        rotkelchen_server = RotkelchenServer()
    except:
        tb = traceback.format_exc()
        logging.critical(tb)
        print("Failed to start rotkelchen backend:\n{}".format(tb))
        sys.exit(1)

    rotkelchen_server.main()


if __name__ == '__main__':
    main()
