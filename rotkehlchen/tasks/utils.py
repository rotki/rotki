from typing import TYPE_CHECKING
from rotkehlchen.constants.timing import DATA_UPDATES_REFRESH
from rotkehlchen.db.updates import LAST_DATA_UPDATES_KEY
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def should_check_data_updates(database: 'DBHandler') -> bool:
    """
    Checks if the last time we checked data updates is far enough to trigger
    the process of querying it again.
    """
    with database.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM settings WHERE name=?', (LAST_DATA_UPDATES_KEY,))
        timestamp_in_db = cursor.fetchone()

    if timestamp_in_db is None:
        return True

    last_update_ts = deserialize_timestamp(timestamp_in_db)
    return ts_now() - last_update_ts >= DATA_UPDATES_REFRESH
