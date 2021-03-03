import sqlite3
from pathlib import Path
from typing import List, Optional

from rotkehlchen.chain.ethereum.typing import CustomEthereumToken, UnderlyingToken
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
    def _fetch_underlying_tokens(
            address: ChecksumEthAddress,
    ) -> Optional[List[UnderlyingToken]]:
        """Fetch underlying tokens for a token address if they exist"""
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT address, weight from underlying_tokens_list WHERE parent_token_entry=?;',
            (address,),
        )
        results = query.fetchall()
        underlying_tokens = None
        if len(results) != 0:
            underlying_tokens = [UnderlyingToken.deserialize_from_db(x) for x in results]

        return underlying_tokens

    @staticmethod
    def _add_underlying_tokens(
            parent_token_address: ChecksumEthAddress,
            underlying_tokens: List[UnderlyingToken],
    ) -> None:
        cursor = GlobalDBHandler()._conn.cursor()
        for underlying_token in underlying_tokens:
            # make sure underlying token address is tracked if not already there
            try:
                cursor.execute(
                    'INSERT INTO ethereum_tokens(address) VALUES(?)',
                    (underlying_token.address,),
                )
            except sqlite3.IntegrityError:
                pass  # already there

            try:
                cursor.execute(
                    'INSERT INTO underlying_tokens_list(address, weight, parent_token_entry) '
                    'VALUES(?, ?, ?)',
                    (underlying_token.address, str(underlying_token.weight), parent_token_address),
                )
            except sqlite3.IntegrityError as e:
                raise InputError(
                    f'Failed to add underlying tokens for {parent_token_address} due to {str(e)}',
                ) from e

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

        token_data = results[0]
        underlying_tokens = GlobalDBHandler()._fetch_underlying_tokens(address)
        return CustomEthereumToken.deserialize_from_db(
            entry=(address, *token_data),  # type: ignore
            underlying_tokens=underlying_tokens,
        )

    @staticmethod
    def get_ethereum_tokens() -> List[CustomEthereumToken]:
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT address, decimals, name, symbol, started, coingecko, cryptocompare '
            'FROM ethereum_tokens;',
        )
        tokens = []
        for entry in query:
            underlying_tokens = GlobalDBHandler()._fetch_underlying_tokens(entry[0])
            tokens.append(CustomEthereumToken.deserialize_from_db(entry, underlying_tokens))

        return tokens

    @staticmethod
    def add_ethereum_token(
            entry: CustomEthereumToken,
    ) -> str:
        """Adds a new ethereum token into the global DB

        May raise InputError if the token already exists

        Returns the token's rotki identifier
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'INSERT INTO '
                'ethereum_tokens(address, decimals, name, symbol, '
                'started, coingecko, cryptocompare) '
                'VALUES(?, ?, ?, ?, ?, ?, ?)',
                entry.to_db_tuple(),
            )
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Ethereum token with address {entry.address} already exists in the DB',
            ) from e

        if entry.underlying_tokens is not None:
            GlobalDBHandler()._add_underlying_tokens(
                parent_token_address=entry.address,
                underlying_tokens=entry.underlying_tokens,
            )

        connection.commit()
        return entry.identifier()

    @staticmethod
    def edit_ethereum_token(
            entry: CustomEthereumToken,
    ) -> str:
        """Adds a new ethereum token into the global DB

        May raise InputError if the token already exists

        Returns the token's rotki identifier
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

        # Since this is editing, make sure no underlying tokens exist
        cursor.execute(
            'DELETE from underlying_tokens_list WHERE parent_token_entry=?',
            (entry.address,),
        )
        if entry.underlying_tokens is not None:  # and now add any if needed
            GlobalDBHandler()._add_underlying_tokens(
                parent_token_address=entry.address,
                underlying_tokens=entry.underlying_tokens,
            )

        connection.commit()
        return entry.identifier()

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
