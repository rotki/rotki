from typing import TYPE_CHECKING

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.types import ApiKey, ExternalService, Timestamp
from rotkehlchen.utils.interfaces import DBSetterMixin
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

    def __init__(self, database: 'DBHandler', service_name: ExternalService) -> None:
        self.db = database
        self.api_key: ApiKey | None = None
        self.service_name = service_name
        self.last_ts = Timestamp(0)

    def _get_api_key(self) -> ApiKey | None:
        """A function to get the API key from the DB (if we have one initialized)"""
        if self.api_key and ts_now() - self.last_ts <= 120:
            return self.api_key

        if not self.db:
            return None

        # else query the DB
        credentials = self.db.get_external_service_credentials(self.service_name)
        self.last_ts = ts_now()
        # If we get here it means the api key is modified/saved
        self.api_key = credentials.api_key if credentials else None
        return self.api_key


class ExternalServiceWithApiKeyOptionalDB(ExternalServiceWithApiKey, DBSetterMixin):
    """An extension of ExternalServiceWithAPIKey where the DB is optional at initialization

    The reason why database is Optional is only for the initialization of some services like
    defillama and cryptocompare to be able to happen without having the DB ready.
    That's needed since it needs to be passed down to the Inquirer singleton before
    DB is ready.
    """
    def __init__(self, database: 'DBHandler|None', service_name: ExternalService) -> None:
        super().__init__(database=database, service_name=service_name)  # type: ignore  # we are aware of discrepancy
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    def _get_name(self) -> str:
        return str(self.service_name)


class ExternalServiceWithRecommendedApiKey(ExternalServiceWithApiKey):
    """An extension of ExternalServiceWithAPIKey for services where we recommend always
    using an API key and warn the user if it's missing.
    """
    def __init__(self, database: 'DBHandler', service_name: ExternalService) -> None:
        ExternalServiceWithApiKey.__init__(self, database=database, service_name=service_name)
        self.warning_given = False

    def _get_api_key(self) -> ApiKey | None:
        if (api_key := ExternalServiceWithApiKey._get_api_key(self)) is not None:
            return api_key

        self.maybe_warn_missing_key()
        return None

    def maybe_warn_missing_key(self) -> None:
        """Warns the user once if the Helius api key is missing."""
        if not self.warning_given:
            self.db.msg_aggregator.add_message(
                message_type=WSMessageType.MISSING_API_KEY,
                data={'service': self.service_name.serialize()},
            )
            self.warning_given = True
