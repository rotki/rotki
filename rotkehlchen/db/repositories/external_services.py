"""Repository for managing external service credentials in the database."""
import logging
from typing import TYPE_CHECKING

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor


log = logging.getLogger(__name__)


class ExternalServicesRepository:
    """Repository for handling all external service credential operations."""

    def __init__(self, conn: 'DBConnection') -> None:
        """Initialize the external services repository."""
        self.conn = conn

    def add_credentials(
            self,
            write_cursor: 'DBCursor',
            credentials: list[ExternalServiceApiCredentials],
    ) -> None:
        """Add or update external service credentials"""
        write_cursor.executemany(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) VALUES(?, ?, ?)',  # noqa: E501
            [c.serialize_for_db() for c in credentials],
        )

    def delete_credentials(
            self, write_cursor: 'DBCursor', services: list[ExternalService],
    ) -> None:
        """Delete external service credentials"""
        write_cursor.executemany(
            'DELETE FROM external_service_credentials WHERE name=?;',
            [(service.name.lower(),) for service in services],
        )

    def get_all_credentials(self, cursor: 'DBCursor') -> list[ExternalServiceApiCredentials]:
        """Returns a list with all the external service credentials saved in the DB"""
        cursor.execute('SELECT name, api_key, api_secret from external_service_credentials;')

        result = []
        for q in cursor:
            try:
                service = ExternalService.deserialize(q[0])
            except DeserializationError:
                log.error(f'Unknown external service name "{q[0]}" found in the DB')
                continue

            result.append(ExternalServiceApiCredentials(
                service=service,
                api_key=q[1],
                api_secret=q[2],
            ))
        return result

    def get_credentials(
            self,
            cursor: 'DBCursor',
            service_name: ExternalService,
    ) -> ExternalServiceApiCredentials | None:
        """If existing it returns the external service credentials for the given service"""
        cursor.execute(
            'SELECT api_key, api_secret from external_service_credentials WHERE name=?;',
            (service_name.name.lower(),),
        )
        if (result := cursor.fetchone()) is None:
            return None

        # There can only be 1 result, since name is the primary key of the table
        return ExternalServiceApiCredentials(
            service=service_name, api_key=result[0], api_secret=result[1],
        )
