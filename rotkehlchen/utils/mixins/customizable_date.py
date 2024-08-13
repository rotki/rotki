from typing import TYPE_CHECKING

from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor


class CustomizableDateMixin:

    def __init__(self, database: 'DBHandler') -> None:
        self.database = database
        with database.conn.read_ctx() as cursor:
            self.reload_settings(cursor)

    def reload_settings(self, cursor: 'DBCursor') -> None:
        """Reload the settings from the DB"""
        self.settings = self.database.get_settings(cursor)

    def timestamp_to_date(self, timestamp: Timestamp) -> str:
        """Turn the timestamp to a date string depending on the user DB settings"""
        return timestamp_to_date(
            timestamp,
            formatstr=self.settings.date_display_format,
            treat_as_local=self.settings.display_date_in_localtime,
        )
