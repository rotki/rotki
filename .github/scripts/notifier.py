#!/usr/bin/env python3

import argparse
import logging
import sys
from http import HTTPStatus

import requests

ALL_DEVS = '1105142033590526052'
BACKEND_DEVS = '983289520000737330'

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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
        group_key = 'backend devs'
        emoji = ':test_tube:'
        job_type = 'tests'
    else:
        group = ALL_DEVS
        group_key = 'all devs'
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

    response = requests.post(url=url, data=data, timeout=30)
    if response.status_code != HTTPStatus.OK and response.status_code != HTTPStatus.NO_CONTENT:
        logger.error(
            f'Failed to notify {group_key} group for {job_type} job. '
            f'Status code: {response.status_code}',
        )
        sys.exit(1)

    logger.info(f'Successfully notified {group_key} group for {job_type} job')


if __name__ == '__main__':
    main()
