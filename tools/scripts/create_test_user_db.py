"""
Create a blank user DB.

Primarily intended for creating DBs for use with the DB upgrade tests. For this you should
check out the tag of the last release before running this script to ensure the db created
is in the state it should be in *before* the new upgrade.

Saves the new DB to the current directory.
"""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from rotkehlchen.constants.misc import DEFAULT_DB_POOL_SIZE, DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import TRACE, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.user_messages import MessagesAggregator

add_logging_level('TRACE', TRACE)
configure_logging(default_args())

print('Creating user DB...')
with TemporaryDirectory() as temp_data_dir:
    GlobalDBHandler(  # globaldb must be present before initializing DBHandler
        data_dir=Path(temp_data_dir),
        perform_assets_updates=True,
        sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        db_pool_size=DEFAULT_DB_POOL_SIZE,
        msg_aggregator=(msg_aggregator := MessagesAggregator()),
    )
    db = DBHandler(
        user_data_dir=Path(temp_data_dir),
        password='123',
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        resume_from_backup=False,
        db_pool_size=DEFAULT_DB_POOL_SIZE,
    )
    db.conn.close()
    shutil.move(
        src=f'{temp_data_dir}/rotkehlchen.db',
        dst=(dst := f'{Path.cwd()}/v{ROTKEHLCHEN_DB_VERSION}_rotkehlchen.db'),
    )
    print(f'Saved DB to {dst}')
