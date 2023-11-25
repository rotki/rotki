from typing import TYPE_CHECKING, Optional

from rotkehlchen.types import ApiKey, ExternalService, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class ExternalServiceWithApiKey:
    """Interface for any ExternalService that has an API Key

    The reason why database is Optional is only for the initialization of cryptocompare to be able
    to happen without having the DB ready. That's since at the moment it happens at Rotkehlchen
    object initialization in order to be passed on to the Inquirer Singleton.

    The problem here is that at constructor of all other objects we need to be
    specifying that the DB is an object that is non optional and exists to satisfy type checkers.
    """

    def __init__(self, database: Optional['DBHandler'], service_name: ExternalService) -> None:
        self.db = database
        self.api_key: ApiKey | None = None
        self.service_name = service_name
        self.last_ts = Timestamp(0)

    def _get_api_key(self) -> ApiKey | None:
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
