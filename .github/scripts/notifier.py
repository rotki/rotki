#!/usr/bin/env python3

import argparse
import logging
import sys
from http import HTTPStatus
from pathlib import Path

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
    parser.add_argument(
        '--message-file',
        help='Optional file with extra notification details',
    )
    parser.add_argument(
        '--message-title',
        help='Optional notification title override',
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

    if args.message_file is not None:
        details = Path(args.message_file).read_text(encoding='utf8').strip()

        title = args.message_title or f'{job_type} need attention'
        # Discord messages are capped at 2000 characters. Leave room for the mention,
        # title and run URL so the notification is sent as a single message.
        if len(details) > 1500:
            details = f'{details[:1500]}\n\n...truncated...'

        msg = (
            f'{emoji} **Github Actions:** {title} :warning: \r\n\r\n '
            f'<@&{group}> please have a look at '
            f'[{run_id}](https://github.com/rotki/rotki/actions/runs/{run_id}).\r\n\r\n'
            f'{details}'
        )
    else:
        msg = (
            f'{emoji} **Github Actions:** {job_type} failed :x: \r\n\r\n '
            f'<@&{group}> please have a look at '
            f'[{run_id}](https://github.com/rotki/rotki/actions/runs/{run_id}) :cry:'
        )
    data = {
        'content': msg,
    }

    response = requests.post(url=url, data=data, timeout=30)
    if response.status_code not in {HTTPStatus.OK, HTTPStatus.NO_CONTENT}:
        logger.error(
            f'Failed to notify {group_key} group for {job_type} job. '
            f'Status code: {response.status_code}',
        )
        sys.exit(1)

    logger.info(f'Successfully notified {group_key} group for {job_type} job')


if __name__ == '__main__':
    main()
