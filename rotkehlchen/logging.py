import argparse
import logging
import random
import re
import string
import time
from typing import Any, Dict, MutableMapping, Tuple

from rotkehlchen.fval import FVal
from rotkehlchen.typing import EthAddress

PYWSGI_RE = re.compile(r'\[(.*)\] ')

ANONYMIZABLE_BIGINT_VALUES = ('tx_value', 'gas_price', 'gas', 'gas_used')
ANONYMIZABLE_BIG_VALUES = (
    'amount',
    'amount_lent',
    'bought_amount',
    'cost',
    'cost_in_profit_currency',
    'earned',
    'fee_in_profit_currency',
    'gain_in_profit_currency',
    'gain_loss_in_profit_currency',
    'gained_amount',
    'general_profit_loss',
    'lent_amount',
    'price',
    'profit_loss',
    'usd_value',
    'net_profit_or_loss',
    'net_gain_loss_amount',
    'paid_in_profit_currency',
    'paid_in_asset',
    'rate_in_profit_currency',
    'received_in_asset'
    'received_in_profit_currency',
    'receiving_amount',
    'remaining_sold_amount',
    'settlement_loss',
    'selling_amount',
    'taxable_amount',
    'taxable_bought_cost',
    'taxable_profit_loss',
    'used_amount',
    'wei_amount',
)
ANONYMIZABLE_SMALL_VALUES = ('fee', 'rate', 'trade_buy_rate')
ANONYMIZABLE_TIME_VALUES = ('time', 'trade_timestamp', 'timestamp', 'open_time', 'close_time')
ANONYMIZABLE_ETH_ADDRESSES = ('eth_address', 'eth_account', 'from_eth_address', 'to_eth_address')
ANONYMIZABLE_MULTIETH_ADDRESSES = ('eth_addresses', 'eth_accounts')
ANONYMIZABLE_ETH_TXHASH = ('eth_tx_hash')

DEFAULT_ANONYMIZED_LOGS = False


def random_eth_address() -> EthAddress:
    b = bytes(''.join(random.choice(string.printable) for _ in range(20)), encoding='utf-8')
    return EthAddress('0x' + b.hex())


def random_hash() -> str:
    b = bytes(''.join(random.choice(string.printable) for _ in range(32)), encoding='utf-8')
    return '0x' + b.hex()


def make_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    return dict(data, **{'sensitive_log': True})


class LoggingSettings():
    __instance = None

    def __new__(cls, anonymized_logs: bool = DEFAULT_ANONYMIZED_LOGS) -> 'LoggingSettings':
        if LoggingSettings.__instance is None:
            LoggingSettings.__instance = object.__new__(cls)

        LoggingSettings.__instance.anonymized_logs = anonymized_logs
        return LoggingSettings.__instance

    @staticmethod
    def get() -> 'LoggingSettings':
        if LoggingSettings.__instance is None:
            LoggingSettings.__instance = LoggingSettings()

        return LoggingSettings.__instance


class RotkehlchenLogsAdapter(logging.LoggerAdapter):

    def __init__(self, logger: logging.Logger):
        super().__init__(logger, extra={})

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> Tuple[str, Dict]:
        """
        This is the main post-processing function for Rotki logs

        It checks if the magic keyword argument 'sensitive_log' is in the kwargs
        and if it is marks the log entry as sensitive. If it is sensitive, the values
        of the kwargs are anonymized via the pre-specified rules

        This function also appends all kwargs to the final message.
        """
        settings = LoggingSettings.get()

        is_sensitive = False
        if 'sensitive_log' in kwargs:
            del kwargs['sensitive_log']
            is_sensitive = True

        if is_sensitive and settings.anonymized_logs:  # type: ignore
            new_kwargs: MutableMapping[str, Any] = {}
            for key, val in kwargs.items():
                if key in ANONYMIZABLE_BIG_VALUES:
                    new_kwargs[key] = FVal(round(random.uniform(0, 10000), 3))
                elif key in ANONYMIZABLE_SMALL_VALUES:
                    new_kwargs[key] = FVal(round(random.uniform(0, 5), 3))
                elif key in ANONYMIZABLE_BIGINT_VALUES:
                    new_kwargs[key] = FVal(random.randint(0, 100000000))
                elif key in ANONYMIZABLE_TIME_VALUES:
                    new_kwargs[key] = random.randrange(1451606400, int(time.time()))
                elif key in ANONYMIZABLE_ETH_ADDRESSES:
                    new_kwargs[key] = random_eth_address()
                elif key in ANONYMIZABLE_MULTIETH_ADDRESSES:
                    assert isinstance(val, list), (
                        f'During anonymizing value for {key} was not a list'
                    )
                    new_kwargs[key] = [random_eth_address()] * len(val)
                elif key in ANONYMIZABLE_ETH_TXHASH:
                    new_kwargs[key] = random_hash()
                else:
                    new_kwargs[key] = val
        else:
            new_kwargs = kwargs

        msg = msg + ','.join(' {}={}'.format(a[0], a[1]) for a in new_kwargs.items())
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
