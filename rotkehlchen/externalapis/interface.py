from typing import TYPE_CHECKING, Optional

from rotkehlchen.types import ApiKey, ExternalService, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class ExternalServiceWithApiKey:

    def __init__(self, database: Optional['DBHandler'], service_name: ExternalService) -> None:
        self.db = database
        self.api_key: Optional[ApiKey] = None
        self.service_name = service_name
        self.last_ts = Timestamp(0)

    def _get_api_key(self) -> Optional[ApiKey]:
        """A function to get the API key from the DB (if we have one initialized)"""
        if not self.db:
            return None

        if self.api_key and ts_now() - self.last_ts <= 120:
            return self.api_key

        # else query the DB
        credentials = self.db.get_external_service_credentials(self.service_name)
        self.last_ts = ts_now()
        # If we get here it means the api key is modified/saved
        self.api_key = credentials.api_key if credentials else None
        return self.api_key
