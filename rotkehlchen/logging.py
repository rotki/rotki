import argparse
import logging.config
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, MutableMapping, Optional, Tuple

import gevent

from rotkehlchen.utils.misc import timestamp_to_date, ts_now

PYWSGI_RE = re.compile(r'\[(.*)\] ')

TRACE = logging.DEBUG - 5


def add_logging_level(
        level_name: str,
        level_num: int,
        method_name: Optional[str] = None,
) -> None:
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`. `method_name` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `method_name` is not specified, `level_name.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> add_logging_level('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    taken from: https://stackoverflow.com/a/35804945/110395
    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError('{} already defined in logging module'.format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError('{} already defined in logging module'.format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError('{} already defined in logger class'.format(method_name))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)  # pylint:disable=protected-access

    def log_to_root(message: str, *args: Any, **kwargs: Any) -> None:
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


if TYPE_CHECKING:
    class RotkehlchenLogger(logging.Logger):
        """Just for typing. Have not found another way to do correct type checking
        for custom log level loggers"""

        def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument  # noqa: E501
            ...


class RotkehlchenLogsAdapter(logging.LoggerAdapter):

    def __init__(self, logger: logging.Logger):
        super().__init__(logger, extra={})

    def process(self, given_msg: Any, kwargs: MutableMapping[str, Any]) -> Tuple[str, Dict]:
        """
        This is the main post-processing function for rotki logs

        This function:
        - appends all kwargs to the final message
        - appends the greenlet id in the log message
        """
        msg = str(given_msg)
        greenlet = gevent.getcurrent()
        if greenlet.parent is None:
            greenlet_name = 'Main Greenlet'
        else:
            try:
                greenlet_name = greenlet.name
            except AttributeError:  # means it's a raw greenlet
                greenlet_name = f'Greenlet with id {id(greenlet)}'

        msg = greenlet_name + ': ' + msg + ','.join(' {}={}'.format(a[0], a[1]) for a in kwargs.items())  # noqa: E501
        return msg, {}

    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Delegate a trace call to the underlying logger.
        """
        self.log(TRACE, msg, *args, **kwargs)


class PywsgiFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out the additional timestamp put in by pywsgi

        This is really a hack to fix https://github.com/rotki/rotki/issues/1192

        It seems that the way they do the logging in pywsgi they create the log
        entry completely on their own. So the %message part of the entry contains
        everything and is hence not properly customizale via normal python logging.

        Other options apart from using this filter would be:
        - Ignore it and just have the timestamp two times in the logs
        - Completely disable pywsgi logging and perhaps move it all to the
        rest api.
        """
        record.msg = PYWSGI_RE.sub('', record.msg)
        return True


def configure_logging(args: argparse.Namespace) -> None:
    loglevel = args.loglevel.upper()
    formatters = {
        'default': {
            'format': '[%(asctime)s] %(levelname)s %(name)s %(message)s',
            'datefmt': '%d/%m/%Y %H:%M:%S %Z',
        },
    }
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': loglevel,
            'formatter': 'default',
        },
    }

    if args.max_logfiles_num < 0:
        backups_num = 0
    else:
        backups_num = args.max_logfiles_num - 1

    if args.logtarget == 'file':
        given_filepath = Path(args.logfile)
        filepath = given_filepath
        if not getattr(sys, 'frozen', False):
            # not packaged -- must be in develop mode. Append date to each file
            date = timestamp_to_date(
                ts=ts_now(),
                formatstr='%Y%m%d_%H%M%S',
                treat_as_local=True,
            )
            filepath = given_filepath.parent / f'{date}_{given_filepath.name}'

        selected_handlers = ['file']
        single_log_max_bytes = int(
            (args.max_size_in_mb_all_logs * 1024 * 1000) / args.max_logfiles_num,
        )
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': filepath,
            'mode': 'a',
            'maxBytes': single_log_max_bytes,
            'backupCount': backups_num,
            'level': loglevel,
            'formatter': 'default',
            'encoding': 'utf-8',
        }
    else:
        selected_handlers = ['console']

    filters = {
        'pywsgi': {
            '()': PywsgiFilter,
        },
    }
    loggers: Dict[str, Any] = {
        '': {  # root logger
            'level': loglevel,
            'handlers': selected_handlers,
        },
        'rotkehlchen.api.server.pywsgi': {
            'level': loglevel,
            'handlers': selected_handlers,
            'filters': ['pywsgi'],
            'propagate': False,
        },
    }
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'filters': filters,
        'formatters': formatters,
        'handlers': handlers,
        'loggers': loggers,
    })

    if not args.logfromothermodules:
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
        logging.getLogger('substrateinterface.base').setLevel(logging.CRITICAL)
        logging.getLogger('eth_hash').setLevel(logging.CRITICAL)
