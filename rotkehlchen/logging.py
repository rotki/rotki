import logging
import random
import string

from rotkehlchen.fval import FVal
from rotkehlchen.utils import ts_now

ANONYMIZABLE_BIG_VALUES = (
    'amount',
    'amount_lent',
    'cost',
    'earned',
    'price',
    'profit_loss',
    'usd_value',
    'net_profit_or_loss',
    'paid_in_profit_currency',
    'paid_in_asset',
    'received_in_asset'
    'received_in_profit_currency',
    'taxable_amount',
    'taxable_bought_cost',
    'wei_amount',
)
ANONYMIZABLE_SMALL_VALUES = ('fee', 'rate')
ANONYMIZABLE_TIME_VALUES = ('time', 'timestamp', 'open_time', 'close_time')
ANONYMIZABLE_ETH_ADDRESSES = ('eth_address', 'eth_account')
ANONYMIZABLE_MULTIETH_ADDRESSES = ('eth_addresses', 'eth_accounts')


def random_eth_address():
    b = bytes(''.join(random.choice(string.printable) for _ in range(20)), encoding='utf-8')
    return '0x' + b.hex()


def make_sensitive(data):
    return dict(data, **{'sensitive_log': True})


class LoggingSettings(object):
    __instance = None

    def __new__(cls, anonymized_logs=False):
        if LoggingSettings.__instance is None:
            LoggingSettings.__instance = object.__new__(cls)

        LoggingSettings.__instance.anonymized_logs = anonymized_logs
        return LoggingSettings.__instance

    def get():
        if LoggingSettings.__instance is None:
            LoggingSettings.__instance = LoggingSettings()

        return LoggingSettings.__instance


class RotkehlchenLogsAdapter(logging.LoggerAdapter):

    def __init__(self, logger):
        return super().__init__(logger, extra={})

    def process(self, msg, kwargs):
        """
        This is the main post-processing function for Rotkehlchen logs

        It checks if the magive keyword argument 'sensitive_log' is in the kwargs
        and if it is marks the log entry as sensitive. If it is sensitive the values
        of the kwargs are anonymized via the pre-specified rules

        This function also appends all kwargs to the final message.
        """
        settings = LoggingSettings.get()

        is_sensitive = False
        if 'sensitive_log' in kwargs:
            del kwargs['sensitive_log']
            is_sensitive = True

        if is_sensitive and settings.anonymized_logs:
            new_kwargs = {}
            for key, val in kwargs.items():
                if key in ANONYMIZABLE_BIG_VALUES:
                    new_kwargs[key] = FVal(round(random.uniform(0, 10000), 3))
                elif key in ANONYMIZABLE_SMALL_VALUES:
                    new_kwargs[key] = FVal(round(random.uniform(0, 5), 3))
                elif key in ANONYMIZABLE_TIME_VALUES:
                    new_kwargs[key] = random.randrange(1451606400, ts_now())
                elif key in ANONYMIZABLE_ETH_ADDRESSES:
                    new_kwargs[key] = random_eth_address()
                elif key in ANONYMIZABLE_MULTIETH_ADDRESSES:
                    assert isinstance(val, list), (
                        f'During anonymizing value for {key} was not a list'
                    )
                    new_kwargs[key] = [random_eth_address()] * len(val)
                else:
                    new_kwargs[key] = val
        else:
            new_kwargs = kwargs

        msg = msg + ','.join(' {}={}'.format(a[0], a[1]) for a in new_kwargs.items())
        return msg, {}
