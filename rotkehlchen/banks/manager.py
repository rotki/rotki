"""Registry and lifecycle of the user's bank connections.

The bank counterpart of the exchange manager: it owns the connected connector objects,
persists their credentials, validates them at setup, and drives balance and history
queries. Connections live in ``integration_connections`` next to the exchange ones (the
connector tells them apart), but banks have their own manager, API surface and setup flow
because their credentials are described by a manifest, not a fixed api key / secret /
passphrase triple, and a connector may let each connection choose its bank location.
"""
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from importlib import import_module
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.api.websockets.typedefs import HistoryEventsStep
from rotkehlchen.banks.constants import FINTS_CONNECTOR, QONTO_CONNECTOR, SUPPORTED_BANKS
from rotkehlchen.banks.errors import BankAuthChallenge, BankError, BankMFARequired
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.connections.types import (
    ConnectionIdentifier,
    ConnectorIdentifier,
    IntegrationConnection,
    new_connection_identifier,
)
from rotkehlchen.db.connections import DBConnections
from rotkehlchen.db.locations import DBLocations
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.locations.constants import LOCATION_BANKS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExchangeAuthCredentials
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.banks.manifest import BankManifest
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.types import Timestamp
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass
class BankSyncStatus:
    """What the UI shows next to a connection"""
    running: bool = False
    last_sync_ts: Timestamp | None = None
    last_error: str | None = None
    auth_challenge: BankAuthChallenge | None = None

    def serialize(self) -> dict[str, Any]:
        return {
            'running': self.running,
            'last_sync_ts': self.last_sync_ts,
            'last_error': self.last_error,
            'auth_challenge': (
                self.auth_challenge.serialize() if self.auth_challenge is not None else None
            ),
        }


@dataclass
class BankCredentialInput:
    """Credentials as the API receives them: one value per manifest secret slot"""
    values: dict[str, str] = field(default_factory=dict)

    def validate_against(self, manifest: BankManifest, complete: bool) -> None:
        """Raise InputError when the given values do not fit the manifest's secrets.

        `complete` demands every declared slot (setup); otherwise any subset is fine (edit).
        """
        declared = {secret.slot for secret in manifest.secrets}
        if (unknown := set(self.values) - declared):
            raise InputError(
                f'{manifest.display_name} does not use credential fields {sorted(unknown)}. '
                f'It needs {sorted(declared)}',
            )
        if complete and (missing := declared - set(self.values)):
            raise InputError(
                f'{manifest.display_name} needs the credential fields {sorted(missing)}',
            )
        for slot, value in self.values.items():
            if value == '':
                raise InputError(f'The {slot} credential field must not be empty')


# The module and class implementing every bank connector
BANK_CONNECTOR_CLASSES: Final[dict[str, tuple[str, str]]] = {
    QONTO_CONNECTOR: ('rotkehlchen.banks.qonto', 'Qonto'),
    FINTS_CONNECTOR: ('rotkehlchen.banks.fints', 'Fints'),
}


