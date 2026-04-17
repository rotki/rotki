"""
Tool to create a globaldb with the assets and/or remote updates from the assets and data repo.

Usage:
python -m tools.assets_database.main <args>

Args:
    --start-db-version <int>
    --start-db-hash <string>
    --start-db-path <string>
    --target-version <int>
    --override-assets-version <int>
    --assets-branch <string>
    --target-directory <string>
    --update-mode <string>
    --help

- Use one of `--start-db-version`, `--start-db-hash` or `--start-db-path` to specify the starting DB.
- Use `--target-version` to specify the target assets version for the update.
- Use `--override-assets-version` to override local `assets_version` before updating (useful to reapply a version).
- Use `--assets-branch` to specify the branch to pull the asset DB from.
- Use `--target-directory` to specify the directory to write the file in. Default is current directory.
- Use `--update-mode` to specify the update mode to use. "assets" will apply only the assets updates, "remote" will apply only remote data updates, "all" will apply both.

Example command:
python -m tools.assets_database.main --start-db-path /<path to last release's db>/global.db --target-version 28 --assets-branch develop --update-mode all
"""  # noqa: E501
from typing import TYPE_CHECKING

from gevent import monkey

monkey.patch_all()  # isort:skip

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.globaldb.asset_updates.manager import ASSETS_VERSION_KEY, AssetsUpdater
from rotkehlchen.user_messages import MessagesAggregator

from .utils import clean_folder, parse_args, prepare_globaldb

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


def _print_collected_messages(msg_aggregator: MessagesAggregator, stage: str) -> None:
    warnings = msg_aggregator.consume_warnings()
    errors = msg_aggregator.consume_errors()
    if len(warnings) == 0 and len(errors) == 0:
        print(f'[{stage}] No warnings or errors reported by updater')
        return

    print(f'[{stage}] Updater messages: {len(warnings)} warning(s), {len(errors)} error(s)')
    for warning in warnings:
        print(f'[{stage}] WARNING: {warning}')
    for error in errors:
        print(f'[{stage}] ERROR: {error}')


def populate_db_with_assets(globaldb: 'GlobalDBHandler', args: argparse.Namespace) -> None:
    """Populate the globaldb created in target_directory with the updates in the remote assets repo
    """
    print('Applying updates...')

    if args.override_assets_version is not None:
        print(
            f'Overriding local {ASSETS_VERSION_KEY} to '
            f'{args.override_assets_version} before applying updates',
        )
        with globaldb.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                (ASSETS_VERSION_KEY, str(args.override_assets_version)),
            )

    msg_aggregator = MessagesAggregator()
    assets_updater = AssetsUpdater(
        globaldb=globaldb,
        msg_aggregator=msg_aggregator,
    )
    assets_updater.branch = args.assets_branch
    print(f'Using assets updates branch: {assets_updater.branch}')
    local_version, remote_version, new_changes = assets_updater.check_for_updates()
    target_version = (
        min(args.target_version, remote_version)
        if args.target_version is not None
        else remote_version
    )
    print(
        'Assets updater status: '
        f'local_assets_version={local_version}, '
        f'remote_assets_version={remote_version}, '
        f'target_version={target_version}, '
        f'pending_changes={new_changes}',
    )

    if (conflicts := assets_updater.perform_update(
        up_to_version=args.target_version,
        conflicts=None,
    )) is not None:
        assert assets_updater.perform_update(
            up_to_version=args.target_version,
            conflicts={
                Asset(conflict['identifier']): 'remote'
                for conflict in conflicts
            },
        ) is None, 'Could not resolve all conflicts during assets upgrade using "remote" data'

    _print_collected_messages(msg_aggregator, stage='assets')


def populate_location_mappings():
    """Apply remote updates to query mappings for assets"""
    msg_aggregator = MessagesAggregator()
    with TemporaryDirectory() as tmp_dir:
        rotki_updater = RotkiDataUpdater(
            msg_aggregator=msg_aggregator,
            user_db=DBHandler(
                user_data_dir=Path(tmp_dir),
                password='123',
                msg_aggregator=msg_aggregator,
                initial_settings=None,
                sql_vm_instructions_cb=0,
                resume_from_backup=False,
            ),
        )
        rotki_updater.branch = 'develop'
        print(f'Applying remote updates from data branch: {rotki_updater.branch}')
        rotki_updater.check_for_updates(updates=[
            UpdateType.LOCATION_ASSET_MAPPINGS,
            UpdateType.LOCATION_UNSUPPORTED_ASSETS,
            UpdateType.COUNTERPARTY_ASSET_MAPPINGS,
            UpdateType.RPC_NODES,
        ])

    _print_collected_messages(msg_aggregator, stage='remote')


def main() -> None:
    args = parse_args()
    globaldb, target_directory = prepare_globaldb(args)

    if args.update_mode in {'assets', 'all'}:
        populate_db_with_assets(globaldb, args)
    if args.update_mode in {'remote', 'all'}:
        populate_location_mappings()

    clean_folder(globaldb, target_directory)


if __name__ == '__main__':
    main()
