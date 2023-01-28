from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


# Whenever you upgrade the global DB make sure to:
# 1. Go to assets repo and tweak the min/max schema of the updates
# 2. Tweak ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS
GLOBAL_DB_VERSION = 5
ASSETS_FILE_IMPORT_ACCEPTED_GLOBALDB_VERSIONS = (3, GLOBAL_DB_VERSION)
MIN_SUPPORTED_GLOBAL_DB_VERSION = 2
GLOBAL_DB_FILENAME = 'global.db'

# Some functions that split the logic out of some GlobalDB query functions that are
# complicated enough to be abstracted and are used in multiple places. The main reason
# this exists is a bad design in the GlobalDBHandler() that can create circular imports.
# The one and only case I (Lefteris) know is maybe_upgrade_globaldb()


def globaldb_get_setting_value(cursor: 'DBCursor', name: str, default_value: int) -> int:
    """
    Implementation of the logic of getting a setting from the global DB. Only for ints for now.
    """
    query = cursor.execute(
        'SELECT value FROM settings WHERE name=?;', (name,),
    )
    result = query.fetchall()
    # If setting is not set, it's the default
    if len(result) == 0:
        return default_value

    return int(result[0][0])
