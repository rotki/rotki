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
        help='The name for the new (or existing) user',
    )
    p.add_argument(
        '--user-password',
        help='The password for the new (or existing) user',
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
    p.add_argument(
        '--command',
        type=str,
        choices=['mockall', 'statistics'],
        help='The type of operation data faken should do',
    )
    p.add_argument(
        '--from-timestamp',
        type=int,
        required=False,
        help='The time from which to create the fake statistics data generation',
    )
    p.add_argument(
        '--to-timestamp',
        type=int,
        required=False,
        help='The time until which to create the fake statistics data generation',
    )
    p.add_argument(
        '--assets',
        type=str,
        required=False,
        help='List of assets to generate for fake statistics',
    )
    p.add_argument(
        '--locations',
        type=str,
        required=False,
        help='List of locations to use for fake statistics',
    )
    p.add_argument(
        '--starting-amount',
        type=int,
        required=False,
        default=10000,
        help='The starting amount of net value in USD',
    )
    p.add_argument(
        '--max-amount',
        type=int,
        required=False,
        default=100000,
        help='The max amount of net value in USD to be able to get to',
    )
    p.add_argument(
        '--min-amount',
        type=int,
        required=False,
        default=1000,
        help='The min amount of net value in USD to be able to get to',
    )
    p.add_argument(
        '--go-up-probability',
        type=str,
        required=False,
        default='0.5',
        help='Number between 0 and 1.0 indicating probability that at each step number will go up',
    )
    return p
