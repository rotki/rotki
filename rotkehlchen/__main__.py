import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == 'mcp':
        from rotkehlchen.mcp.__main__ import main as mcp_main

        mcp_main(sys.argv[2:])
        return

    from gevent import monkey  # isort:skip
    monkey.patch_all()  # isort:skip

    import logging
    import traceback

    from rotkehlchen.errors.misc import DBSchemaError, SystemPermissionError
    from rotkehlchen.logging import RotkehlchenLogsAdapter
    from rotkehlchen.server import RotkehlchenServer

    log = RotkehlchenLogsAdapter(logging.getLogger(__name__))

    try:
        rotkehlchen_server = RotkehlchenServer()
    except (SystemPermissionError, DBSchemaError) as e:
        print(f'ERROR at initialization: {e!s}', file=sys.stderr)
        sys.exit(1)
    except SystemExit as e:
        if e.code is None or e.code in (0, 2):
            # exit_code 2 is for invalid arguments
            exit_code = 0 if e.code is None else e.code
            sys.exit(exit_code)
        else:
            tb = traceback.format_exc()
            log.critical(tb)
            # Only show clean error message to frontend, full traceback is in logs
            print(f'Failed to start rotki backend: {e!s}', file=sys.stderr)
            sys.exit(1)
    except BaseException as e:
        tb = traceback.format_exc()
        log.critical(tb)
        # Only show clean error message to frontend, full traceback is in logs
        print(f'Failed to start rotki backend: {e!s}', file=sys.stderr)
        sys.exit(1)

    rotkehlchen_server.main()


if __name__ == '__main__':
    main()
