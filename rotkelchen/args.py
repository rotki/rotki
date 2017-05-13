#!/usr/bin/env python
import argparse
from config import default_data_directory


def app_args():
    """ Parse the arguments and create and return the arguments object"""
    p = argparse.ArgumentParser(description='Rotkelchen Crypto Portfolio Management')

    p.add_argument(
        '--output',
        help=(
            'A path to a file for logging all output. If nothing is given'
            'stdout is used'
        )
    )
    p.add_argument(
        '--sleep-secs',
        type=int,
        default=120,
        help="Seconds to sleep during the main loop"
    )
    p.add_argument(
        '--notify',
        action='store_true',
        help=(
            'If given then the tool will send notifications via '
            'notify-send.'
        )
    )
    p.add_argument(
        '--data-dir',
        help='The directory where all data and configs are placed',
        default=default_data_directory()
    )

    p.add_argument(
        '--zerorpc-port',
        help='The port on which to open a zerorpc server for communication with the UI',
        default=4242
    )

    args = p.parse_args()

    return args
