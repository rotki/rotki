from typing import TYPE_CHECKING

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def run_data_issue_remediation(database: DBHandler) -> None:
    """Run the daily automatic data-issue remediation task.

    Remediation logic belongs behind this entry point. The timestamp is updated after all work
    completes so failed runs remain eligible for a retry.
    """
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
            value=ts_now(),
        )
