# make it possible to run rotkelchen with 'python -m rotkelchen'


def main():
    import traceback
    import sys
    from rotkelchen.server import RotkelchenServer
    try:
        rotkelchen_server = RotkelchenServer()
    except:
        tb = traceback.format_exc()
        # open a file and dump the stack trace
        with open("error.log", "w") as f:
            f.write(tb)
        print("Failed to start rotkelchen backend:\n{}".format(tb))
        sys.exit(1)

    rotkelchen_server.main()


if __name__ == '__main__':
    main()
