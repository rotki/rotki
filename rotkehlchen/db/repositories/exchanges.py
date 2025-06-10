"""Repository for managing exchange operations in the database."""
import json
import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.constants import (
    BINANCE_MARKETS_KEY,
    KRAKEN_ACCOUNT_TYPE_KEY,
    USER_CREDENTIAL_MAPPING_KEYS,
)
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.types import ApiKey, ApiSecret, ExchangeApiCredentials, Location

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


log = logging.getLogger(__name__)


class ExchangeRepository:
    """Repository for handling all exchange-related operations."""

    def add(
            self,
            write_cursor: 'DBCursor',
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret | None,
            passphrase: str | None = None,
            kraken_account_type: KrakenAccountType | None = None,
            binance_selected_trade_pairs: list[str] | None = None,
    ) -> None:
        """Add a new exchange to the database."""
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {location!s}')

        write_cursor.execute(
            'INSERT INTO user_credentials '
            '(name, location, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?, ?)',
            (name, location.serialize_for_db(), api_key, api_secret.decode() if api_secret is not None else None, passphrase),  # noqa: E501
        )

        if location == Location.KRAKEN and kraken_account_type is not None:
            write_cursor.execute(
                'INSERT INTO user_credentials_mappings '
                '(credential_name, credential_location, setting_name, setting_value) '
                'VALUES (?, ?, ?, ?)',
                (name, location.serialize_for_db(), KRAKEN_ACCOUNT_TYPE_KEY, kraken_account_type.serialize()),  # noqa: E501
            )

        if location in (Location.BINANCE, Location.BINANCEUS) and binance_selected_trade_pairs is not None:  # noqa: E501
            self.set_binance_pairs(write_cursor, name=name, pairs=binance_selected_trade_pairs, location=location)  # noqa: E501

    def edit(
            self,
            write_cursor: 'DBCursor',
            name: str,
            location: Location,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_selected_trade_pairs: list[str] | None,
    ) -> None:
        """Edit an existing exchange in the database.

        May raise InputError if something is wrong with editing the DB
        """
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {location!s}')

        if any(x is not None for x in (new_name, passphrase, api_key, api_secret)):
            querystr = 'UPDATE user_credentials SET '
            bindings = []
            if new_name is not None:
                querystr += 'name=?,'
                bindings.append(new_name)
            if passphrase is not None:
                querystr += 'passphrase=?,'
                bindings.append(passphrase)
            if api_key is not None:
                querystr += 'api_key=?,'
                bindings.append(api_key)
            if api_secret is not None:
                querystr += 'api_secret=?,'
                bindings.append(api_secret.decode())

            if querystr[-1] == ',':
                querystr = querystr[:-1]

            querystr += ' WHERE name=? AND location=?;'
            bindings.extend([name, location.serialize_for_db()])

            try:
                write_cursor.execute(querystr, bindings)
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials due to {e!s}') from e

        if location == Location.KRAKEN and kraken_account_type is not None:
            try:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO user_credentials_mappings '
                    '(credential_name, credential_location, setting_name, setting_value) '
                    'VALUES (?, ?, ?, ?)',
                    (
                        new_name if new_name is not None else name,
                        location.serialize_for_db(),
                        KRAKEN_ACCOUNT_TYPE_KEY,
                        kraken_account_type.serialize(),
                    ),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials_mappings due to {e!s}') from e  # noqa: E501

        location_is_binance = location in (Location.BINANCE, Location.BINANCEUS)
        if location_is_binance and binance_selected_trade_pairs is not None:
            try:
                exchange_name = new_name if new_name is not None else name
                self.set_binance_pairs(write_cursor, name=exchange_name, pairs=binance_selected_trade_pairs, location=location)  # noqa: E501
                # Also delete used query ranges to allow fetching missing trades
                # from the possible new pairs
                write_cursor.execute(
                    'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
                    (f'{location!s}\\_history_events_\\_{name}', '\\'),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials_mappings due to {e!s}') from e  # noqa: E501

        if new_name is not None:
            exchange_re = re.compile(r'(.*?)_(margins|history_events).*')
            used_ranges = write_cursor.execute(
                'SELECT * from used_query_ranges WHERE name LIKE ?',
                (f'{location!s}_%_{name}',),
            )
            entry_types = set()
            for used_range in used_ranges:
                range_name = used_range[0]
                match = exchange_re.search(range_name)
                if match is None:
                    continue
                entry_types.add(match.group(2))
            write_cursor.executemany(
                'UPDATE used_query_ranges SET name=? WHERE name=?',
                [
                    (f'{location!s}_{entry_type}_{new_name}', f'{location!s}_{entry_type}_{name}')
                    for entry_type in entry_types
                ],
            )

            # also update the name of the events related to this exchange
            write_cursor.execute(
                'UPDATE history_events SET location_label=? WHERE location=? AND location_label=?',
                (new_name, location.serialize_for_db(), name),
            )

    def remove(self, write_cursor: 'DBCursor', name: str, location: Location) -> None:
        """
        Removes the exchange location from user_credentials and from
        `the non_syncing_exchanges`setting.
        """
        write_cursor.execute(
            'DELETE FROM user_credentials WHERE name=? AND location=?',
            (name, location.serialize_for_db()),
        )

    def get_credentials(
            self,
            cursor: 'DBCursor',
            location: Location | None = None,
            name: str | None = None,
    ) -> dict[Location, list[ExchangeApiCredentials]]:
        """Gets all exchange credentials

        If an exchange name and location are passed the credentials are filtered further
        """
        bindings = ()
        querystr = 'SELECT name, location, api_key, api_secret, passphrase FROM user_credentials'
        if name is not None and location is not None:
            querystr += ' WHERE name=? and location=?'
            bindings = (name, location.serialize_for_db())  # type: ignore
        querystr += ';'
        result = cursor.execute(querystr, bindings)
        credentials = defaultdict(list)
        for entry in result:
            if entry[0] == 'rotkehlchen':
                continue

            passphrase = None if entry[4] is None else entry[4]
            try:
                location = Location.deserialize_from_db(entry[1])
            except DeserializationError as e:
                log.error(
                    f'Found unknown location {entry[1]} for exchange {entry[0]} at '
                    f'get_exchange_credentials. This could mean that you are opening '
                    f'the app with an older version. {e!s}',
                )
                continue

            if location not in SUPPORTED_EXCHANGES:
                continue

            credentials[location].append(ExchangeApiCredentials(
                name=entry[0],
                location=location,
                api_key=ApiKey(entry[2]),
                api_secret=ApiSecret(str.encode(entry[3])) if entry[3] is not None else None,
                passphrase=passphrase,
            ))

        return credentials

    def get_credentials_extras(
            self, cursor: 'DBCursor', name: str, location: Location,
    ) -> dict[str, Any]:
        """Get the non-key credential extras for the given exchange location

        These are exchange dependent
        """
        cursor.execute(
            'SELECT setting_name, setting_value FROM user_credentials_mappings '
            'WHERE credential_name=? AND credential_location=?',
            (name, location.serialize_for_db()),
        )
        extras = {}
        for entry in cursor:
            if entry[0] not in USER_CREDENTIAL_MAPPING_KEYS:
                log.error(
                    f'Unknown credential setting {entry[0]} found in the DB. Skipping.',
                )
                continue

            key = entry[0]
            if key == KRAKEN_ACCOUNT_TYPE_KEY:
                try:
                    extras[key] = KrakenAccountType.deserialize(entry[1])
                except DeserializationError as e:
                    log.error(f'Couldnt deserialize kraken account type from DB. {e!s}')
            else:  # can only be BINANCE_MARKETS_KEY
                try:
                    extras[key] = json.loads(entry[1])
                except json.JSONDecodeError as e:
                    log.error(f'Could not deserialize binance markets from DB. {e!s}')

        return extras

    def set_binance_pairs(self, write_cursor: 'DBCursor', name: str, pairs: list[str], location: Location) -> None:  # noqa: E501
        """Set the binance pairs for the given account"""
        data = json.dumps(pairs)
        write_cursor.execute(
            'INSERT OR REPLACE INTO user_credentials_mappings '
            '(credential_name, credential_location, setting_name, setting_value) '
            'VALUES (?, ?, ?, ?)',
            (
                name,
                location.serialize_for_db(),
                BINANCE_MARKETS_KEY,
                data,
            ),
        )

    def get_binance_pairs(self, cursor: 'DBCursor', name: str, location: Location) -> list[str]:
        """Get the binance pairs for the given account"""
        cursor.execute(
            'SELECT setting_value '
            'FROM user_credentials_mappings '
            'WHERE credential_name=? AND credential_location=? AND setting_name=?',
            (name, location.serialize_for_db(), BINANCE_MARKETS_KEY),
        )
        result = cursor.fetchone()
        if result is None:
            return []

        try:
            return json.loads(result[0])
        except json.JSONDecodeError as e:
            log.error(f'Could not deserialize binance markets from DB. {e!s}')
            return []

    def delete_used_query_range(
            self,
            write_cursor: 'DBCursor',
            name: str,
            location: Location,
            ranges_to_query: list[str],
    ) -> None:
        """Delete used query ranges for an exchange

        Takes a list of query range names that relate to this exchange
        e.g. ['history', 'history_events']
        """
        for query in ranges_to_query:
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name=?;',
                (f'{location!s}_{query}_{name}',),
            )

    def purge_exchange_data(self, write_cursor: 'DBCursor', location: Location) -> None:
        """Deletes all exchange related data for the given exchange"""
        # Delete exchange specific used_query_ranges
        names_to_delete = f'{location!s}\\_%'
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (names_to_delete, '\\'),
        )
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?;',
            (names_to_delete, '\\'),
        )

        # Delete all exchange history events
        serialized_location = location.serialize_for_db()
        write_cursor.execute('DELETE FROM history_events WHERE location = ?;', (serialized_location,))  # noqa: E501
