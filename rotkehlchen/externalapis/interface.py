from typing import Optional, TYPE_CHECKING

from rotkehlchen.typing import ApiKey, ExternalService, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class ExternalServiceWithApiKey():

    def __init__(self, database: Optional['DBHandler'], service_name: ExternalService) -> None:
        super().__init__()
        self.db = database
        self.api_key: Optional[ApiKey] = None
        self.api_key_saved_ts = Timestamp(0)
        self.service_name = service_name

    def _get_api_key(self) -> Optional[ApiKey]:
        """A function to get the API key from the DB (if we have one initialized)

        It's optimized to not query the DB every time we want to know the API
        key, but to remember it and re-query only if the DB has been written to
        again after the last time we queried it.
        """
        if not self.db:
            return None

        if self.api_key is None:
            # If we don't have a key try to get one from the DB
            credentials = self.db.get_external_service_credentials(self.service_name)
        else:
            # If we have a key check the DB's last write time and if nothign new
            # got written there return the already known key
            if self.db.last_write_ts and self.db.last_write_ts <= self.api_key_saved_ts:
                return self.api_key

            # else query the DB
            credentials = self.db.get_external_service_credentials(self.service_name)

        # If we get here it means the api key is modified/saved
        self.api_key = credentials.api_key if credentials else None
        self.api_key_saved_ts = ts_now()
        return self.api_key
