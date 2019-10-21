#!/usr/bin/env python
import argparse
import sys
from typing import Any, List, Sequence, Union

from rotkehlchen.config import default_data_directory
from rotkehlchen.utils.misc import get_system_spec


class CommandAction(argparse.Action):
    """Interprets the positional argument as a command if that command exists"""
    def __init__(  # pylint: disable=unused-argument
            self,
            option_strings: List[str],
            dest: str,
            **kwargs: Any,
    ) -> None:
        super().__init__(option_strings, dest)

    def __call__(
            self,
            parser: argparse.ArgumentParser,
            namespace: argparse.Namespace,
            values: Union[str, Sequence[Any], None],
            option_string: str = None,
    ) -> None:
        # Only command we have at the moment is version
        if values != 'version':
            parser.print_usage()
            print(f'Unrecognized command: {values}.')
            sys.exit(0)

        print(get_system_spec()['rotkehlchen'])
        sys.exit(0)


def app_args(prog: str, description: str) -> argparse.ArgumentParser:
    """Add the Rotkehlchen arguments to the argument parser and return it"""
    p = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )

    p.add_argument(
        '--sleep-secs',
        type=int,
        default=20,
        help="Seconds to sleep during the main loop",
    )
    p.add_argument(
        '--data-dir',
        help='The directory where all data and configs are placed',
        default=default_data_directory(),
    )
    p.add_argument(
        '--api-host',
        help='The host on which the rest API will run',
        default='127.0.0.1',
    )
    p.add_argument(
        '--api-port',
        help='The port on which the rest API will run',
        default=5042,
    )
    p.add_argument(
        '--ethrpc-port',
        help="The port on which to communicate with an ethereum client's RPC.",
        default=8545,
    )
    p.add_argument(
        '--logfile',
        help='The name of the file to write log entries to',
        default='rotkehlchen.log',
    )
    p.add_argument(
        '--logtarget',
        help='Choose where logging entries will be sent. Valid values are "file and "stdout"',
        choices=['stdout', 'file'],
        default='file',
    )
    p.add_argument(
        '--loglevel',
        help='Choose the logging level',
        choices=['debug', 'info', 'warn', 'error', 'critical'],
        default='debug',
    )
    p.add_argument(
        '--logfromothermodules',
        help=(
            'If given then logs from all imported modules that use the '
            'logging system will also be visible.'
        ),
        action='store_true',
    )
    p.add_argument(
        'version',
        help='Shows the rotkehlchen version',
        action=CommandAction,
    )

    return p
