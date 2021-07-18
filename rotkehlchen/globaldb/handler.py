import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast, overload

from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset, EthereumToken, UnderlyingToken
from rotkehlchen.assets.typing import AssetData, AssetType
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.assets import CONSTANT_ASSETS
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors import DeserializationError, InputError, UnknownAsset
from rotkehlchen.globaldb.upgrades.v1_v2 import upgrade_ethereum_asset_ids
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.typing import ChecksumEthAddress, Timestamp

from .schema import DB_SCRIPT_CREATE_TABLES

log = logging.getLogger(__name__)

GLOBAL_DB_VERSION = 2


def _get_setting_value(cursor: sqlite3.Cursor, name: str, default_value: int) -> int:
    query = cursor.execute(
        'SELECT value FROM settings WHERE name=?;', (name,),
    )
    result = query.fetchall()
    # If setting is not set, it's the default
    if len(result) == 0:
        return default_value

    return int(result[0][0])


def initialize_globaldb(dbpath: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(dbpath)
    connection.executescript(DB_SCRIPT_CREATE_TABLES)
    cursor = connection.cursor()
    db_version = _get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)
    if db_version > GLOBAL_DB_VERSION:
        raise ValueError(
            f'Tried to open a rotki version intended to work with GlobalDB v{GLOBAL_DB_VERSION} '
            f'but the GlobalDB found in the system is v{db_version}. Bailing ...',
        )

    if db_version == 1:
        upgrade_ethereum_asset_ids(connection)
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(GLOBAL_DB_VERSION)),
    )
    connection.commit()
    return connection


def _initialize_global_db_directory(data_dir: Path) -> sqlite3.Connection:
    global_dir = data_dir / 'global_data'
    global_dir.mkdir(parents=True, exist_ok=True)
    dbname = global_dir / 'global.db'
    if not dbname.is_file():
        # if no global db exists, copy the built-in file
        root_dir = Path(__file__).resolve().parent.parent
        builtin_data_dir = root_dir / 'data'
        shutil.copyfile(builtin_data_dir / 'global.db', global_dir / 'global.db')
    return initialize_globaldb(dbname)


