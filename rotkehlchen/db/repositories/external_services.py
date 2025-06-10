"""Repository for managing external service credentials in the database."""
import logging
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.errors.api import IncorrectApiKeyFormat
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.types import ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.user_messages import MessagesAggregator


log = logging.getLogger(__name__)


class ExternalServicesRepository:
    """Repository for handling all external service credential operations."""

    def __init__(self, conn: 'DBConnection', msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the external services repository."""
        self.conn = conn
        self.msg_aggregator = msg_aggregator

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

    def set_rotkehlchen_premium(self, credentials: PremiumCredentials) -> None:
        """Save the rotki premium credentials in the DB"""
        cursor = self.conn.cursor()
        # We don't care about previous value so simple insert or replace should work
        cursor.execute(
            'INSERT OR REPLACE INTO user_credentials'
            '(name, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?)',
            ('rotkehlchen', credentials.serialize_key(), credentials.serialize_secret(), None),
        )
        self.conn.commit()
        cursor.close()
        # Do not update the last write here. If we are starting in a new machine
        # then this write is mandatory and to sync with data from server we need
        # an empty last write ts in that case

    def delete_premium_credentials(self, write_cursor: 'DBCursor') -> bool:
        """Delete the rotki premium credentials in the DB for the logged-in user"""
        try:
            write_cursor.execute(
                'DELETE FROM user_credentials WHERE name=?', ('rotkehlchen',),
            )
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            log.error(f'Could not delete rotki premium credentials: {e!s}')
            return False
        return True

    def get_rotkehlchen_premium(self, cursor: 'DBCursor') -> PremiumCredentials | None:
        cursor.execute(
            "SELECT api_key, api_secret FROM user_credentials where name='rotkehlchen';",
        )
        result = cursor.fetchone()
        if result is None:
            return None

        try:
            credentials = PremiumCredentials(
                given_api_key=result[0],
                given_api_secret=result[1],
            )
        except IncorrectApiKeyFormat:
            self.msg_aggregator.add_error(
                'Incorrect rotki API Key/Secret format found in the DB. Skipping ...',
            )
            return None

        return credentials
