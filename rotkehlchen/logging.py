import argparse
import logging
import re
from typing import Any, Dict, MutableMapping, Tuple

PYWSGI_RE = re.compile(r'\[(.*)\] ')


class RotkehlchenLogsAdapter(logging.LoggerAdapter):

    def __init__(self, logger: logging.Logger):
        super().__init__(logger, extra={})

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> Tuple[str, Dict]:
        """
        This is the main post-processing function for rotki logs

        This function also appends all kwargs to the final message.
        """
        msg = msg + ','.join(' {}={}'.format(a[0], a[1]) for a in kwargs.items())
        return msg, {}


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
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
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

    if args.logtarget == 'file':
        selected_handlers = ['file']
        handlers['file'] = {
            'class': 'logging.FileHandler',
            'filename': args.logfile,
            'mode': 'w',
            'level': loglevel,
            'formatter': 'default',
        }
    else:
        selected_handlers = ['console']

    filters = {
        'pywsgi': {
            '()': PywsgiFilter,
        },
    }
    loggers = {
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