class GlobalDBHandler():
    """A singleton class controlling the global DB"""
    __instance: Optional['GlobalDBHandler'] = None
    _data_directory: Optional[Path] = None
    _conn: sqlite3.Connection

    def __new__(
            cls,
            data_dir: Path = None,
    ) -> 'GlobalDBHandler':
        """
        Initializes the GlobalDB.

        If the data dir is given it uses the already existing global DB in that directory,
        of if there is none copies the built-in one there.
        """
        if GlobalDBHandler.__instance is not None:
            return GlobalDBHandler.__instance

        assert data_dir, 'First instantiation of GlobalDBHandler should have a data_dir'
        GlobalDBHandler.__instance = object.__new__(cls)
        GlobalDBHandler.__instance._data_directory = data_dir
        GlobalDBHandler.__instance._conn = _initialize_global_db_directory(data_dir)
        _reload_constant_assets(GlobalDBHandler.__instance)
        return GlobalDBHandler.__instance

    @staticmethod
    def get_schema_version() -> int:
        """Get the version of the DB Schema"""
        cursor = GlobalDBHandler()._conn.cursor()
        return _get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)

    @staticmethod
    def get_setting_value(name: str, default_value: int) -> int:
        """Get the value of a setting or default. Typing is always int for now"""
        cursor = GlobalDBHandler()._conn.cursor()
        return _get_setting_value(cursor, name, default_value)

    @staticmethod
    def add_setting_value(name: str, value: Any, commit: bool = True) -> None:
        """Add the value of a setting"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (name, str(value)),
        )
        if commit:
            connection.commit()

    @staticmethod
    def add_asset(
            asset_id: str,
            asset_type: AssetType,
            data: Union[EthereumToken, Dict[str, Any]],
    ) -> None:
        """
        Add an asset in the DB. Either an ethereum token or a custom asset.

        If it's a custom asset the data should be typed. As given in by marshmallow.

        May raise InputError in case of error, meaning asset exists or some constraint hit"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()

        details_id: Union[str, ChecksumEthAddress]
        if asset_type == AssetType.ETHEREUM_TOKEN:
            token = cast(EthereumToken, data)
            GlobalDBHandler().add_ethereum_token_data(token)
            details_id = token.ethereum_address
            name = token.name
            symbol = token.symbol
            started = token.started
            swapped_for = token.swapped_for.identifier if token.swapped_for else None
            coingecko = token.coingecko
            cryptocompare = token.cryptocompare
        else:
            details_id = asset_id
            data = cast(Dict[str, Any], data)
            # The data should already be typed (as given in by marshmallow)
            name = data.get('name', None)
            symbol = data.get('symbol', None)
            started = data.get('started', None)
            swapped_for_asset = data.get('swapped_for', None)
            swapped_for = swapped_for_asset.identifier if swapped_for_asset else None
            coingecko = data.get('coingecko', None)
            cryptocompare = data.get('cryptocompare', '')

        try:
            cursor.execute(
                'INSERT INTO assets('
                'identifier, type, name, symbol, started, swapped_for, '
                'coingecko, cryptocompare, details_reference) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    asset_id,
                    asset_type.serialize_for_db(),
                    name,
                    symbol,
                    started,
                    swapped_for,
                    coingecko,
                    cryptocompare,
                    details_id),
            )
        except sqlite3.IntegrityError as e:
            connection.rollback()
            raise InputError(
                f'Failed to add asset {asset_id} into the assets table for details id {details_id} due to {str(e)}',  # noqa: E501
            ) from e

        # for common asset details we have to add them after the addition of the main asset table
        if asset_type != AssetType.ETHEREUM_TOKEN:
            asset_data = cast(Dict[str, Any], data)
            asset_data['identifier'] = asset_id
            GlobalDBHandler().add_common_asset_details(asset_data)

        connection.commit()  # success

    @overload
    @staticmethod
    def get_all_asset_data(
            mapping: Literal[True],
            serialized: bool = False,
            specific_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        ...

    @overload
    @staticmethod
    def get_all_asset_data(
            mapping: Literal[False],
            serialized: bool = False,
            specific_ids: Optional[List[str]] = None,
    ) -> List[AssetData]:
        ...

    @staticmethod
    def get_all_asset_data(
            mapping: bool,
            serialized: bool = False,
            specific_ids: Optional[List[str]] = None,
    ) -> Union[List[AssetData], Dict[str, Dict[str, Any]]]:
        """Return all asset data from the DB or all data matching the given ids

        If mapping is True, return them as a Dict of identifier to data
        If mapping is False, return them as a List of AssetData
        """
        result: Union[List[AssetData], Dict[str, Dict[str, Any]]]
        if mapping:
            result = {}
        else:
            result = []
        cursor = GlobalDBHandler()._conn.cursor()
        specific_ids_query = ''
        if specific_ids is not None:
            specific_ids_query = f'AND A.identifier in ({",".join("?" * len(specific_ids))})'
        querystr = f"""
        SELECT A.identifier, A.type, B.address, B.decimals, A.name, A.symbol, A.started, null, A.swapped_for, A.coingecko, A.cryptocompare, B.protocol from assets as A LEFT OUTER JOIN ethereum_tokens as B
        ON B.address = A.details_reference WHERE A.type=? {specific_ids_query}
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, A.symbol, A.started, B.forked, A.swapped_for, A.coingecko, A.cryptocompare, null from assets as A LEFT OUTER JOIN common_asset_details as B
        ON B.asset_id = A.identifier WHERE A.type!=? {specific_ids_query};
        """  # noqa: E501
        eth_token_type = AssetType.ETHEREUM_TOKEN.serialize_for_db()    # pylint: disable=no-member
        if specific_ids is not None:
            bindings = (eth_token_type, *specific_ids, eth_token_type, *specific_ids)
        else:
            bindings = (eth_token_type, eth_token_type)
        query = cursor.execute(querystr, bindings)
        for entry in query:
            asset_type = AssetType.deserialize_from_db(entry[1])
            ethereum_address: Optional[ChecksumEthAddress]
            if asset_type == AssetType.ETHEREUM_TOKEN:
                ethereum_address = string_to_ethereum_address(entry[2])
            else:
                ethereum_address = None
            data = AssetData(
                identifier=entry[0],
                asset_type=asset_type,
                ethereum_address=ethereum_address,
                decimals=entry[3],
                name=entry[4],
                symbol=entry[5],
                started=entry[6],
                forked=entry[7],
                swapped_for=entry[8],
                coingecko=entry[9],
                cryptocompare=entry[10],
                protocol=entry[11],
            )
            if mapping:
                result[entry[0]] = data.serialize() if serialized else data  # type: ignore
            else:
                result.append(data)  # type: ignore

        return result

    @staticmethod
    def get_asset_data(
            identifier: str,
            form_with_incomplete_data: bool,
    ) -> Optional[AssetData]:
        """Get all details of a single asset by identifier

        Returns None if identifier can't be matched to an asset
        """
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT identifier, type, name, symbol, started, swapped_for, coingecko, '
            'cryptocompare, details_reference from assets WHERE identifier=?;',
            (identifier,),
        )
        result = query.fetchone()
        if result is None:
            return None

        # Since comparison is case insensitive let's return original identifier
        saved_identifier = result[0]  # get the identifier as saved in the DB.
        db_serialized_type = result[1]
        name = result[2]
        symbol = result[3]
        started = result[4]
        swapped_for = result[5]
        coingecko = result[6]
        cryptocompare = result[7]
        details_reference = result[8]
        forked = None
        decimals = None
        protocol = None
        ethereum_address = None

        try:
            asset_type = AssetType.deserialize_from_db(db_serialized_type)
        except DeserializationError as e:
            log.debug(
                f'Failed to read asset {identifier} from the DB due to '
                f'{str(e)}. Skipping',
            )
            return None

        if asset_type == AssetType.ETHEREUM_TOKEN:
            ethereum_address = details_reference
            cursor.execute(
                'SELECT decimals, protocol from ethereum_tokens '
                'WHERE address=?', (ethereum_address,),
            )
            result = query.fetchone()
            if result is None:
                log.error(
                    f'Found token {saved_identifier} in the DB assets table but not '
                    f'in the token details table.',
                )
                return None

            decimals = result[0]
            protocol = result[1]
            missing_basic_data = name is None or symbol is None or decimals is None
            if missing_basic_data and form_with_incomplete_data is False:
                log.debug(
                    f'Considering ethereum token with address {details_reference} '
                    f'as unknown since its missing either decimals or name or symbol',
                )
                return None
        else:
            cursor = GlobalDBHandler()._conn.cursor()
            query = cursor.execute(
                'SELECT forked FROM common_asset_details WHERE asset_id = ?;',
                (details_reference,),
            )
            result = query.fetchone()
            if result is None:
                log.error(
                    f'Found asset {saved_identifier} in the DB assets table but not '
                    f'in the common asset details table.',
                )
                return None
            forked = result[0]

        return AssetData(
            identifier=saved_identifier,
            name=name,
            symbol=symbol,
            asset_type=asset_type,
            started=started,
            forked=forked,
            swapped_for=swapped_for,
            ethereum_address=ethereum_address,
            decimals=decimals,
            coingecko=coingecko,
            cryptocompare=cryptocompare,
            protocol=protocol,
        )

    @staticmethod
    def fetch_underlying_tokens(
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
            connection: sqlite3.Connection,
            parent_token_address: ChecksumEthAddress,
            underlying_tokens: List[UnderlyingToken],
    ) -> None:
        """Add the underlying tokens for the parent token

        Passing in the connection so it can be rolled back in case of error
        """
        cursor = GlobalDBHandler()._conn.cursor()
        for underlying_token in underlying_tokens:
            # make sure underlying token address is tracked if not already there
            asset_id = GlobalDBHandler.get_ethereum_token_identifier(underlying_token.address)  # noqa: E501
            if asset_id is None:
                try:  # underlying token does not exist. Track it
                    cursor.execute(
                        'INSERT INTO ethereum_tokens(address) VALUES(?)',
                        (underlying_token.address,),
                    )
                    asset_id = ethaddress_to_identifier(underlying_token.address)
                    cursor.execute(
                        """INSERT INTO assets(identifier, type, name, symbol,
                        started, swapped_for, coingecko, cryptocompare, details_reference)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (asset_id, 'C', None, None, None,
                         None, None, '', underlying_token.address),
                    )
                except sqlite3.IntegrityError as e:
                    connection.rollback()
                    raise InputError(
                        f'Failed to add underlying tokens for {parent_token_address} '
                        f'due to {str(e)}',
                    ) from e
            try:
                cursor.execute(
                    'INSERT INTO underlying_tokens_list(address, weight, parent_token_entry) '
                    'VALUES(?, ?, ?)',
                    (
                        underlying_token.address,
                        str(underlying_token.weight),
                        parent_token_address,
                    ),
                )
            except sqlite3.IntegrityError as e:
                connection.rollback()
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
    def check_asset_exists(
            asset_type: AssetType,
            name: str,
            symbol: str,
    ) -> Optional[List[str]]:
        """Checks if an asset of a given type, symbol and name exists in the DB already

        For non ethereum tokens with no unique identifier like an address this is the
        only way to check if something already exists in the DB.

        If it exists it returns a list of the identifiers of the assets.
        """
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT identifier from assets WHERE type=? AND name=? AND symbol=?;',
            (asset_type.serialize_for_db(), name, symbol),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None

        return [x[0] for x in result]

    @staticmethod
    def get_ethereum_token(address: ChecksumEthAddress) -> Optional[EthereumToken]:  # noqa: E501
        """Gets all details for an ethereum token by its address

        If no token for the given address can be found None is returned.
        """
        cursor = GlobalDBHandler()._conn.cursor()
        query = cursor.execute(
            'SELECT A.identifier, B.address, B.decimals, A.name, A.symbol, A.started, '
            'A.swapped_for, A.coingecko, A.cryptocompare, B.protocol '
            'FROM ethereum_tokens AS B LEFT OUTER JOIN '
            'assets AS A ON B.address = A.details_reference WHERE address=?;',
            (address,),
        )
        results = query.fetchall()
        if len(results) == 0:
            return None

        token_data = results[0]
        underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(address)

        try:
            return EthereumToken.deserialize_from_db(
                entry=token_data,
                underlying_tokens=underlying_tokens,
            )
        except UnknownAsset as e:
            log.error(
                f'Found unknown swapped_for asset {str(e)} in '
                f'the DB when deserializing an EthereumToken',
            )
            return None

    @staticmethod
    def get_ethereum_tokens(
            exceptions: Optional[List[ChecksumEthAddress]] = None,
            protocol: Optional[str] = None,
    ) -> List[EthereumToken]:
        """Gets all ethereum tokens from the DB

        Can also accept filtering parameters.
        - List of addresses to ignore via exceptions
        - Protocol for which to return tokens
        """
        cursor = GlobalDBHandler()._conn.cursor()
        querystr = (
            'SELECT A.identifier, B.address, B.decimals, A.name, A.symbol, A.started, '
            'A.swapped_for, A.coingecko, A.cryptocompare, B.protocol '
            'FROM ethereum_tokens as B LEFT OUTER JOIN '
            'assets AS A on B.address = A.details_reference '
        )
        if exceptions is not None or protocol is not None:
            bindings_list: List[Union[str, ChecksumEthAddress]] = []
            querystr_additions = []
            if exceptions is not None:
                questionmarks = '?' * len(exceptions)
                querystr_additions.append(f'WHERE B.address NOT IN ({",".join(questionmarks)}) ')
                bindings_list.extend(exceptions)
            if protocol is not None:
                querystr_additions.append('WHERE B.protocol=? ')
                bindings_list.append(protocol)

            querystr += 'AND '.join(querystr_additions) + ';'
            bindings = tuple(bindings_list)
        else:
            querystr += ';'
            bindings = ()
        query = cursor.execute(querystr, bindings)
        tokens = []
        for entry in query:
            underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(entry[1])
            try:
                token = EthereumToken.deserialize_from_db(entry, underlying_tokens)  # noqa: E501
                tokens.append(token)
            except UnknownAsset as e:
                log.error(
                    f'Found unknown swapped_for asset {str(e)} in '
                    f'the DB when deserializing an EthereumToken',
                )

        return tokens

    @staticmethod
    def add_ethereum_token_data(entry: EthereumToken) -> None:
        """Adds ethereum token specific information into the global DB

        May raise InputError if the token already exists
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'INSERT INTO '
                'ethereum_tokens(address, decimals, protocol) '
                'VALUES(?, ?, ?)',
                (entry.ethereum_address, entry.decimals, entry.protocol),
            )
        except sqlite3.IntegrityError as e:
            exception_msg = str(e)
            if 'FOREIGN KEY' in exception_msg:
                # should not really happen since API should check for this
                msg = (
                    f'Ethereum token with address {entry.ethereum_address} can not be put '
                    f'in the DB due to swapped for entry not existing'
                )
            else:
                msg = f'Ethereum token with address {entry.ethereum_address} already exists in the DB'  # noqa: E501
            raise InputError(msg) from e

        if entry.underlying_tokens is not None:
            GlobalDBHandler()._add_underlying_tokens(
                connection=connection,
                parent_token_address=entry.ethereum_address,
                underlying_tokens=entry.underlying_tokens,
            )

    @staticmethod
    def edit_ethereum_token(
            entry: EthereumToken,
    ) -> str:
        """Edits an ethereum token entry in the DB

        May raise InputError if there is an error during updating

        Returns the token's rotki identifier
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'UPDATE assets SET name=?, symbol=?, started=?, swapped_for=?, '
                'coingecko=?, cryptocompare=? WHERE identifier=?;',
                (
                    entry.name,
                    entry.symbol,
                    entry.started,
                    entry.swapped_for.identifier if entry.swapped_for else None,
                    entry.coingecko,
                    entry.cryptocompare,
                    ethaddress_to_identifier(entry.ethereum_address),
                ),
            )
            cursor.execute(
                'UPDATE ethereum_tokens SET decimals=?, protocol=? WHERE address = ?',
                (entry.decimals, entry.protocol, entry.ethereum_address),
            )
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Failed to update DB entry for ethereum token with address {entry.ethereum_address} '  # noqa: E501
                f'due to a constraint being hit. Make sure the new values are valid ',
            ) from e

        if cursor.rowcount != 1:
            raise InputError(
                f'Tried to edit non existing ethereum token with address {entry.ethereum_address}',
            )

        # Since this is editing, make sure no underlying tokens exist
        cursor.execute(
            'DELETE from underlying_tokens_list WHERE parent_token_entry=?',
            (entry.ethereum_address,),
        )
        if entry.underlying_tokens is not None:  # and now add any if needed
            GlobalDBHandler()._add_underlying_tokens(
                connection=connection,
                parent_token_address=entry.ethereum_address,
                underlying_tokens=entry.underlying_tokens,
            )

        rotki_id = GlobalDBHandler().get_ethereum_token_identifier(entry.ethereum_address)
        if rotki_id is None:
            connection.rollback()
            raise InputError(
                f'Unexpected DB state. Ethereum token {entry.ethereum_address} exists in the DB '
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
        except sqlite3.IntegrityError as e:
            connection.rollback()
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'but its deletion would violate a constraint so deletion '
                f'failed. Make sure that this token is not already used by '
                f'other tokens as an underlying or swapped for token or is '
                f'not owned by any user in the same system rotki runs',
            ) from e

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
        try:
            cursor.execute(
                'DELETE FROM assets WHERE details_reference=?;',
                (address,),
            )
        except sqlite3.IntegrityError as e:
            connection.rollback()
            raise InputError(
                f'Tried to delete ethereum token with address {address} '
                f'but its deletion would violate a constraint so deletion '
                f'failed. Make sure that this token is not already used by '
                f'other tokens as an underlying or swapped for token',
            ) from e

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
    def edit_custom_asset(data: Dict[str, Any]) -> None:
        """Edits an already existing custom asset in the DB

        The data should already be typed (as given in by marshmallow).

        May raise InputError if the token already exists or other error

        Returns the asset's identifier
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()

        identifier = data['identifier']
        forked_asset = data.get('forked', None)
        forked = forked_asset.identifier if forked_asset else None
        swapped_for_asset = data.get('swapped_for', None)
        swapped_for = swapped_for_asset.identifier if swapped_for_asset else None
        try:
            cursor.execute(
                'UPDATE assets SET type=?, name=?, symbol=?, started=?, swapped_for=?, '
                'coingecko=?, cryptocompare=? WHERE identifier = ?',
                (
                    data['asset_type'].serialize_for_db(),
                    data.get('name'),
                    data.get('symbol'),
                    data.get('started'),
                    swapped_for,
                    data.get('coingecko'),
                    data.get('cryptocompare', ''),
                    identifier,
                ),
            )
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Failed to update DB entry for asset with identifier {identifier} '
                f'due to a constraint being hit. Make sure the new values are valid ',
            ) from e

        if cursor.rowcount != 1:
            raise InputError(
                f'Tried to edit non existing asset with identifier {identifier}',
            )

        # Edit the common asset details
        try:
            cursor.execute(
                'UPDATE common_asset_details SET forked=? WHERE asset_id=?',
                (forked, identifier),
            )
        except sqlite3.IntegrityError as e:
            connection.rollback()
            raise InputError(
                f'Failure at editing custom asset {identifier} common asset details',
            ) from e

        connection.commit()

    @staticmethod
    def add_common_asset_details(data: Dict[str, Any]) -> None:
        """Adds a new row in common asset details

        The data should already be typed (as given in by marshmallow).

        May raise InputError if the asset already exists

        Does not commit to the DB. Commit must be called from the caller.
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        # assuming they are already serialized
        asset_id = data['identifier']
        forked_asset = data.get('forked', None)
        forked = forked_asset.identifier if forked_asset else None
        try:
            cursor.execute(
                'INSERT INTO common_asset_details(asset_id, forked)'
                'VALUES(?, ?)',
                (asset_id, forked),
            )
        except sqlite3.IntegrityError as e:
            raise InputError(  # should not really happen, marshmallow should check forked for
                f'Adding common asset details for {asset_id} failed',
            ) from e

    @staticmethod
    def delete_custom_asset(identifier: str) -> None:
        """Deletes an asset (non-ethereum token) from the global DB

        May raise InputError if the asset does not exist in the DB or
        some other constraint is hit. Such as for example trying to delete
        an asset that is in another asset's forked or swapped attribute
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.execute(
                'DELETE FROM assets WHERE identifier=?;',
                (identifier,),
            )
        except sqlite3.IntegrityError as e:
            asset_data = GlobalDBHandler().get_asset_data(identifier, form_with_incomplete_data=False)  # noqa: E501
            if asset_data is None:
                details_str = f'asset with identifier {identifier}'
            else:
                details_str = (
                    f'asset with name "{asset_data.name}" and '
                    f'symbol "{asset_data.symbol}"'
                )
            raise InputError(
                f'Tried to delete {details_str} '
                f'but its deletion would violate a constraint so deletion '
                f'failed. Make sure that this asset is not already used by '
                f'other assets as a swapped_for or forked asset',
            ) from e

        affected_rows = cursor.rowcount
        if affected_rows != 1:
            raise InputError(
                f'Tried to delete asset with identifier {identifier} '
                f'but it was not found in the DB',
            )

        connection.commit()

    @staticmethod
    def add_user_owned_assets(assets: List['Asset']) -> None:
        """Make sure all assets in the list are included in the user owned assets

        These assets are there so that when someone tries to delete assets from the global DB
        they don't delete assets that are owned by any local user.
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.executemany(
                'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES(?)',
                [(x.identifier,) for x in assets],
            )
        except sqlite3.IntegrityError as e:
            log.error(
                f'One of the following asset ids caused a DB IntegrityError ({str(e)}): '
                f'{",".join([x.identifier for x in assets])}',
            )  # should not ever happen but need to handle with informative log if it does
            connection.rollback()
            return

        connection.commit()

    @staticmethod
    def delete_asset_by_identifer(identifier: str, asset_type: AssetType) -> None:
        """Delete an asset by identifier EVEN if it's in the owned assets table

        May raise InputError if there is a foreign key relation such as the asset
        is a swapped_for or forked_for of another asset.
        """
        globaldb = GlobalDBHandler()
        connection = globaldb._conn
        cursor = connection.cursor()
        cursor.execute('DELETE FROM user_owned_assets WHERE asset_id=?;', (identifier,))
        cursor.execute(
            'DELETE FROM price_history WHERE from_asset=? OR to_asset=? ;',
            (identifier, identifier),
        )

        try:
            if asset_type == AssetType.ETHEREUM_TOKEN:
                globaldb.delete_ethereum_token(identifier[6:])  # type: ignore
            else:
                globaldb.delete_custom_asset(identifier)
        except InputError:
            connection.rollback()
            raise

        connection.commit()

    @staticmethod
    def get_assets_with_symbol(symbol: str, asset_type: Optional[AssetType] = None) -> List[AssetData]:  # noqa: E501
        """Find all asset entries that have the given symbol"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        query_tuples: Union[Tuple[str, str, str, str], Tuple[str, str, str, str, str]]
        eth_token_type = AssetType.ETHEREUM_TOKEN.serialize_for_db()    # pylint: disable=no-member
        if asset_type is not None:
            asset_type_check = ' AND A.type=?'
            query_tuples = (symbol, eth_token_type, symbol, eth_token_type, asset_type.serialize_for_db())  # noqa: E501
        else:
            asset_type_check = ''
            query_tuples = (symbol, eth_token_type, symbol, eth_token_type)
        querystr = f"""
        SELECT A.identifier, A.type, B.address, B.decimals, A.name, A.symbol, A.started, null, A.swapped_for, A.coingecko, A.cryptocompare, B.protocol from assets as A LEFT OUTER JOIN ethereum_tokens as B
        ON B.address = A.details_reference WHERE A.symbol=? COLLATE NOCASE AND A.type=?
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, A.symbol, A.started, B.forked, A.swapped_for, A.coingecko, A.cryptocompare, null from assets as A LEFT OUTER JOIN common_asset_details as B
        ON B.asset_id = A.identifier WHERE A.symbol=? COLLATE NOCASE AND A.type!=?{asset_type_check};
        """  # noqa: E501
        query = cursor.execute(querystr, query_tuples)
        assets = []
        for entry in query:
            asset_type = AssetType.deserialize_from_db(entry[1])
            ethereum_address: Optional[ChecksumEthAddress]
            if asset_type == AssetType.ETHEREUM_TOKEN:
                ethereum_address = string_to_ethereum_address(entry[2])
            else:
                ethereum_address = None
            assets.append(AssetData(
                identifier=entry[0],
                asset_type=asset_type,
                ethereum_address=ethereum_address,
                decimals=entry[3],
                name=entry[4],
                symbol=entry[5],
                started=entry[6],
                forked=entry[7],
                swapped_for=entry[8],
                coingecko=entry[9],
                cryptocompare=entry[10],
                protocol=entry[11],
            ))

        return assets

    @staticmethod
    def get_historical_price(
            from_asset: 'Asset',
            to_asset: 'Asset',
            timestamp: Timestamp,
            max_seconds_distance: int,
            source: Optional[HistoricalPriceOracle] = None,
    ) -> Optional['HistoricalPrice']:
        """Gets the price around a particular timestamp

        If no price can be found returns None
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        querystr = (
            'SELECT from_asset, to_asset, source_type, timestamp, price FROM price_history '
            'WHERE from_asset=? AND to_asset=? AND ABS(timestamp - ?) <= ? '
        )
        querylist = [from_asset.identifier, to_asset.identifier, timestamp, max_seconds_distance]
        if source is not None:
            querystr += ' AND source_type=?'
            querylist.append(source.serialize_for_db())

        querystr += 'ORDER BY ABS(timestamp - ?) ASC LIMIT 1'
        querylist.append(timestamp)

        query = cursor.execute(querystr, tuple(querylist))
        result = query.fetchone()
        if result is None:
            return None

        return HistoricalPrice.deserialize_from_db(result)

    @staticmethod
    def add_historical_prices(entries: List['HistoricalPrice']) -> None:
        """Adds the given historical price entries in the DB

        If any addition causes a DB error it's skipped and an error is logged
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            cursor.executemany(
                """INSERT OR IGNORE INTO price_history(
                from_asset, to_asset, source_type, timestamp, price
                ) VALUES (?, ?, ?, ?, ?)
                """, [x.serialize_for_db() for x in entries],
            )
        except sqlite3.IntegrityError as e:
            connection.rollback()  # roll back any of the executemany that may have gone in
            log.error(
                f'One of the given historical price entries caused a DB error. {str(e)}. '
                f'Will attempt to input them one by one',
            )
            for entry in entries:
                try:
                    cursor.execute(
                        """INSERT OR IGNORE INTO price_history(
                        from_asset, to_asset, source_type, timestamp, price
                        ) VALUES (?, ?, ?, ?, ?)
                        """, entry.serialize_for_db(),
                    )
                except sqlite3.IntegrityError as e:
                    log.error(
                        f'Failed to add {str(entry)} due to {str(e)}. Skipping entry addition',
                    )

        connection.commit()

    @staticmethod
    def add_single_historical_price(entry: HistoricalPrice) -> bool:
        """
        Adds the given historical price entries in the DB.
        Returns True if the operation succeeded and False otherwise
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        try:
            serialized = entry.serialize_for_db()
            cursor.execute(
                """INSERT OR IGNORE INTO price_history(
                from_asset, to_asset, source_type, timestamp, price
                ) VALUES (?, ?, ?, ?, ?)
                """,
                serialized,
            )
        except sqlite3.IntegrityError as e:
            connection.rollback()
            log.error(
                f'Failed to add single historical price. {str(e)}. ',
            )
            return False
        # success
        connection.commit()
        return True

    @staticmethod
    def get_manual_prices(
        from_asset: Optional[Asset],
        to_asset: Optional[Asset],
    ) -> List[Dict[str, str]]:
        """Returns prices added to the database by the user for an asset"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        querystr = (
            'SELECT from_asset, to_asset, source_type, timestamp, price FROM price_history '
            'WHERE source_type=? '
        )
        # Start by adding the manual source type to the list of params
        params = [HistoricalPriceOracle.MANUAL.serialize_for_db()]  # pylint: disable=no-member
        if from_asset is not None:
            querystr += 'AND from_asset=? '
            params.append(from_asset.identifier)
        if to_asset is not None:
            querystr += 'AND to_asset=? '
            params.append(to_asset.identifier)
        querystr += 'ORDER BY timestamp'
        query = cursor.execute(querystr, tuple(params))
        return [
            {
                'from_asset': entry[0],
                'to_asset': entry[1],
                'timestamp': entry[3],
                'price': entry[4],
            }
            for entry in query
        ]

    @staticmethod
    def edit_manual_price(entry: HistoricalPrice) -> bool:
        """Edits a manually inserted historical price. Returns false if no row
        was updated and true otherwise.
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        querystr = (
            'UPDATE price_history SET price=? WHERE from_asset=? AND to_asset=? '
            'AND source_type=? AND timestamp=? '
        )
        entry_serialized = entry.serialize_for_db()
        # Price that is the last entry should be the first and the rest of the
        # positions are correct in the tuple
        params_update = entry_serialized[-1:] + entry_serialized[:-1]
        try:
            cursor.execute(querystr, params_update)
        except sqlite3.IntegrityError as e:
            connection.rollback()
            log.error(
                f'Failed to edit manual historical prices from {entry.from_asset} '
                f'to {entry.to_asset} at timestamp: {str(entry.timestamp)} due to {str(e)}',
            )
            return False

        if cursor.rowcount == 1:
            connection.commit()
            return True
        return False

    @staticmethod
    def delete_manual_price(
            from_asset: 'Asset',
            to_asset: 'Asset',
            timestamp: Timestamp,
    ) -> bool:
        """
        Deletes a manually inserted historical price given by its primary key.
        Returns True if one row was deleted and False otherwise
        """
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        querystr = (
            'DELETE FROM price_history WHERE from_asset=? AND to_asset=? '
            'AND timestamp=? AND source_type=?'
        )
        bindings = (
            from_asset.identifier,
            to_asset.identifier,
            timestamp,
            HistoricalPriceOracle.MANUAL.serialize_for_db(),  # pylint: disable=no-member
        )
        cursor.execute(querystr, bindings)
        if cursor.rowcount != 1:
            log.error(
                f'Failed to delete historical price from {from_asset} to {to_asset} '
                f'and timestamp: {str(timestamp)}.',
            )
            return False
        connection.commit()
        return True

    @staticmethod
    def delete_historical_prices(
            from_asset: 'Asset',
            to_asset: 'Asset',
            source: Optional[HistoricalPriceOracle] = None,
    ) -> None:
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        querystr = 'DELETE FROM price_history WHERE from_asset=? AND to_asset=?'
        query_list = [from_asset.identifier, to_asset.identifier]
        if source is not None:
            querystr += ' AND source_type=?'
            query_list.append(source.serialize_for_db())

        try:
            cursor.execute(querystr, tuple(query_list))
        except sqlite3.IntegrityError as e:
            connection.rollback()
            log.error(
                f'Failed to delete historical prices from {from_asset} to {to_asset} '
                f'and source: {str(source)} due to {str(e)}',
            )

        connection.commit()

    @staticmethod
    def get_historical_price_range(
            from_asset: 'Asset',
            to_asset: 'Asset',
            source: Optional[HistoricalPriceOracle] = None,
    ) -> Optional[Tuple[Timestamp, Timestamp]]:
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        querystr = 'SELECT MIN(timestamp), MAX(timestamp) FROM price_history WHERE from_asset=? AND to_asset=?'  # noqa: E501
        query_list = [from_asset.identifier, to_asset.identifier]
        if source is not None:
            querystr += ' AND source_type=?'
            query_list.append(source.serialize_for_db())

        query = cursor.execute(querystr, tuple(query_list))
        result = query.fetchone()
        if result is None or None in (result[0], result[1]):
            return None
        return result[0], result[1]

    @staticmethod
    def get_historical_price_data(source: HistoricalPriceOracle) -> List[Dict[str, Any]]:
        """Return a list of assets and first/last ts

        Only used by the API so just returning it as List of dicts from here"""
        connection = GlobalDBHandler()._conn
        cursor = connection.cursor()
        query = cursor.execute(
            'SELECT from_asset, to_asset, MIN(timestamp), MAX(timestamp) FROM '
            'price_history WHERE source_type=? GROUP BY from_asset, to_asset',
            (source.serialize_for_db(),),
        )
        return [
            {'from_asset': entry[0],
             'to_asset': entry[1],
             'from_timestamp': entry[2],
             'to_timestamp': entry[3],
             } for entry in query]


def _reload_constant_assets(globaldb: GlobalDBHandler) -> None:
    """Reloads the details of the constant declared assets after reading from the DB"""
    identifiers = [x.identifier for x in CONSTANT_ASSETS]
    db_data = globaldb.get_all_asset_data(mapping=True, serialized=False, specific_ids=identifiers)  # type: ignore  # noqa: E501

    for entry in CONSTANT_ASSETS:
        db_entry = db_data.get(entry.identifier)
        if db_entry is None:
            log.critical(
                f'Constant declared asset with id {entry.identifier} has no corresponding DB entry'
                f'. Skipping reload this asset from DB. Either old global DB or user deleted it.',
            )
            continue

        # TODO: Perhaps don't use frozen dataclasses? This setattr everywhere is ugly
        if entry.asset_type == AssetType.ETHEREUM_TOKEN:
            if db_entry.asset_type != AssetType.ETHEREUM_TOKEN:
                log.critical(
                    f'Constant declared token with id {entry.identifier} has a '
                    f'different type in the DB {db_entry.asset_type}. This should never happen. '
                    f'Skipping reloading this asset from DB. Did user mess with the DB?',
                )
                continue
            swapped_for = Asset(db_entry.swapped_for) if db_entry.swapped_for else None
            object.__setattr__(entry, 'name', db_entry.name)
            object.__setattr__(entry, 'symbol', db_entry.symbol)
            object.__setattr__(entry, 'started', db_entry.started)
            object.__setattr__(entry, 'swapped_for', swapped_for)
            object.__setattr__(entry, 'cryptocompare', db_entry.cryptocompare)
            object.__setattr__(entry, 'coingecko', db_entry.coingecko)
            object.__setattr__(entry, 'ethereum_address', db_entry.ethereum_address)
            object.__setattr__(entry, 'decimals', db_entry.decimals)
            object.__setattr__(entry, 'protocol', db_entry.protocol)
            # TODO: Not changing underlying tokens at the moment since none
            # of the constant ones have but perhaps in the future we should?
        else:
            if db_entry.asset_type == AssetType.ETHEREUM_TOKEN:
                log.critical(
                    f'Constant declared asset with id {entry.identifier} has an ethereum '
                    f'token type in the DB {db_entry.asset_type}. This should never happen. '
                    f'Skipping reloading this asset from DB. Did user mess with the DB?',
                )
                continue
            swapped_for = Asset(db_entry.swapped_for) if db_entry.swapped_for else None
            forked = Asset(db_entry.forked) if db_entry.forked else None
            object.__setattr__(entry, 'name', db_entry.name)
            object.__setattr__(entry, 'symbol', db_entry.symbol)
            object.__setattr__(entry, 'asset_type', db_entry.asset_type)
            object.__setattr__(entry, 'started', db_entry.started)
            object.__setattr__(entry, 'forked', forked)
            object.__setattr__(entry, 'swapped_for', swapped_for)
            object.__setattr__(entry, 'cryptocompare', db_entry.cryptocompare)
            object.__setattr__(entry, 'coingecko', db_entry.coingecko)
