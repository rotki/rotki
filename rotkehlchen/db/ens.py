from typing import TYPE_CHECKING

from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor


class DBEns:

    def __init__(self, db_handler: DBHandler) -> None:
        self.db = db_handler

    def add_ens_mapping(
            self,
            write_cursor: DBCursor,
            address: ChecksumEvmAddress,
            name: str | None,
            now: Timestamp,
            source: str = 'ens',
    ) -> None:
        """Adds a name mapping of the given naming system to the DB for an address

        If the name is None then it sets it as an empty name to the DB, signifying we checked it
        If the mapping already exists, but name is updated then we update the name + time

        May raise:
        """
        write_cursor.execute(
            'INSERT INTO ens_mappings (ens_name, address, last_update, source) '
            'VALUES (?, ?, ?, ?) ON CONFLICT(address, source) '
            'DO UPDATE SET ens_name=excluded.ens_name, last_update=excluded.last_update; ',
            (name, address, now, source),
        )

    def get_reverse_ens(
            self,
            cursor: DBCursor,
            addresses: list[ChecksumEvmAddress],
            source: str = 'ens',
    ) -> dict[ChecksumEvmAddress, EnsMapping | Timestamp]:
        """Returns a mapping of addresses to name mappings of the given naming
        system if found in the DB

        - If the address has a name mapping in the DB it is returned as part of the dict
        - If the address maps to None in the DB then address maps to last update in return dict
        - If address is not found in the DB it's not in the result
        """
        cursor.execute(
            f'SELECT ens_name, address, last_update FROM ens_mappings WHERE source=? AND address IN ({",".join("?" * len(addresses))})',  # noqa: E501
            [source, *addresses],
        )
        result = {}
        for ens_name, raw_address, last_update in cursor:
            address = ChecksumEvmAddress(raw_address)
            if ens_name is None:
                result[address] = last_update
            else:
                result[address] = EnsMapping(
                    address=address,
                    name=ens_name,
                    last_update=last_update,
                )

        return result

    def get_address_for_name(
            self,
            cursor: DBCursor,
            name: str,
    ) -> ChecksumEvmAddress | None:
        """Returns the address for the given name if cached"""
        cursor.execute('SELECT address FROM ens_mappings WHERE ens_name=?', (name,))
        if (result := cursor.fetchone()) is None:
            return None
        return result[0]

    def update_values(
            self,
            write_cursor: DBCursor,
            ens_lookup_results: dict[ChecksumEvmAddress, str | None],
            mappings_to_send: dict[ChecksumEvmAddress, str],
            source: str = 'ens',
    ) -> dict[ChecksumEvmAddress, str]:
        """Update the name mapping values in the DB and return updates mappings to return via api"""  # noqa: E501
        now = ts_now()
        for address, name in ens_lookup_results.items():
            try:
                self.add_ens_mapping(write_cursor, address=address, name=name, now=now, source=source)  # noqa: E501
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                # Means that we have an old name mapping in the DB which has by now expired
                with self.db.conn.cursor() as cursor:  # context-managed: a leaked cursor's GC finalization bypasses the driver's statement lock  # noqa: E501
                    cursor.execute('DELETE FROM ens_mappings WHERE ens_name=?', (name,))
                self.add_ens_mapping(write_cursor, address=address, name=name, now=now, source=source)  # noqa: E501

            if name is not None:
                mappings_to_send[address] = name

        return mappings_to_send

    def get_last_avatar_update(self, ens_name: str) -> Timestamp:
        """
        Returns the timestamp when the avatar for the given ens name was updated last time.
        May raise:
        - InputError if given `ens_name` is not in `ens_mappings` table
        """
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT last_avatar_update FROM ens_mappings WHERE ens_name=?',
                (ens_name,),
            ).fetchone()

        if result is None:
            raise InputError(f'ens name {ens_name} is not being tracked')

        return Timestamp(result[0])
