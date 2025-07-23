import os
import shutil
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.types import SPAM_PROTOCOL

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.db.drivers.gevent import DBCursor


# Whenever you upgrade the global DB make sure to:
# 1. Go to assets repo and tweak the min/max schema of the updates
# 2. Tweak ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS
# 3. Add the previous version to GLOBAL_DB_ASSETS_BREAKING_VERSIONS if it breaks asset updates compatibility  # noqa: E501
GLOBAL_DB_VERSION = 13
ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS = (3, GLOBAL_DB_VERSION)
MIN_SUPPORTED_GLOBAL_DB_VERSION = 2
# Global DB versions that break compatibility with existing asset updates.
# Used by apply_pending_compatible_updates() to determine the maximum safe version to update to.
GLOBAL_DB_ASSETS_BREAKING_VERSIONS = {
    9,  # v9 to v10 breaks asset collections schema
    12,  # v12 to v13 introduces solana tokens.
}
# Some functions that split the logic out of some GlobalDB query functions that are
# complicated enough to be abstracted and are used in multiple places. The main reason
# this exists is a bad design in the GlobalDBHandler() that can create circular imports.
# The cases I (Lefteris) know is maybe_upgrade_globaldb() and maybe_apply_globaldb_migrations()


def globaldb_get_setting_value(cursor: 'DBCursor', name: str, default_value: int) -> int:
    """
    Implementation of the logic of getting a setting from the global DB. Only for ints for now.
    """
    query = cursor.execute(
        'SELECT value FROM settings WHERE name=?;', (name,),
    )
    result = query.fetchall()
    # If setting is not set, it's the default
    if not result:
        return default_value

    return int(result[0][0])


def set_token_spam_protocol(
        write_cursor: 'DBCursor',
        token: 'EvmToken',
        is_spam: bool,
) -> None:
    """
    Set the protocol field of the provided token as `SPAM` depending on the `is_spam`
    argument and clean the resolver cache. It overwrites the protocol field of the provided token
    """
    write_cursor.execute(
        'UPDATE evm_tokens SET protocol=? WHERE identifier=?',
        (SPAM_PROTOCOL if is_spam is True else None, token.identifier),
    )
    object.__setattr__(token, 'protocol', None)
    AssetResolver.clean_memory_cache(identifier=token.identifier)


def initialize_globaldb(
        global_dir: Path,
        db_filename: str,
        sql_vm_instructions_cb: int,
) -> tuple[DBConnection, bool]:
    """
    Checks the database whether there are any not finished upgrades and automatically uses a
    backup if there are any. If no backup found, throws an error.

    - global_dir: The directory in which to find the global.db to initialize
    - db_filename: The filename of the DB. Almost always: global.db.
    - sql_vm_instructions_cb is a connection setting. Check DBConnection for details.

    Returns the DB connection and true if a DB backup was used and False otherwise
    May raise:
        - DBUpgradeError
    """
    connection = DBConnection(
        path=global_dir / db_filename,
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )
    try:
        with connection.read_ctx() as cursor:
            ongoing_upgrade_from_version = globaldb_get_setting_value(
                cursor=cursor,
                name='ongoing_upgrade_from_version',
                default_value=-1,
            )
    except sqlite3.OperationalError:  # pylint: disable=no-member
        ongoing_upgrade_from_version = -1  # Fresh DB

    if ongoing_upgrade_from_version == -1:
        return connection, False  # We are all good

    # Otherwise replace the db with a backup and relogin
    connection.close()
    backup_postfix = f'global_db_v{ongoing_upgrade_from_version}.backup'
    found_backups = list(filter(
        lambda x: x[-len(backup_postfix):] == backup_postfix,
        os.listdir(global_dir),
    ))
    if len(found_backups) == 0:
        raise DBUpgradeError(
            'Your global database is in a half-upgraded state and there was no backup '
            'found. Please open an issue on our github or contact us in our discord server.',
        )

    backup_to_use = max(found_backups)  # Use latest backup
    shutil.copyfile(
        global_dir / backup_to_use,
        global_dir / db_filename,
    )
    connection = DBConnection(
        path=global_dir / db_filename,
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )
    return connection, True
