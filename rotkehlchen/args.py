import argparse
import sys
from collections.abc import Sequence
from typing import Any

from rotkehlchen.constants.misc import (
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
)
from rotkehlchen.utils.misc import get_system_spec


class CommandAction(argparse.Action):
    """Interprets the positional argument as a command if that command exists"""
    def __init__(  # pylint: disable=unused-argument
            self,
            option_strings: list[str],
            dest: str,
            **kwargs: Any,
    ) -> None:
        super().__init__(option_strings, dest)

    def __call__(
            self,
            parser: argparse.ArgumentParser,
            namespace: argparse.Namespace,
            values: str | (Sequence[Any] | None),
            option_string: str | None = None,
    ) -> None:
        # Only command we have at the moment is version
        if values != 'version':
            parser.print_usage()
            print(f'Unrecognized command: {values}.')
            sys.exit(0)

        print(get_system_spec()['rotkehlchen'])
        sys.exit(0)


def _positive_int_or_zero(value: str) -> int:
    """Force positive int or zero https://docs.python.org/3/library/argparse.html#type"""
    int_val = int(value)  # ValueError is caught and shown to user
    if int_val < 0:
        raise ValueError('Int value should be positive or zero')

    return int_val


def app_args(prog: str, description: str) -> argparse.ArgumentParser:
    """Add the rotki arguments to the argument parser and return it"""
    p = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )

    p.add_argument(
        '--data-dir',
        help='The directory where all data and configs are placed',
        type=str,
        default=None,
    )
    p.add_argument(
        '--api-host',
        help='The host on which the rest API will run',
        default='127.0.0.1',
    )
    p.add_argument(
        '--rest-api-port',
        help='The port on which the rest API will run',
        type=int,
        default=5042,
    )
    p.add_argument(
        '--db-api-port',
        help='The port on which the db writer process will listen',
        type=int,
        default=5555,
    )
    p.add_argument(
        '--websockets-api-port',
        help='The port on which the websockets API will run',
        type=int,
        default=5043,
    )
    p.add_argument(
        '--api-cors',
        help='Comma separated list of domains for the API to accept cross origin requests.',
        default='http://localhost:*/*',
        type=str,
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
        choices=['trace', 'debug', 'info', 'warning', 'error', 'critical'],
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
        '--max-size-in-mb-all-logs',
        help='This is the maximum size in megabytes that will be used for all rotki logs',
        default=DEFAULT_MAX_LOG_SIZE_IN_MB,
        type=int,
    )
    p.add_argument(
        '--max-logfiles-num',
        help='This is the maximum number of logfiles to keep',
        default=DEFAULT_MAX_LOG_BACKUP_FILES,
        type=int,
    )
    p.add_argument(
        '--sqlite-instructions',
        help='Instructions per sqlite context switch. Should be a positive integer or zero to disable.',  # noqa: E501
        default=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        type=_positive_int_or_zero,
    )
    p.add_argument(
        'version',
        help='Shows the rotki version',
        action=CommandAction,
    )
    p.add_argument(
        '--disable-task-manager',
        help="If given then task manager won't schedule new tasks",
        action='store_true',
    )
    p.add_argument(
        '--process',
        help='Choose the process to run',
        choices=['all', 'api_server', 'db_writer', 'bg_worker'],
        default='all',
    )
    return p
