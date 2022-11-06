"""Tool to pull an assets database from Github, and apply updates to it"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from gevent import monkey  # isort:skip
monkey.patch_all()  # isort:skip
import requests

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.updates import AssetsUpdater
from rotkehlchen.logging import TRACE, add_logging_level
from rotkehlchen.user_messages import MessagesAggregator

add_logging_level('TRACE', TRACE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog='assets_database_tool',
        description=(
            'A tool to easily create an updated DB version, instead of running '
            'rotki with an old clean DB and pulling upgrades manually'
        ),
    )
    p.add_argument(
        '--start-db',
        type=int,
        help='The starting DB version',
        required=True,
    )
    p.add_argument(
        '--target-version',
        type=int,
        default=None,
        help='The version until which to update',
    )
    p.add_argument(
        '--assets-branch',
        type=str,
        default='develop',
        help='The branch to pull the asset DB from',
    )
    p.add_argument(
        '--target-directory',
        type=str,
        help='The directory to write the file in. Default is current directory',
    )
    return p.parse_args()


def get_remote_global_db(directory: Path, version: int, branch: str) -> Path:
    try:
        url = f'https://github.com/rotki/assets/raw/{branch}/databases/v{version}_global.db'  # noqa: E501
        response = requests.get(url)
    except requests.exceptions.RequestException:
        print(f'Couldnt download v{version} global.db from github')
        sys.exit(1)

    if response.status_code != 200:
        print(f'Couldnt download v{version} global.db from github, got {response.status_code} status code')  # noqa: E501
        sys.exit(1)

    total_bytes = 0
    dbpath = directory / 'global.db'
    chunk_size = 4096
    print(f'Downloading v{version} globaldb from the remote...')
    with open(dbpath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                total_bytes += chunk_size
                print(f'Downloaded {total_bytes * 1025} KB...')
                f.write(chunk)
    print('Download complete!')

    return dbpath


def main() -> None:
    args = parse_args()
    target_directory = os.getcwd() if args.target_directory is None else args.target_directory
    target_directory = Path(target_directory)
    if not target_directory.is_dir():
        print(f'Given directory {target_directory} not a valid directory')
        sys.exit(1)
    # The way global db works it needs to be under a directory called 'global_data'
    target_global_dir = target_directory / 'global_data'
    target_global_dir.mkdir(parents=True, exist_ok=True)
    get_remote_global_db(
        directory=target_global_dir,
        version=args.start_db,
        branch=args.assets_branch,
    )
    print('Applying updates...')
    GlobalDBHandler(data_dir=target_directory, sql_vm_instructions_cb=0)
    assets_updater = AssetsUpdater(msg_aggregator=MessagesAggregator)
    conflicts = assets_updater.perform_update(
        up_to_version=args.target_version,
        conflicts=None,
    )
    if conflicts is not None:
        print('There were conflicts during the update. Bailing.')
        sys.exit(1)

    # Due to the way globaldb initializes we have two of them. Clean up the extra one
    print('Cleaning up...')
    (target_directory / 'global_data' / 'global.db').rename(target_directory / 'global.db')
    shutil.rmtree(target_directory / 'global_data')
    print('Done!')


if __name__ == '__main__':
    main()
