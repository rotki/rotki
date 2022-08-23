from typing import TYPE_CHECKING, Dict, List, Optional, Union

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


class DBEns:

    def __init__(self, db_handler: 'DBHandler') -> None:
        self.db = db_handler

    def add_ens_mapping(    # pylint: disable=no-self-use
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            name: Optional[str],
            now: Timestamp,
    ) -> None:
        """Adds an ens mapping to the DB for an address

        If the name is None then it sets it as an empty name to the DB, signifying we checked it
        If the mapping already exists, but name is updated then we update the name + time

        May raise:
        """
        write_cursor.execute(
            'INSERT INTO ens_mappings (ens_name, address, last_update) '
            'VALUES (?, ?, ?) ON CONFLICT(address) '
            'DO UPDATE SET ens_name=excluded.ens_name, last_update=excluded.last_update; ',
            (name, address, now),
        )

    def get_reverse_ens(    # pylint: disable=no-self-use
            self,
            cursor: 'DBCursor',
            addresses: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, Union[EnsMapping, Timestamp]]:
        """Returns a mapping of addresses to ens mappings if found in the DB

        - If the address has a name mapping in the DB it is returned as part of the dict
        - If the address maps to None in the DB then address maps to last update in return dict
        - If address is not found in the DB it's not in the result
        """
        cursor.execute(
            f'SELECT ens_name, address, last_update FROM ens_mappings WHERE address IN ({",".join("?"*len(addresses))})',  # noqa: E501
            addresses,
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

    def update_values(
            self,
            write_cursor: 'DBCursor',
            ens_lookup_results: Dict[ChecksumEvmAddress, Optional[str]],
            mappings_to_send: Dict[ChecksumEvmAddress, str],
    ) -> Dict[ChecksumEvmAddress, str]:
        """Update the ENS mapping values in the DB and return updates mappings to return via api"""
        now = ts_now()
        for address, name in ens_lookup_results.items():
            try:
                self.add_ens_mapping(write_cursor, address=address, name=name, now=now)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                # Means that we have an old name mapping in the DB which has by now expired
                cursor = self.db.conn.cursor()
                cursor.execute('DELETE FROM ens_mappings WHERE ens_name=?', (name,))
                self.add_ens_mapping(write_cursor, address=address, name=name, now=now)

            if name is not None:
                mappings_to_send[address] = name

        return mappings_to_send
