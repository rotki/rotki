"""
Tool to create a globaldb with the remote updates in the asset repo and the updates in the
data repo for location assets mappings and unsupported assets . This script extends
the one named "main.py" in the same folder.

This script is intended to be used when testing the mappings to ensure that all the updates
are correctly applied. To call the script do:

python -m tools.assets_database.populate_with_mappings \
    --start-db 9 --target-version 24 --assets-branch develop --target-directory data
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from gevent import monkey

monkey.patch_all()  # isort:skip

from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.user_messages import MessagesAggregator

from .main import clean_folder, populate_db_with_assets


def populate_location_mappings():
    """Apply remote updates to query mappings for assets"""
    msg_aggregator = MessagesAggregator()
    with TemporaryDirectory() as tmp_dir:
        user_db = DBHandler(  # the RotkiDataUpdater takes a user db argument but is not used for the UpdateTypes that we use.  # noqa: E501
            user_data_dir=Path(tmp_dir),
            password='123',
            msg_aggregator=msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=0,
            resume_from_backup=False,
        )
        rotki_updater = RotkiDataUpdater(msg_aggregator=msg_aggregator, user_db=user_db)
        print('Applying remote updates')
        rotki_updater.check_for_updates(updates=[
            UpdateType.LOCATION_ASSET_MAPPINGS,
            UpdateType.LOCATION_UNSUPPORTED_ASSETS,
        ])


def main():
    globaldb, target_directory = populate_db_with_assets()
    populate_location_mappings()
    clean_folder(globaldb, target_directory)


if __name__ == '__main__':
    main()
