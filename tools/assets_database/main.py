"""Tool to pull an assets database from Github, and apply updates to it"""
import json
from typing import Any

from gevent import monkey

from rotkehlchen.globaldb.updates import AssetsUpdater

monkey.patch_all()  # isort:skip

import argparse
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import requests

from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import TRACE, add_logging_level
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.network import query_file

add_logging_level('TRACE', TRACE)
DATA_UPDATES_URL = 'https://raw.githubusercontent.com/rotki/data/{branch}/updates/{data}/v{version}.json'


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
        url = f'https://github.com/rotki/assets/raw/{branch}/databases/v{version}_global.db'
        response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException:
        print(f'Couldnt download v{version} global.db from github')
        sys.exit(1)

    if response.status_code != 200:
        print(f'Couldnt download v{version} global.db from github, got {response.status_code} status code')  # noqa: E501
        sys.exit(1)

    total_bytes = 0
    dbpath = directory / GLOBALDB_NAME
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


def _retrieve_data_files(
        infojson: dict[str, Any],
) -> dict[int, dict[UpdateType, Any]]:
    """
    Query the assets update repository to retrieve the pending updates before trying to
    apply them. It returns a dict that maps each version to their update files.

    May raise:
    - RemoteError if there is a problem querying github
    """
    updates = {}
    data_files = ['location_asset_mappings']
    # type ignore since due to check_for_updates we know last_remote_checked_version exists
    for key in data_files:
        try:
            latest_version = infojson[key]['latest']
        except KeyError as e:
            print(
                f'Remote info.json for {key} did not contain '
                f'key "{e!s}". Skipping update.',
            )
            continue

        for version in range(1, latest_version + 1):
            data_url = DATA_UPDATES_URL.format(branch='develop', data=key, version=latest_version)
            data_file = query_file(url=data_url, is_json=True)
            updates[version] = {
                UpdateType.LOCATION_ASSET_MAPPINGS: data_file,
            }

    return updates


def get_remote_info_json() -> dict[str, Any]:
    """Retrieve remote file with information for different updates

    May raise RemoteError if anything is wrong contacting github
    """
    url = 'https://raw.githubusercontent.com/rotki/data/develop/updates/info.json'
    try:
        response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Failed to query {url} during assets update: {e!s}') from e

    try:
        json_data = response.json()
    except json.decoder.JSONDecodeError as e:
        raise RemoteError(
            f'Could not parse update info from {url} as json: {response.text}',
        ) from e

    return json_data


def main() -> None:
    args = parse_args()
    target_directory = Path.cwd() if args.target_directory is None else args.target_directory
    target_directory = Path(target_directory)
    if not target_directory.is_dir():
        print(f'Given directory {target_directory} not a valid directory')
        sys.exit(1)
    # The way global db works it needs to be under a directory called 'global'
    target_global_dir = target_directory / GLOBALDIR_NAME
    target_global_dir.mkdir(parents=True, exist_ok=True)
    get_remote_global_db(
        directory=target_global_dir,
        version=args.start_db,
        branch=args.assets_branch,
    )
    print('Applying updates...')
    msg_aggregator = MessagesAggregator()
    # We need a user db since the spam assets get synced during user unlock and
    # they touch both the global and the user DB at the same time
    with TemporaryDirectory():
        globaldb = GlobalDBHandler(data_dir=target_directory, sql_vm_instructions_cb=0)
        assets_updater = AssetsUpdater(msg_aggregator=msg_aggregator)
        conflicts = assets_updater.perform_update(
            up_to_version=args.target_version,
            conflicts=None,
        )

        # Add location asset mappings
        infojson = get_remote_info_json()
        updates = _retrieve_data_files(
            infojson=infojson,
        )
        for version, _updates in updates.items():
            updated_data = _updates.get(UpdateType.LOCATION_ASSET_MAPPINGS)
            if updated_data is None:
                print('Remote update invalid')
                continue  # perhaps broken file? Skipping
            RotkiDataUpdater.update_location_asset_mappings(updated_data, version)
    if conflicts is not None:
        print('There were conflicts during the update. Bailing.')
        sys.exit(1)

    globaldb.conn.execute('PRAGMA journal_mode=DELETE')
    # Due to the way globaldb initializes we have two of them. Clean up the extra one
    print('Cleaning up...')
    (target_directory / GLOBALDIR_NAME / GLOBALDB_NAME).rename(target_directory / GLOBALDB_NAME)
    shutil.rmtree(target_directory / GLOBALDIR_NAME)
    print('Done!')


if __name__ == '__main__':
    main()
