import argparse
import shutil
import sys
from http import HTTPStatus
from pathlib import Path

import requests

from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.globaldb.handler import GlobalDBHandler
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
    start_db = p.add_mutually_exclusive_group(required=True)
    start_db.add_argument(
        '--start-db-version',
        type=int,
        help='The starting DB version',
    )
    start_db.add_argument(
        '--start-db-hash',
        type=str,
        help='The starting DB commit hash',
    )
    start_db.add_argument(
        '--start-db-path',
        type=str,
        help='The starting DB path',
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
    p.add_argument(
        '--update-mode',
        type=str,
        choices=['assets', 'remote', 'all'],
        default='all',
        help='The update mode to use. "assets" will apply only the assets updates, "remote" will apply only remote data updates, "all" will apply both.',  # noqa: E501
    )
    return p.parse_args()


def get_remote_global_db(
        directory: Path,
        branch: str,
        version: str | None = None,
        commit_hash: str | None = None,
        path: str | None = None,
) -> Path:
    dbpath = directory / GLOBALDB_NAME
    if path is not None:
        shutil.copyfile(path, dbpath)
        return dbpath

    if version is not None:
        url = f'https://github.com/rotki/assets/raw/{branch}/databases/v{version}_global.db'
    else:
        url = f'https://github.com/rotki/rotki/raw/{commit_hash}/rotkehlchen/data/global.db'

    try:
        response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException:
        print(f'Couldnt download v{version} global.db from github')
        sys.exit(1)

    if response.status_code != HTTPStatus.OK:
        print(f'Couldnt download v{version} global.db from github, got {response.status_code} status code')  # noqa: E501
        sys.exit(1)

    total_bytes, chunk_size = 0, 4096
    print(f'Downloading v{version} globaldb from the remote...')
    with open(dbpath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                total_bytes += chunk_size
                print(f'Downloaded {total_bytes * 1025} KB...')
                f.write(chunk)
    print('Download complete!')

    return dbpath


def prepare_globaldb(args: argparse.Namespace) -> tuple[GlobalDBHandler, Path]:
    """Prepare the globaldb and target directory for the updates"""
    target_directory = Path.cwd() if args.target_directory is None else args.target_directory
    target_directory = Path(target_directory)
    if not target_directory.is_dir():
        print(f'Given directory {target_directory} not a valid directory')
        sys.exit(1)

    # The way global db works it needs to be under a directory called 'global'
    target_global_dir = target_directory / GLOBALDIR_NAME
    target_global_dir.mkdir(parents=True, exist_ok=True)
    get_remote_global_db(
        directory=target_directory / GLOBALDIR_NAME,
        version=args.start_db_version,
        commit_hash=args.start_db_hash,
        path=args.start_db_path,
        branch=args.assets_branch,
    )
    return GlobalDBHandler(
        data_dir=target_directory,
        sql_vm_instructions_cb=0,
        msg_aggregator=MessagesAggregator(),
        perform_assets_updates=False,
    ), target_directory


def clean_folder(globaldb: GlobalDBHandler, target_directory: Path):
    """Set journal_mode=DELETE in the global db. Move it out of the temporary directory to the
    final location, and clean up the temporary directory."""
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('PRAGMA journal_mode=DELETE')

    print('Cleaning up...')
    (target_directory / GLOBALDIR_NAME / GLOBALDB_NAME).rename(target_directory / GLOBALDB_NAME)
    shutil.rmtree(target_directory / GLOBALDIR_NAME)
    print('Done!')
