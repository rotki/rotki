from typing import TYPE_CHECKING, Literal

from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def should_run_periodic_task(
        database: 'DBHandler',
        key_name: Literal['last_data_updates_ts', 'last_evm_accounts_detect_ts'],
        refresh_period: int,
) -> bool:
    """
    Checks if enough time has elapsed since the last run of a periodic task in order to run
    it again.
    """
    with database.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM settings WHERE name=?', (key_name,))
        timestamp_in_db = cursor.fetchone()

    if timestamp_in_db is None:
        return True

    last_update_ts = deserialize_timestamp(timestamp_in_db[0])
    return ts_now() - last_update_ts >= refresh_period