class BankManager:

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        # the connected banks of every connector
        self.connected_banks: dict[str, list[BankConnector]] = defaultdict(list)
        self.pending_setups: dict[ConnectionIdentifier, BankConnector] = {}
        self.sync_status: dict[ConnectionIdentifier, BankSyncStatus] = defaultdict(BankSyncStatus)
        self.msg_aggregator = msg_aggregator
        # serializes registry mutations together with their DB persistence, like the
        # exchange manager does. Never held across network calls.
        self.registry_lock = threading.Lock()
        self.database: DBHandler | None = None

    @staticmethod
    def get_manifest(connector: str) -> BankManifest:
        return BANK_MANIFESTS[ConnectorIdentifier(connector)]

    @staticmethod
    def _connector_class(connector: str) -> type[BankConnector]:
        module_name, class_name = BANK_CONNECTOR_CLASSES[connector]
        return getattr(import_module(module_name), class_name)

    def get_bank(self, identifier: str) -> BankConnector | None:
        for bank in self.iterate_banks():
            if bank.connection_identifier == identifier:
                return bank
        return None

    def get_bank_by_name(self, connector: str, name: str) -> BankConnector | None:
        for bank in self.connected_banks.get(connector, ()):
            if bank.name == name:
                return bank
        return None

    def iterate_banks(self) -> Iterator[BankConnector]:
        for banks in list(self.connected_banks.values()):
            yield from banks

    def connected_banks_num(self) -> int:
        return sum(1 for _ in self.iterate_banks())

    def get_connected_banks_info(self) -> list[dict[str, Any]]:
        return [{
            'identifier': bank.connection_identifier,
            'name': bank.name,
            'connector': bank.manifest.connector_identifier,
            'location': bank.location,
            'display_name': bank.manifest.display_name,
            'sync_status': self.sync_status[bank.connection_identifier].serialize(),
        } for bank in self.iterate_banks()]

    def _instantiate(
            self,
            connector: str,
            name: str,
            location: LocationIdentifier,
            credentials: ExchangeAuthCredentials,
            database: DBHandler,
            connection_identifier: ConnectionIdentifier,
    ) -> BankConnector:
        assert credentials.api_key is not None and credentials.api_secret is not None, 'validated against the manifest'  # noqa: E501
        return self._connector_class(connector)(
            name=name,
            api_key=credentials.api_key,
            secret=credentials.api_secret,
            database=database,
            msg_aggregator=self.msg_aggregator,
            location=location,
            connection_identifier=connection_identifier,
        )

    @staticmethod
    def _connection_location(
            cursor: DBCursor,
            manifest: BankManifest,
            location: LocationIdentifier | None,
    ) -> LocationIdentifier:
        """The location a new connection of the connector puts its data in.

        May raise InputError if the connector needs a location in the Banks subtree and none
        or another one is given.
        """
        if manifest.fixed_location is not None:
            if location is not None and location != manifest.fixed_location:
                raise InputError(
                    f'{manifest.display_name} connections always use the '
                    f'{manifest.fixed_location} location',
                )
            return manifest.fixed_location
        if location is None:
            raise InputError(f'{manifest.display_name} connections need the location of their bank')  # noqa: E501
        node = DBLocations().validate_assignable(cursor, location)
        if node.identifier not in DBLocations.descendants(cursor, [LOCATION_BANKS]):
            raise InputError(f'Location {location} is not a bank')
        return node.identifier

    def setup_bank(
            self,
            name: str,
            connector: str,
            location: LocationIdentifier | None,
            credentials: BankCredentialInput,
            database: DBHandler,
    ) -> tuple[ConnectionIdentifier | None, str]:
        """Validate the credentials against the bank and persist the connection. Returns the
        new connection's identifier, or None and the reason the setup failed.

        May raise InputError when the credentials do not fit the bank's manifest or the
        location does not fit the connector, and BankMFARequired when the bank asks for an
        authentication, which then continues under the identifier the exception carries.
        """
        if connector not in SUPPORTED_BANKS:
            return None, f'{connector!s} is not a supported bank'
        manifest = self.get_manifest(connector)
        credentials.validate_against(manifest, complete=True)
        with database.conn.read_ctx() as cursor:
            location = self._connection_location(cursor, manifest, location)
        if self.get_bank_by_name(connector=connector, name=name) is not None:
            return None, f'{connector!s} bank connection {name} already exists'

        connector_class = self._connector_class(connector)
        try:
            api_credentials = connector_class.api_credentials_from_values(values=credentials.values)  # noqa: E501
        except BankError as e:
            return None, str(e)
        bank = self._instantiate(
            connector=connector,
            name=name,
            location=location,
            credentials=api_credentials,
            database=database,
            connection_identifier=new_connection_identifier(),
        )
        try:
            valid, message = bank.validate_api_key()
        except BankMFARequired as e:
            self.pending_setups[bank.connection_identifier] = bank
            e.connection_identifier = bank.connection_identifier
            raise
        except RemoteError as e:
            valid, message = False, str(e)
        if not valid:
            log.error('Failed to validate %s bank credentials for %s: %s', connector, name, message)  # noqa: E501
            return None, message

        with self.registry_lock:
            if self.get_bank_by_name(connector=connector, name=name) is not None:
                return None, f'{connector!s} bank connection {name} already exists'
            self._persist(database, bank)
            self.connected_banks[connector].append(bank)
        return bank.connection_identifier, ''

    @staticmethod
    def _persist(database: DBHandler, bank: BankConnector) -> None:
        """May raise InputError if the connection can not be saved"""
        with database.user_write() as write_cursor:
            DBConnections.add(
                write_cursor=write_cursor,
                name=bank.name,
                connector=bank.manifest.connector_identifier,
                location=bank.location,
                api_key=bank.api_key,
                api_secret=bank.secret,
                identifier=bank.connection_identifier,
            )

    def answer_bank_authentication(
            self,
            identifier: ConnectionIdentifier,
            response: str | None,
    ) -> tuple[bool, str]:
        """Resume a pending connector challenge and finish setup when it was an add flow."""
        pending_setup = self.pending_setups.get(identifier)
        bank = pending_setup or self.get_bank(identifier)
        if bank is None:
            return False, f'Bank connection {identifier} has no pending authentication'
        resume_history = (
            pending_setup is None and bank.pending_authentication_resumes_history()
        )

        try:
            bank.answer_authentication(response)
        except BankMFARequired as e:
            e.connection_identifier = identifier
            self.sync_status[identifier].auth_challenge = e.challenge
            raise
        self.sync_status[identifier].auth_challenge = None
        if pending_setup is None:
            if resume_history:
                self.sync_one(bank)
            return True, ''

        valid, message = bank.validate_api_key()
        if not valid:
            return False, message
        assert self.database is not None, 'authentication answered before login'
        with self.registry_lock:
            self._persist(self.database, bank)
            self.connected_banks[bank.manifest.connector_identifier].append(bank)
            self.pending_setups.pop(identifier, None)
        return True, ''

    def edit_bank(
            self,
            identifier: ConnectionIdentifier,
            new_name: str | None,
            credentials: BankCredentialInput,
    ) -> tuple[bool, str]:
        """Rename a connection and/or replace some of its credentials.

        New credentials are validated against the bank before anything is persisted.
        May raise InputError when they do not fit the manifest.
        """
        assert self.database is not None, 'edit_bank called before login'
        if (bank := self.get_bank(identifier)) is None:
            return False, f'Could not find bank connection {identifier} for editing'
        connector = bank.manifest.connector_identifier
        credentials.validate_against(bank.manifest, complete=False)
        if (
                new_name is not None and new_name != bank.name and
                self.get_bank_by_name(connector=connector, name=new_name) is not None
        ):
            return False, f'{connector!s} bank connection {new_name} already exists'

        try:
            auth = type(bank).api_credentials_from_values(
                values=credentials.values,
                current=ExchangeAuthCredentials(bank.api_key, bank.secret, None),
            )
        except BankError as e:
            return False, str(e)
        credentials_changed = bank.edit_exchange_credentials(auth)
        if credentials_changed:
            try:
                valid, message = bank.validate_api_key()
            except RemoteError as e:
                valid, message = False, str(e)
            if not valid:
                bank.reset_to_db_credentials()
                return False, message

        with self.registry_lock:
            persisted = False
            try:
                with self.database.user_write() as write_cursor:
                    DBConnections(self.database).edit(
                        write_cursor=write_cursor,
                        identifier=identifier,
                        new_name=new_name,
                        credentials=auth,
                    )
                persisted = True
            finally:
                if not persisted and credentials_changed:
                    bank.reset_to_db_credentials()
            if new_name is not None:
                bank.name = new_name
        return True, ''

    def delete_bank(self, identifier: ConnectionIdentifier) -> tuple[bool, str]:
        assert self.database is not None, 'delete_bank called before login'
        with self.registry_lock:
            if (bank := self.get_bank(identifier)) is None:
                return False, f'Bank connection {identifier} does not exist'

            with self.database.user_write() as write_cursor:
                self.database.remove_exchange(write_cursor=write_cursor, identifier=identifier)
            connector = bank.manifest.connector_identifier
            if len(remaining := [x for x in self.connected_banks[connector] if x is not bank]) == 0:  # noqa: E501
                self.connected_banks.pop(connector)
            else:
                self.connected_banks[connector] = remaining
            self.sync_status.pop(identifier, None)
        return True, ''

    def delete_all_banks(self) -> None:
        """Forget every connection in memory. The DB is untouched (logout)."""
        self.connected_banks.clear()
        self.pending_setups.clear()
        self.sync_status.clear()

    def initialize_banks(
            self,
            connections: list[IntegrationConnection],
            database: DBHandler,
    ) -> None:
        """Instantiate the connectors of every saved bank connection at login"""
        self.database = database
        for connection in connections:
            if connection.connector not in SUPPORTED_BANKS:
                continue
            if connection.api_secret is None:
                log.error('Skipping %s bank connection %s: no secret', connection.connector, connection.name)  # noqa: E501
                continue
            try:
                bank = self._instantiate(
                    connector=connection.connector,
                    name=connection.name,
                    location=connection.location,
                    credentials=ExchangeAuthCredentials(connection.api_key, connection.api_secret, connection.passphrase),  # noqa: E501
                    database=database,
                    connection_identifier=connection.identifier,
                )
            except BankError as e:
                log.error('Could not restore %s bank connection %s: %s', connection.connector, connection.name, e)  # noqa: E501
                continue
            with self.registry_lock:
                self.connected_banks[connection.connector].append(bank)
            try:
                if (challenge := bank.pending_authentication()) is not None:
                    self.sync_status[connection.identifier].auth_challenge = challenge
            except BankError as e:
                log.warning(
                    'Could not restore pending authentication for %s bank %s: %s',
                    connection.connector,
                    connection.name,
                    e,
                )

    def query_bank_history_events(self, connector: str | None, identifier: str | None) -> None:
        """Sync the history of one connection, of every connection of a connector, or of all.

        May raise RemoteError when one or more syncs fail and InputError when the
        connection does not exist.
        """
        if identifier is not None:
            if (bank := self.get_bank(identifier)) is None:
                raise InputError(f'Bank connection {identifier} does not exist')
            banks = [bank]
        elif connector is None:
            banks = list(self.iterate_banks())
        else:
            banks = list(self.connected_banks.get(connector, ()))

        errors = []
        for bank in banks:
            try:
                self.sync_one(bank)
            except BankMFARequired:
                raise
            except RemoteError as e:
                errors.append(f'{bank.manifest.display_name} {bank.name}: {e!s}')
        if len(errors) != 0:
            raise RemoteError('; '.join(errors))

    def sync_one(self, bank: BankConnector) -> None:
        """Run one connection's history sync and record its status.

        May raise RemoteError.
        """
        status = self.sync_status[bank.connection_identifier]
        status.running = True
        try:
            bank.query_history_events()
        except BankMFARequired as e:
            status.auth_challenge = e.challenge
            status.last_error = None
            raise
        except RemoteError as e:
            status.last_error = str(e)
            raise
        else:
            status.auth_challenge = None
            status.last_error = None
            status.last_sync_ts = ts_now()
        finally:
            status.running = False
            bank.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_FINISHED)
