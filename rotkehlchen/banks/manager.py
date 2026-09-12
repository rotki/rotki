"""Registry and lifecycle of the user's bank connections.

The bank counterpart of the exchange manager: it owns the connected connector objects,
persists their credentials, validates them at setup, and drives balance and history
queries. Credentials live in the same ``user_credentials`` table as exchange keys (the
location column tells them apart), but banks have their own manager, API surface and
setup flow because their credentials are described by a manifest, not a fixed
api key / secret / passphrase triple.
"""
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from importlib import import_module
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.typedefs import HistoryEventsStep
from rotkehlchen.banks.constants import SUPPORTED_BANKS
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeApiCredentials,
    ExchangeAuthCredentials,
    ExchangeLocationID,
    Location,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.banks.manifest import BankManifest
    from rotkehlchen.db.dbhandler import DBHandler
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

    def serialize(self) -> dict[str, Any]:
        return {
            'running': self.running,
            'last_sync_ts': self.last_sync_ts,
            'last_error': self.last_error,
        }


@dataclass
class BankCredentialInput:
    """Credentials as the API receives them: one value per manifest secret slot"""
    values: dict[str, str] = field(default_factory=dict)

    def to_exchange_credentials(self, name: str, location: Location) -> ExchangeApiCredentials:
        secret = self.values.get('api_secret')
        return ExchangeApiCredentials(
            name=name,
            location=location,
            api_key=ApiKey(self.values['api_key']),
            api_secret=ApiSecret(secret.encode()) if secret is not None else None,
            passphrase=self.values.get('passphrase'),
        )

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


