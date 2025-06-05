"""
Tool to create a globaldb with the assets and/or remote updates from the assets and data repo.

Usage:
python -m tools.assets_database.main <args>

Args:
    --start-db-version <int>
    --start-db-hash <string>
    --start-db-path <string>
    --target-version <int>
    --assets-branch <string>
    --target-directory <string>
    --update-mode <string>
    --help

- Use one of `--start-db-version`, `--start-db-hash` or `--start-db-path` to specify the starting DB.
- Use `--target-version` to specify the target assets version for the update.
- Use `--assets-branch` to specify the branch to pull the asset DB from.
- Use `--target-directory` to specify the directory to write the file in. Default is current directory.
- Use `--update-mode` to specify the update mode to use. "assets" will apply only the assets updates, "remote" will apply only remote data updates, "all" will apply both.

Example command:
python -m tools.assets_database.main --start-db-path /<path to last release's db>/global.db --target-version 28 --assets-branch develop --update-mode all
"""  # noqa: E501
from typing import TYPE_CHECKING

from gevent import monkey

monkey.patch_all()  # isort:skip

from pathlib import Path
from tempfile import TemporaryDirectory

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.globaldb.asset_updates.manager import AssetsUpdater
from rotkehlchen.user_messages import MessagesAggregator

from .utils import clean_folder, parse_args, prepare_globaldb

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


def populate_db_with_assets(globaldb: 'GlobalDBHandler'):
    """Populate the globaldb created in target_directory with the updates in the remote assets repo
    """
    print('Applying updates...')
    msg_aggregator = MessagesAggregator()
    assets_updater = AssetsUpdater(
        globaldb=globaldb,
        msg_aggregator=msg_aggregator,
    )

    if (conflicts := assets_updater.perform_update(
        up_to_version=parse_args().target_version,
        conflicts=None,
    )) is not None:
        assert assets_updater.perform_update(
            up_to_version=None,
            conflicts={
                Asset(conflict['identifier']): 'remote'
                for conflict in conflicts
            },
        ) is None, 'Could not resolve all conflicts during assets upgrade using "remote" data'


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
        print('Applying remote updates...')
        rotki_updater.check_for_updates(updates=[
            UpdateType.LOCATION_ASSET_MAPPINGS,
            UpdateType.LOCATION_UNSUPPORTED_ASSETS,
            UpdateType.COUNTERPARTY_ASSET_MAPPINGS,
        ])


def main() -> None:
    args = parse_args()
    globaldb, target_directory = prepare_globaldb(args)

    if args.update_mode in {'assets', 'all'}:
        populate_db_with_assets(globaldb)
    if args.update_mode in {'remote', 'all'}:
        populate_location_mappings()

    clean_folder(globaldb, target_directory)


if __name__ == '__main__':
    main()
