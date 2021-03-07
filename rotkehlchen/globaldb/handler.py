import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast, overload

from typing_extensions import Literal

from rotkehlchen.chain.ethereum.typing import (
    CustomEthereumToken,
    CustomEthereumTokenWithIdentifier,
    UnderlyingToken,
)
from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
from rotkehlchen.errors import (
    DeserializationError,
    InputError,
    ModuleInitializationFailure,
    UnknownAsset,
)
from rotkehlchen.typing import AssetData, AssetType, ChecksumEthAddress

from .schema import DB_SCRIPT_CREATE_TABLES

log = logging.getLogger(__name__)

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

        if data_dir is None:
            # Can happen in tests. And perhaps in an edge case when the resolver
            # tries to use the db handler before it's initialized with a data directory
            raise ModuleInitializationFailure(
                'GlobalDBHandler invoked before being primed with the data directory',
            )

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
    def get_setting_value(name: str, default_value: int) -> int:
        """Get the value of a setting or default. Typing is always int for now"""
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings WHERE name=?;', (name,),
        )
        result = query.fetchall()
        # If setting is not set, it's the default
        if len(result) == 0:
            return default_value

        return int(result[0][0])

    @staticmethod
    def add_setting_value(name: str, value: Any) -> None:
        """Add the value of a setting"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (name, str(value)),
        )
        connection.commit()

    @staticmethod
    def add_asset(
            asset_id: str,
            asset_type: AssetType,
            data: Union[CustomEthereumToken, Dict[str, Any]],
    ) -> None:
        """May raise InputError in case of error, meaning the asset exists"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()

        details_id: Union[str, ChecksumEthAddress]
        if asset_type == AssetType.ETHEREUM_TOKEN:
            token = cast(CustomEthereumToken, data)
            GlobalDBHandler().add_ethereum_token(token)
            details_id = token.address
        else:
            asset_data = cast(Dict[str, Any], data)
            asset_data['identifier'] = asset_id
            GlobalDBHandler().add_common_asset_details(asset_data)
            details_id = asset_id

        try:
            cursor.execute(
                'INSERT INTO assets(identifier, type, details_reference) '
                'VALUES(?, ?, ?)',
                (asset_id, asset_type.serialize_for_db(), details_id),
            )
        except sqlite3.IntegrityError as e:
            connection.rollback()
            raise InputError(
                f'Failed to add asset {asset_id} into the assets table for details id {details_id}',  # noqa: E501
            ) from e

        connection.commit()  # success

    @staticmethod
    def add_all_assets_from_json(
            ethereum_tokens: List[Dict[str, Any]],
            other_assets: List[Dict[str, Any]],
    ) -> None:
        """Attempts to add all assets from the lists to the all assets.json

        If an integrity error occurs then log it as an error and make sure nothing
        is inserted so we don't end up with a DB with incomplete state
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()

        # first add ethereum tokens to the assets table
        try:
            cursor.executemany(
                'INSERT OR IGNORE INTO assets(identifier, type, details_reference) '
                'VALUES(?, ?, ?)',
                [(x['identifier'], 'C', x['ethereum_address']) for x in ethereum_tokens],
            )
        except sqlite3.IntegrityError as e:
            log.error(
                f'Attempting to insert into assets table for tokens during global DB priming '
                f'encountered integrity error {str(e)}. Global DB is left unchanged',
            )
            connection.rollback()
            return

        # now other assets. First see which ones are already in the DB
        query = cursor.execute(
            f'SELECT identifier from assets WHERE identifier IN '
            f'({",".join("?" * len(other_assets))}) ',
            [x['identifier'] for x in other_assets],
        )
        result = query.fetchall()
        existing_ids = [x[0] for x in result]
        new_other_assets = [x for x in other_assets if x['identifier'] not in existing_ids]

        # and then add the new ones
        try:
            cursor.executemany(
                'INSERT OR IGNORE INTO assets(identifier, type, details_reference) '
                'VALUES(?, ?, ?)',
                [(
                    x['identifier'],
                    x['type'].serialize_for_db(),
                    x['identifier'],
                ) for idx, x in enumerate(new_other_assets)],
            )
        except sqlite3.IntegrityError as e:
            log.error(
                f'Attempting to insert into assets table for common assets during global DB '
                f'priming encountered integrity error {str(e)}. Global DB is left unchanged',
            )
            connection.rollback()
            return

        # At this point the assets DB table is populated for all assets. Time to add the details
        # First add the token details for all
        try:
            cursor.executemany(
                'INSERT OR IGNORE INTO ethereum_tokens(address, decimals, name, symbol, '
                'started, swapped_for, coingecko, cryptocompare, protocol) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [(
                    x['ethereum_address'],
                    x['ethereum_token_decimals'],
                    x['name'],
                    x['symbol'],
                    x.get('started', None),
                    x.get('swapped_for', None),
                    x.get('coingecko', None),
                    x.get('cryptocompare', None),
                    None,  # all_assets entries do not have a protocol as of yet
                ) for x in ethereum_tokens],
            )
        except sqlite3.IntegrityError as e:
            log.error(
                f'Attempting to insert into ethereum tokens table during global DB priming '
                f'encountered integrity error {str(e)}. Global DB is left unchanged',
            )
            connection.rollback()
            return

        # and finally add the common asset details for all
        try:
            cursor.executemany(
                'INSERT OR IGNORE INTO common_asset_details(asset_id, name, symbol, started, forked, '  # noqa: E501
                'swapped_for, coingecko, cryptocompare) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                [(
                    x['identifier'],
                    x['name'],
                    x['symbol'],
                    x.get('started', None),
                    x.get('forked', None),
                    x.get('swapped_for', None),
                    x.get('coingecko', None),
                    x.get('cryptocompare', None),
                ) for x in new_other_assets],
            )
        except sqlite3.IntegrityError as e:
            log.error(
                f'Attempting to insert into common asset details table during global DB '
                f'priming encountered integrity error {str(e)}. Global DB is left unchanged',
            )
            connection.rollback()
            return

        connection.commit()

    @staticmethod
    def get_asset_data(identifier: str, form_with_incomplete_data: bool = False) -> Optional[AssetData]:  # noqa: E501
        if identifier == 'XD':
            identifier = 'SCRL'  # https://github.com/rotki/rotki/issues/2503
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT identifier, type, details_reference from assets WHERE identifier=?;',
            (identifier,),
        )
        results = query.fetchall()
        if len(results) == 0:
            return None

        return GlobalDBHandler().get_asset_details(
            identifier=results[0][0],  # get the identifier in the exact case it's saved in the DB
            db_serialized_type=results[0][1],
            details_reference=results[0][2],
            form_with_incomplete_data=form_with_incomplete_data,
        )

    @overload
    @staticmethod
    def get_all_asset_data(mapping: Literal[True]) -> Dict[str, Dict[str, Any]]:
        ...

    @overload
    @staticmethod
    def get_all_asset_data(mapping: Literal[False]) -> List[AssetData]:
        ...

    @staticmethod
    def get_all_asset_data(mapping: bool) -> Union[List[AssetData], Dict[str, Dict[str, Any]]]:
        """Return all asset data from the DB

        TODO: This can be improved. Too many sql queries.

        If mapping is True, return them as a Dict of identifier to data
        If mapping is False, return them as a List of AssetData
        """
        result: Union[List[AssetData], Dict[str, Dict[str, Any]]]
        if mapping:
            result = {}
        else:
            result = []
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT identifier, type, details_reference from assets;',
        )
        for entry in query:
            data = GlobalDBHandler().get_asset_details(
                identifier=entry[0],
                db_serialized_type=entry[1],
                details_reference=entry[2],
                form_with_incomplete_data=False,
            )
            if data is None:
                continue
            if mapping:
                result[entry[0]] = data.serialize()  # type: ignore
            else:
                result.append(data)  # type: ignore

        return result

    @staticmethod
    def get_asset_details(
            identifier: str,
            db_serialized_type: str,
            details_reference: str,
            form_with_incomplete_data: bool,
    ) -> Optional[AssetData]:
        try:
            asset_type = AssetType.deserialize_from_db(db_serialized_type)
        except DeserializationError as e:
            log.debug(
                f'Failed to read asset {identifier} from the DB due to '
                f'{str(e)}. Skipping',
            )
            return None

        if asset_type == AssetType.ETHEREUM_TOKEN:
            address = cast(ChecksumEthAddress, details_reference)  # reference is an address
            token = GlobalDBHandler().get_ethereum_token(address)
            if token is None:
                log.error(
                    f'Found token {identifier} in the DB assets table but not '
                    f'in the token details table.',
                )
                return None

            if token.missing_basic_data() and form_with_incomplete_data is False:
                log.debug(
                    f'Considering ethereum token with address {address} '
                    f'as unknown since its missing either decimals or name or symbol',
                )
                return None

            return AssetData(
                identifier=identifier,
                name=token.name,  # type: ignore # check from missing_basic_data()
                symbol=token.symbol,  # type: ignore # check from missing_basic_data()
                active=True,
                asset_type=asset_type,
                started=token.started,
                ended=None,
                forked=None,
                swapped_for=token.swapped_for.identifier if token.swapped_for else None,
                ethereum_address=token.address,
                decimals=token.decimals,
                cryptocompare=token.cryptocompare,
                coingecko=token.coingecko,
            )

        # else
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT name, symbol, started, forked, swapped_for, coingecko, cryptocompare '
            'FROM common_asset_details WHERE asset_id = ?;',
            (details_reference,),
        )
        result = query.fetchall()
        if len(result) == 0:
            log.error(
                f'Found asset {identifier} in the DB assets table but not '
                f'in the common asset details table.',
            )
            return None

        result = result[0]
        return AssetData(
            identifier=identifier,
            name=result[0],
            symbol=result[1],
            active=True,
            asset_type=asset_type,
            started=result[2],
            ended=None,
            forked=result[3],
            swapped_for=result[4],
            ethereum_address=None,
            decimals=None,
            coingecko=result[5],
            cryptocompare=result[6],
        )

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
            asset_id = GlobalDBHandler.get_ethereum_token_identifier(underlying_token.address)
            if asset_id is None:
                try:  # underlying token does not exist. Track it
                    cursor.execute(
                        'INSERT INTO ethereum_tokens(address) VALUES(?)',
                        (underlying_token.address,),
                    )
                    asset_id = ETHEREUM_DIRECTIVE + underlying_token.address
                    cursor.execute(
                        'INSERT INTO assets(identifier, type, details_reference) '
                        'VALUES(?, ?, ?) ',
                        (asset_id, 'C', underlying_token.address),
                    )
                except sqlite3.IntegrityError as e:
                    raise InputError(
                        f'Failed to add underlying tokens for {parent_token_address} '
                        f'due to {str(e)}',
                    ) from e
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
    def get_ethereum_token_identifier(address: ChecksumEthAddress) -> Optional[str]:
        """Returns the asset identifier of an ethereum token by address if it can be found"""
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT A.identifier from assets AS A LEFT OUTER JOIN ethereum_tokens as B '
            ' ON B.address = A.details_reference WHERE b.address=?;',
            (address,),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None

        return result[0][0]

    @staticmethod
    def get_ethereum_token(address: ChecksumEthAddress) -> Optional[CustomEthereumTokenWithIdentifier]:  # noqa: E501
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT A.identifier, B.address, B.decimals, B.name, B.symbol, B.started, '
            'B.swapped_for, B.coingecko, B.cryptocompare, B.protocol '
            'FROM ethereum_tokens AS B LEFT OUTER JOIN '
            'assets AS A ON B.address = A.details_reference WHERE address=?;',
            (address,),
        )
        results = query.fetchall()
        if len(results) == 0:
            return None

        token_data = results[0]
        underlying_tokens = GlobalDBHandler()._fetch_underlying_tokens(address)

        try:
            return CustomEthereumTokenWithIdentifier.deserialize_from_db(
                entry=token_data,
                underlying_tokens=underlying_tokens,
            )
        except UnknownAsset as e:
            log.error(
                f'Found unknown swapped_for asset {str(e)} in '
                f'the DB when deserializing a CustomEthereumToken',
            )
            return None

    @staticmethod
    def get_ethereum_tokens() -> List[CustomEthereumTokenWithIdentifier]:
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT A.identifier, B.address, B.decimals, B.name, B.symbol, B.started, '
            'B.swapped_for, B.coingecko, B.cryptocompare, B.protocol '
            'FROM ethereum_tokens as B LEFT OUTER JOIN '
            'assets AS A on B.address = A.details_reference;',
        )
        tokens = []
        for entry in query:
            underlying_tokens = GlobalDBHandler()._fetch_underlying_tokens(entry[1])
            try:
                token = CustomEthereumTokenWithIdentifier.deserialize_from_db(entry, underlying_tokens)  # noqa: E501
                tokens.append(token)
            except UnknownAsset as e:
                log.error(
                    f'Found unknown swapped_for asset {str(e)} in '
                    f'the DB when deserializing a CustomEthereumTokenWithIdentifier',
                )

        return tokens

    @staticmethod
    def add_ethereum_token(entry: CustomEthereumToken) -> None:
        """Adds a new ethereum token into the global DB

        May raise InputError if the token already exists

        Returns the token's rotki identifier
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'INSERT INTO '
                'ethereum_tokens(address, decimals, name, symbol, started, '
                'swapped_for, coingecko, cryptocompare, protocol) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
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

    @staticmethod
    def edit_ethereum_token(
            entry: CustomEthereumToken,
    ) -> str:
        """Adds a new ethereum token into the global DB

        May raise InputError if the token already exists or other error

        Returns the token's rotki identifier
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        db_tuple = entry.to_db_tuple()
        swapped_tuple = (*db_tuple[1:], db_tuple[0])
        cursor.execute(
            'UPDATE ethereum_tokens SET decimals=?, name=?, symbol=?, started=?, swapped_for=?, '
            'coingecko=?, cryptocompare=?, protocol=? WHERE address = ?',
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

        rotki_id = GlobalDBHandler().get_ethereum_token_identifier(entry.address)
        if rotki_id is None:
            connection.rollback()
            raise InputError(
                f'Unexpected DB state. Ethereum token {entry.address} exists in the DB '
                f'but its corresponding asset entry was not found.',
            )

        connection.commit()
        return rotki_id

    @staticmethod
    def delete_ethereum_token(address: ChecksumEthAddress) -> str:
        """Deletes an ethereum token from the global DB

        May raise InputError if the token does not exist in the DB or
        some other constraint is hit. Such as for example trying to delete
        a token that is in another token's underlying tokens list.
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'DELETE FROM ethereum_tokens WHERE address=?;',
                (address,),
            )
        except sqlite3.IntegrityError:
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'but its deletion would violate a constraint so deletion '
                f'failed. Make sure that this token is not already used by '
                f'other tokens as an underlying or swapped for token',
            )

        affected_rows = cursor.rowcount
        if affected_rows != 1:
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'but it was not found in the DB',
            )

        # get the rotki identifier of the token
        query = cursor.execute(
            'SELECT identifier from assets where details_reference=?;',
            (address,),
        )
        result = query.fetchall()
        if len(result) == 0:
            connection.rollback()
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'from the assets table but it was not found in the DB',
            )
        rotki_id = result[0][0]

        # finally delete the assets entry
        cursor.execute(
            'DELETE FROM assets WHERE details_reference=?;',
            (address,),
        )
        affected_rows = cursor.rowcount
        if affected_rows != 1:
            connection.rollback()
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'from the assets table but it was not found in the DB',
            )

        connection.commit()
        return rotki_id

    @staticmethod
    def add_common_asset_details(data: Dict[str, Any]) -> None:
        """Adds a new row in common asset details

        May raise InputError if the token already exists

        Returns the stringified rowid of the entry
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        # assuming they are already serialized
        asset_id = data['identifier']
        entry_tuple = (
            asset_id,
            data['name'],
            data['symbol'],
            data.get('started', None),
            data.get('forked', None),
            data.get('swapped_for', None),
            data.get('coingecko', None),
            data.get('cryptocompare', None),
        )
        try:
            cursor.execute(
                'INSERT INTO common_asset_details('
                'asset_id, name, symbol, started, forked, '
                'swapped_for, coingecko, cryptocompare) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                entry_tuple,
            )
        except sqlite3.IntegrityError as e:
            raise InputError(  # should not really happen
                f'Adding common asset details for {asset_id} failed',
            ) from e
