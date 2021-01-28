from typing import Dict, List, Optional

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import InputError
from rotkehlchen.typing import AVAILABLE_MODULES_MAP, ChecksumAddress, ModuleName


class QueriedAddresses():

    def __init__(self, database: DBHandler):
        self.db = database

    def add_queried_address_for_module(self, module: ModuleName, address: ChecksumAddress) -> None:
        """May raise:
        - InputError: If the address is already in the queried addresses for
        the module
        """
        cursor = self.db.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO multisettings(name, value) VALUES(?, ?)',
                (f'queried_address_{module}', address),
            )
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            raise InputError(
                f'Address {address} is already in the queried addresses for {module}',
            ) from e
        self.db.conn.commit()
        self.db.update_last_write()

    def remove_queried_address_for_module(
            self,
            module: ModuleName,
            address: ChecksumAddress,
    ) -> None:
        """May raise:
        - InputError: If the address is not in the queried addresses for
        the module
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            'DELETE FROM multisettings WHERE name=? AND value=?;',
            (f'queried_address_{module}', address),
        )
        if cursor.rowcount != 1:
            raise InputError(f'Address {address} is not in the queried addresses for {module}')
        self.db.conn.commit()
        self.db.update_last_write()

    def get_queried_addresses_for_module(
            self,
            module: ModuleName,
    ) -> Optional[List[ChecksumAddress]]:
        """Get a List of addresses to query for module or None if none is set"""
        cursor = self.db.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM multisettings WHERE name=?;',
            (f'queried_address_{module}',),
        )
        result = [entry[0] for entry in query]
        return None if len(result) == 0 else result

    def get_queried_addresses_per_module(self) -> Dict[ModuleName, List[ChecksumAddress]]:
        """Get a mapping of modules to addresses to query for that module"""
        mapping: Dict[ModuleName, List[ChecksumAddress]] = {}
        for module in AVAILABLE_MODULES_MAP:
            result = self.get_queried_addresses_for_module(module)  # type: ignore
            if result is not None:
                mapping[module] = result  # type: ignore

        return mapping
