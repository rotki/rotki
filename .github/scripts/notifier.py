#!/usr/bin/env python3

import argparse
from http import HTTPStatus

import requests

ALL_DEVS = '735068019440615516'
BACKEND_DEVS = '983289520000737330'


def main() -> None:
    parser = argparse.ArgumentParser(description='job failure notifier')
    parser.add_argument(
        '--webhook',
        required=True,
        help='Webhook that will be called for notification',
    )
    parser.add_argument(
        '--run-id',
        required=True,
        help='Github run ID',
    )
    parser.add_argument(
        '--test',
        action='store_true',
        default=False,
    )
    args = parser.parse_args()
    url = args.webhook
    run_id = args.run_id

    if args.test:
        group = BACKEND_DEVS
        emoji = ':test_tube:'
        job_type = 'tests'
    else:
        group = ALL_DEVS
        emoji = ':construction_site:'
        job_type = 'builds'

    msg = (
        f'{emoji} **Github Actions:** {job_type} failed :x: \r\n\r\n '
        f'<@&{group}> please have a look at '
        f'[{run_id}](https://github.com/rotki/rotki/actions/runs/{run_id}) :cry:'
    )
    data = {
        'content': msg,
    }

    response = requests.post(url=url, data=data)
    if response.status_code != HTTPStatus.OK:
        exit(1)


if __name__ == '__main__':
    main()
