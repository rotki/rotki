import sqlite3
from pathlib import Path
from typing import List, Optional

from rotkehlchen.chain.etherum.typing import CustomEthereumToken
from rotkehlchen.errors import InputError
from rotkehlchen.typing import ChecksumEthAddress

from .schema import DB_SCRIPT_CREATE_TABLES

GLOBAL_DB_VERSION = 1


class GlobalDBHandler():
    """A singleton class controlling the global DB"""
    __instance: Optional['GlobalDBHandler'] = None
    _data_directory: Path
    _conn: sqlite3.Connection

    def __new__(
            cls,
            data_dir: Path = None,
    ) -> 'GlobalDBHandler':
        if GlobalDBHandler.__instance is not None:
            return GlobalDBHandler.__instance

        assert data_dir, 'arguments should be given at the first instantiation'

        GlobalDBHandler.__instance = object.__new__(cls)

        GlobalDBHandler.__instance._data_directory = data_dir

        # Create global data directory if not existing
        global_dir = data_dir / 'global_data'
        global_dir.mkdir(parents=True, exist_ok=True)
        dbname = global_dir / 'global.db'
        # Initialize the DB
        connection = sqlite3.connect(dbname)
        connection.executescript(DB_SCRIPT_CREATE_TABLES)
        cursor = connection.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('version', str(GLOBAL_DB_VERSION)),
        )
        connection.commit()
        GlobalDBHandler.__instance._conn = connection
        return GlobalDBHandler.__instance

    @staticmethod
    def get_ethereum_token(address: ChecksumEthAddress) -> Optional[CustomEthereumToken]:
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT decimals, name, symbol, started, coingecko, cryptocompare '
            'FROM ethereum_tokens where address=?;',
            (address,),
        )
        results = query.fetchall()
        if len(results) == 0:
            return None

        return CustomEthereumToken.deserialize_from_db((address, *results[0]))

    @staticmethod
    def get_ethereum_tokens() -> List[CustomEthereumToken]:
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT address, decimals, name, symbol, started, coingecko, cryptocompare '
            'FROM ethereum_tokens?;',
        )
        tokens = []
        for entry in query:
            tokens.append(CustomEthereumToken.deserialize_from_db(entry))

        return tokens

    @staticmethod
    def add_ethereum_token(
            entry: CustomEthereumToken,
    ) -> None:
        """Adds a new ethereum token into the global DB

        May raise InputError if the token already exists
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO '
                'ethereum_tokens(address, decimals, name, symbol, '
                'started, coingecko, cryptocompare) '
                'VALUES(?, ?, ?, ?, ?, ?, ?)',
                entry.to_db_tuple(),
            )
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Ethereum token with address {entry.address} already exists in the DB',
            ) from e
        connection.commit()

    @staticmethod
    def edit_ethereum_token(
            entry: CustomEthereumToken,
    ) -> None:
        """Adds a new ethereum token into the global DB

        May raise InputError if the token already exists
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        db_tuple = entry.to_db_tuple()
        swapped_tuple = (*db_tuple[1:], db_tuple[0])
        cursor.execute(
            'UPDATE ethereum_tokens SET decimals=?, name=?, symbol=?, started=?,'
            'coingecko=?, cryptocompare=? WHERE address = ?',
            swapped_tuple,
        )
        if cursor.rowcount != 1:
            raise InputError(
                f'Tried to edit non existing ethereum token with address {entry.address}',
            )
        connection.commit()

    @staticmethod
    def delete_ethereum_token(address: ChecksumEthAddress) -> None:
        """Deletes an ethereum token from the global DB

        May raise InputError if the token does not exist in the DB
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        cursor.execute(
            'DELETE FROM ethereum_tokens WHERE address=?;',
            (address,),
        )
        affected_rows = cursor.rowcount
        if affected_rows != 1:
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'but it was not found in the DB',
            )
        connection.commit()
