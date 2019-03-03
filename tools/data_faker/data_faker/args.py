import argparse

from rotkehlchen.args import app_args


def data_faker_args() -> argparse.ArgumentParser:
    """Append to the Rotkehlchen argument parser and return it"""
    p = app_args(
        prog='data_faker',
        description='Rotkehlchen fake data generation tool',
    )
    p.add_argument(
        '--user-name',
        help='The name for the new user',
    )
    p.add_argument(
        '--user-password',
        help='The password for the new user',
        required=True,
    )
    p.add_argument(
        '--trades-number',
        type=int,
        help='The number of trades to automatically generate',
        default=100,
    )
    p.add_argument(
        '--seconds-between-trades',
        type=int,
        help='The min number of seconds between each trade. Default 1 day',
        default=86400,
    )
    p.add_argument(
        '--seconds-between-balance-save',
        type=int,
        help='The min number of seconds between each balance save. Default 1 day',
        default=86400,
    )

    return p