class BankManager:

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.connected_banks: dict[Location, list[BankConnector]] = defaultdict(list)
        self.sync_status: dict[ExchangeLocationID, BankSyncStatus] = defaultdict(BankSyncStatus)
        self.msg_aggregator = msg_aggregator
        # serializes registry mutations together with their DB persistence, like the
        # exchange manager does. Never held across network calls.
        self.registry_lock = threading.Lock()
        self.database: DBHandler | None = None

    @staticmethod
    def get_manifest(location: Location) -> BankManifest:
        return BANK_MANIFESTS[location]

    @staticmethod
    def _connector_class(location: Location) -> type[BankConnector]:
        module = import_module(f'rotkehlchen.banks.{location!s}')
        return getattr(module, str(location).capitalize())

    def get_bank(self, name: str, location: Location) -> BankConnector | None:
        for bank in self.connected_banks.get(location, ()):
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
            'name': bank.name,
            'location': bank.location.serialize(),
            'display_name': bank.manifest.display_name,
            'sync_status': self.sync_status[bank.location_id()].serialize(),
        } for bank in self.iterate_banks()]

    def _instantiate(
            self,
            credentials: ExchangeApiCredentials,
            database: DBHandler,
    ) -> BankConnector:
        assert credentials.api_secret is not None, 'validated against the manifest'
        return self._connector_class(credentials.location)(
            name=credentials.name,
            api_key=credentials.api_key,
            secret=credentials.api_secret,
            database=database,
            msg_aggregator=self.msg_aggregator,
        )

    def setup_bank(
            self,
            name: str,
            location: Location,
            credentials: BankCredentialInput,
            database: DBHandler,
    ) -> tuple[bool, str]:
        """Validate the credentials against the bank and persist the connection.

        May raise InputError when the credentials do not fit the bank's manifest.
        """
        if location not in SUPPORTED_BANKS:
            return False, f'{location!s} is not a supported bank'
        credentials.validate_against(self.get_manifest(location), complete=True)
        if self.get_bank(name=name, location=location) is not None:
            return False, f'{location!s} bank connection {name} already exists'

        api_credentials = credentials.to_exchange_credentials(name=name, location=location)
        bank = self._instantiate(api_credentials, database)
        try:
            valid, message = bank.validate_api_key()
        except RemoteError as e:
            valid, message = False, str(e)
        if not valid:
            log.error('Failed to validate %s bank credentials for %s: %s', location, name, message)
            return False, message

        with self.registry_lock:
            if self.get_bank(name=name, location=location) is not None:
                return False, f'{location!s} bank connection {name} already exists'
            database.add_bank_credentials(api_credentials)
            self.connected_banks[location].append(bank)
        return True, ''

    def edit_bank(
            self,
            name: str,
            location: Location,
            new_name: str | None,
            credentials: BankCredentialInput,
    ) -> tuple[bool, str]:
        """Rename a connection and/or replace some of its credentials.

        New credentials are validated against the bank before anything is persisted.
        May raise InputError when they do not fit the manifest.
        """
        assert self.database is not None, 'edit_bank called before login'
        bank = self.get_bank(name=name, location=location)
        if bank is None:
            return False, f'Could not find {location!s} bank connection {name} for editing'
        credentials.validate_against(self.get_manifest(location), complete=False)
        if new_name is not None and new_name != name and self.get_bank(new_name, location):
            return False, f'{location!s} bank connection {new_name} already exists'

        auth = ExchangeAuthCredentials(
            api_key=ApiKey(credentials.values['api_key']) if 'api_key' in credentials.values else None,  # noqa: E501
            api_secret=ApiSecret(credentials.values['api_secret'].encode()) if 'api_secret' in credentials.values else None,  # noqa: E501
            passphrase=credentials.values.get('passphrase'),
        )
        if bank.edit_exchange_credentials(auth):
            try:
                valid, message = bank.validate_api_key()
            except RemoteError as e:
                valid, message = False, str(e)
            if not valid:
                bank.reset_to_db_credentials()
                return False, message

        with self.registry_lock, self.database.user_write() as write_cursor:
            self.database.edit_bank_credentials(
                write_cursor=write_cursor,
                name=name,
                location=location,
                new_name=new_name,
                credentials=auth,
            )
        if new_name is not None:
            bank.name = new_name
        return True, ''

    def delete_bank(self, name: str, location: Location) -> tuple[bool, str]:
        assert self.database is not None, 'delete_bank called before login'
        with self.registry_lock:
            bank = self.get_bank(name=name, location=location)
            if bank is None:
                return False, f'{location!s} bank connection {name} does not exist'

            remaining = [x for x in self.connected_banks[location] if x.name != name]
            if len(remaining) == 0:
                self.connected_banks.pop(location)
            else:
                self.connected_banks[location] = remaining
            self.sync_status.pop(bank.location_id(), None)
            with self.database.user_write() as write_cursor:
                self.database.remove_exchange(write_cursor=write_cursor, name=name, location=location)  # noqa: E501
                self.database.delete_used_query_range_for_exchange(
                    write_cursor=write_cursor,
                    location=location,
                    exchange_name=name,
                )
                bank.purge_local_state(write_cursor)
        return True, ''

    def delete_all_banks(self) -> None:
        """Forget every connection in memory. The DB is untouched (logout)."""
        self.connected_banks.clear()
        self.sync_status.clear()

    def initialize_banks(
            self,
            credentials: dict[Location, list[ExchangeApiCredentials]],
            database: DBHandler,
    ) -> None:
        """Instantiate the connectors of every saved bank credential at login"""
        self.database = database
        for location, entries in credentials.items():
            if location not in SUPPORTED_BANKS:
                continue
            for entry in entries:
                if entry.api_secret is None:
                    log.error('Skipping %s bank credentials %s: no secret', location, entry.name)
                    continue
                bank = self._instantiate(entry, database)
                with self.registry_lock:
                    self.connected_banks[location].append(bank)

    def query_bank_history_events(self, location: Location | None, name: str | None) -> None:
        """Sync the history of one connection, of every connection at a location, or of all.

        May raise RemoteError when one or more syncs fail and InputError when the
        connection does not exist.
        """
        if location is None:
            banks = list(self.iterate_banks())
        elif name is None:
            banks = list(self.connected_banks.get(location, ()))
        else:
            bank = self.get_bank(name=name, location=location)
            if bank is None:
                raise InputError(f'{location!s} bank connection {name} does not exist')
            banks = [bank]

        errors = []
        for bank in banks:
            try:
                self.sync_one(bank)
            except RemoteError as e:
                errors.append(f'{bank.manifest.display_name} {bank.name}: {e!s}')
        if len(errors) != 0:
            raise RemoteError('; '.join(errors))

    def sync_one(self, bank: BankConnector) -> None:
        """Run one connection's history sync and record its status.

        May raise RemoteError.
        """
        status = self.sync_status[bank.location_id()]
        status.running = True
        try:
            bank.query_history_events()
        except RemoteError as e:
            status.last_error = str(e)
            raise
        else:
            status.last_error = None
            status.last_sync_ts = ts_now()
        finally:
            status.running = False
            bank.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_FINISHED)
