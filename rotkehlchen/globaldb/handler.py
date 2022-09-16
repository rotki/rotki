import logging
import shutil
import sqlite3
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
    overload,
)

from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import CONSTANT_ASSETS
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType, DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    GeneralCacheType,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

from .schema import DB_SCRIPT_CREATE_TABLES
from .upgrades.manager import maybe_upgrade_globaldb
from .utils import GLOBAL_DB_VERSION, _get_setting_value

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def initialize_globaldb(dbpath: Path, sql_vm_instructions_cb: int) -> DBConnection:
    connection = DBConnection(
        path=dbpath,
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )
    is_fresh_db = maybe_upgrade_globaldb(connection=connection, dbpath=dbpath)
    connection.executescript(DB_SCRIPT_CREATE_TABLES)
    if is_fresh_db is True:
        with connection.write_ctx() as cursor:
            cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('version', str(GLOBAL_DB_VERSION)),
            )
    connection.commit()
    return connection


def _initialize_global_db_directory(data_dir: Path, sql_vm_instructions_cb: int) -> DBConnection:
    global_dir = data_dir / 'global_data'
    global_dir.mkdir(parents=True, exist_ok=True)
    dbname = global_dir / 'global.db'
    if not dbname.is_file():
        # if no global db exists, copy the built-in file
        root_dir = Path(__file__).resolve().parent.parent
        builtin_data_dir = root_dir / 'data'
        shutil.copyfile(builtin_data_dir / 'global.db', global_dir / 'global.db')
    return initialize_globaldb(dbname, sql_vm_instructions_cb)


def _compute_cache_key(key_parts: Iterable[Union[str, GeneralCacheType]]) -> str:
    """Function to compute cache key before accessing globaldb cache.
    Computes cache key by iterating through `key_parts` and making one string from them.
    Only tuple with the same values and the same order represents the same key."""
    cache_key = ''
    for part in key_parts:
        if isinstance(part, GeneralCacheType):
            cache_key += part.serialize()
        else:
            cache_key += part
    return cache_key


class GlobalDBHandler():
    """A singleton class controlling the global DB"""
    __instance: Optional['GlobalDBHandler'] = None
    _data_directory: Optional[Path] = None
    conn: DBConnection

    def __new__(
            cls,
            data_dir: Path = None,
            sql_vm_instructions_cb: int = None,
    ) -> 'GlobalDBHandler':
        """
        Initializes the GlobalDB.

        If the data dir is given it uses the already existing global DB in that directory,
        of if there is none copies the built-in one there.
        """
        if GlobalDBHandler.__instance is not None:
            return GlobalDBHandler.__instance

        assert data_dir is not None, 'First instantiation of GlobalDBHandler should have a data_dir'  # noqa: E501
        assert sql_vm_instructions_cb is not None, 'First instantiation of GlobalDBHandler should have a sql_vm_instructions_cb'  # noqa: E501
        GlobalDBHandler.__instance = object.__new__(cls)
        GlobalDBHandler.__instance._data_directory = data_dir
        GlobalDBHandler.__instance.conn = _initialize_global_db_directory(data_dir, sql_vm_instructions_cb)  # noqa: E501
        _reload_constant_assets(GlobalDBHandler.__instance)
        return GlobalDBHandler.__instance

    @staticmethod
    def get_schema_version() -> int:
        """Get the version of the DB Schema"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            return _get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)

    @staticmethod
    def get_setting_value(name: str, default_value: int) -> int:
        """Get the value of a setting or default. Typing is always int for now"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            return _get_setting_value(cursor, name, default_value)

    @staticmethod
    def add_setting_value(name: str, value: Any) -> None:
        """Add the value of a setting"""
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                (name, str(value)),
            )

    @staticmethod
    def add_asset(
            asset_id: str,
            asset_type: AssetType,
            data: Union[EvmToken, Dict[str, Any]],
    ) -> None:
        """
        Add an asset in the DB. Either an ethereum token or a custom asset.

        If it's a custom asset the data should be typed. As given in by marshmallow.

        May raise InputError in case of error, meaning asset exists or some constraint hit"""
        if asset_type == AssetType.EVM_TOKEN:
            token = cast(EvmToken, data)
            forked_asset = token.forked
            name = token.name
            symbol = token.symbol
            started = token.started
            swapped_for = token.swapped_for.identifier if token.swapped_for else None
            coingecko = token.coingecko
            cryptocompare = token.cryptocompare
        else:
            token = None
            data = cast(Dict[str, Any], data)
            forked_asset = data.get('forked', None)
            # The data should already be typed (as given in by marshmallow)
            name = data.get('name', None)
            symbol = data.get('symbol', None)
            started = data.get('started', None)
            swapped_for_asset = data.get('swapped_for', None)
            swapped_for = swapped_for_asset.identifier if swapped_for_asset else None
            coingecko = data.get('coingecko', None)
            cryptocompare = data.get('cryptocompare', '')

        forked = forked_asset.identifier if forked_asset is not None else None
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT INTO assets(identifier, name, type, started, swapped_for) '
                    'VALUES(?, ?, ?, ?, ?);',
                    (
                        asset_id,
                        name,
                        asset_type.serialize_for_db(),
                        started,
                        swapped_for,
                    ),
                )
                if token is not None:
                    GlobalDBHandler.add_evm_token_data(write_cursor, token)
                write_cursor.execute(
                    'INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked)'  # noqa: E501
                    'VALUES(?, ?, ?, ?, ?);',
                    (
                        asset_id,
                        symbol,
                        coingecko,
                        cryptocompare,
                        forked,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Failed to add asset {asset_id} into the assets table due to {str(e)}',
            ) from e

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
        specific_ids_query = ''
        if specific_ids is not None:
            specific_ids_query = f'AND A.identifier in ({",".join("?" * len(specific_ids))})'
        querystr = f"""
        SELECT A.identifier, A.type, B.address, B.decimals, A.name, C.symbol, A.started, null, A.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain, B.token_kind FROM assets as A JOIN evm_tokens as B
        ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE A.type = '{AssetType.EVM_TOKEN.serialize_for_db()}' {specific_ids_query}
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, B.symbol, A.started, B.forked, A.swapped_for, B.coingecko, B.cryptocompare, null, null, null from assets as A JOIN common_asset_details as B
        ON B.identifier = A.identifier WHERE A.type != '{AssetType.EVM_TOKEN.serialize_for_db()}' {specific_ids_query};
        """  # noqa: E501
        if specific_ids is not None:
            bindings = (*specific_ids, *specific_ids)
        else:
            bindings = ()

        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(querystr, bindings)
            for entry in cursor:
                asset_type = AssetType.deserialize_from_db(entry[1])
                evm_address: Optional[ChecksumEvmAddress]
                if asset_type == AssetType.EVM_TOKEN:
                    evm_address = string_to_evm_address(entry[2])
                    chain = ChainID.deserialize_from_db(entry[12])
                    token_kind = EvmTokenKind.deserialize_from_db(entry[13])
                else:
                    evm_address, chain, token_kind = None, None, None
                data = AssetData(
                    identifier=entry[0],
                    asset_type=asset_type,
                    address=evm_address,
                    chain=chain,
                    token_kind=token_kind,
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
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT A.identifier, A.type, A.name, B.symbol, A.started, A.swapped_for, '
                'B.coingecko, B.cryptocompare, B.forked from assets AS A JOIN  '
                'common_asset_details AS B ON A.identifier = B.identifier WHERE A.identifier=?;',
                (identifier,),
            )
            result = cursor.fetchone()
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
            forked = result[8]
            decimals = None
            protocol = None
            evm_address = None
            chain = None
            token_kind = None

            try:
                asset_type = AssetType.deserialize_from_db(db_serialized_type)
            except DeserializationError as e:
                log.debug(
                    f'Failed to read asset {identifier} from the DB due to '
                    f'{str(e)}. Skipping',
                )
                return None

            if asset_type == AssetType.EVM_TOKEN:
                cursor.execute(
                    'SELECT decimals, protocol, address, chain, token_kind from evm_tokens '
                    'WHERE identifier=?', (saved_identifier,),
                )
                result = cursor.fetchone()
                if result is None:
                    log.error(
                        f'Found token {saved_identifier} in the DB assets table but not '
                        f'in the token details table.',
                    )
                    return None

                decimals = result[0]
                protocol = result[1]
                evm_address = result[2]
                chain = ChainID.deserialize_from_db(result[3])
                token_kind = EvmTokenKind.deserialize_from_db(result[4])
                missing_basic_data = name is None or symbol is None or decimals is None
                if missing_basic_data and form_with_incomplete_data is False:
                    log.debug(
                        f'Considering ethereum token with identifier {saved_identifier} '
                        f'as unknown since its missing either decimals or name or symbol',
                    )
                    return None

        return AssetData(
            identifier=saved_identifier,
            name=name,
            symbol=symbol,
            asset_type=asset_type,
            started=started,
            forked=forked,
            swapped_for=swapped_for,
            address=evm_address,
            chain=chain,
            token_kind=token_kind,
            decimals=decimals,
            coingecko=coingecko,
            cryptocompare=cryptocompare,
            protocol=protocol,
        )

    @staticmethod
    def fetch_underlying_tokens(
            cursor: DBCursor,
            parent_token_identifier: str,
    ) -> Optional[List[UnderlyingToken]]:
        """Fetch underlying tokens for a token address if they exist"""
        cursor.execute(
            'SELECT B.address, B.token_kind, A.weight FROM underlying_tokens_list AS A JOIN evm_tokens as B WHERE A.identifier=B.identifier AND parent_token_entry=?;',  # noqa: E501
            (parent_token_identifier,),
        )
        results = cursor.fetchall()
        underlying_tokens = None
        if len(results) != 0:
            underlying_tokens = [UnderlyingToken.deserialize_from_db(x) for x in results]

        return underlying_tokens

    @staticmethod
    def _add_underlying_tokens(
            write_cursor: DBCursor,
            parent_token_identifier: str,
            underlying_tokens: List[UnderlyingToken],
            chain: ChainID,
    ) -> None:
        """Add the underlying tokens for the parent token

        May raise InputError
        """
        for underlying_token in underlying_tokens:
            # make sure underlying token address is tracked if not already there
            asset_id = GlobalDBHandler.get_evm_token_identifier(
                cursor=write_cursor,
                address=underlying_token.address,
                chain=chain,
            )
            if asset_id is None:
                try:  # underlying token does not exist. Track it
                    asset_id = underlying_token.get_identifier(parent_chain=chain)
                    write_cursor.execute(
                        'INSERT INTO assets(identifier, name, type, started, swapped_for)'
                        'VALUES(?, ?, ?, ?, ?);',
                        (asset_id, None, AssetType.EVM_TOKEN.serialize_for_db(), None, None),
                    )
                    write_cursor.execute(
                        'INSERT INTO evm_tokens(identifier, address, chain, token_kind)'
                        'VALUES(?, ?, ?, ?)',
                        (
                            asset_id,
                            underlying_token.address,
                            chain.serialize_for_db(),
                            underlying_token.token_kind.serialize_for_db(),
                        ),
                    )
                    write_cursor.execute(
                        'INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked)'  # noqa: E501
                        'VALUES(?, ?, ?, ?, ?)',
                        (asset_id, None, None, '', None),
                    )
                except sqlite3.IntegrityError as e:
                    raise InputError(
                        f'Failed to add underlying tokens for {parent_token_identifier} '
                        f'due to {str(e)}',
                    ) from e
            try:
                write_cursor.execute(
                    'INSERT INTO underlying_tokens_list(identifier, weight, parent_token_entry) '
                    'VALUES(?, ?, ?)',
                    (
                        asset_id,
                        str(underlying_token.weight),
                        parent_token_identifier,
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise InputError(
                    f'Failed to add underlying tokens for {parent_token_identifier} '
                    f'due to {str(e)}',
                ) from e

    @staticmethod
    def get_evm_token_identifier(
            cursor: DBCursor,
            address: ChecksumEvmAddress,
            chain: ChainID,
    ) -> Optional[str]:
        """Returns the asset identifier of an EVM token by address if it can be found"""
        query = cursor.execute(
            'SELECT identifier from evm_tokens WHERE address=? AND chain=?;',
            (address, chain.serialize_for_db()),
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
        cursor = GlobalDBHandler().conn.cursor()
        query = cursor.execute(
            'SELECT A.identifier from assets AS A JOIN common_asset_details as C '
            'ON A.identifier=C.identifier WHERE A.type=? AND A.name=? AND C.symbol=?;',
            (asset_type.serialize_for_db(), name, symbol),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None

        return [x[0] for x in result]

    @staticmethod
    def get_evm_token(address: ChecksumEvmAddress, chain: ChainID) -> Optional[EvmToken]:
        """Gets all details for an evm token by its address

        If no token for the given address can be found None is returned.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT A.identifier, B.address, B.chain, B.token_kind, B.decimals, C.name, '
                'A.symbol, C.started, C.swapped_for, A.coingecko, A.cryptocompare, B.protocol '
                'FROM evm_tokens AS B JOIN '
                'common_asset_details AS A ON B.identifier = A.identifier '
                'JOIN assets AS C on C.identifier=A.identifier WHERE B.address=? AND B.chain=?;',
                (address, chain.serialize_for_db()),
            )
            results = cursor.fetchall()
            if len(results) == 0:
                return None

            token_data = results[0]
            underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(cursor, token_data[0])

        try:
            return EvmToken.deserialize_from_db(
                entry=token_data,
                underlying_tokens=underlying_tokens,
            )
        except UnknownAsset as e:
            log.error(
                f'Found unknown swapped_for asset {str(e)} in '
                f'the DB when deserializing an EvmToken',
            )
            return None

    @staticmethod
    def get_ethereum_tokens(
            exceptions: Optional[List[ChecksumEvmAddress]] = None,
            except_protocols: Optional[List[str]] = None,
            protocol: Optional[str] = None,
    ) -> List[EvmToken]:
        """Gets all ethereum tokens from the DB

        Can also accept filtering parameters.
        - List of addresses to ignore via exceptions
        - Protocol for which to return tokens
        """
        querystr = (
            'SELECT A.identifier, B.address,  B.chain, B.token_kind, B.decimals, A.name, '
            'C.symbol, A.started, A.swapped_for, C.coingecko, C.cryptocompare, B.protocol '
            'FROM evm_tokens as B LEFT OUTER JOIN '
            'assets AS A on B.identifier = A.identifier JOIN common_asset_details AS C ON '
            'C.identifier = B.identifier '
        )
        if exceptions is not None or protocol is not None or except_protocols is not None:
            bindings_list: List[Union[str, ChecksumEvmAddress]] = []
            querystr_additions = []
            if exceptions is not None:
                questionmarks = '?' * len(exceptions)
                querystr_additions.append(f'B.address NOT IN ({",".join(questionmarks)}) ')
                bindings_list.extend(exceptions)
            if protocol is not None:
                querystr_additions.append('B.protocol=? ')
                bindings_list.append(protocol)

            if except_protocols is not None:
                questionmarks = '?' * len(except_protocols)
                querystr_additions.append(f'(B.protocol NOT IN ({",".join(questionmarks)}) OR B.protocol IS NULL) ')  # noqa: E501
                bindings_list.extend(except_protocols)

            querystr += 'WHERE ' + 'AND '.join(querystr_additions) + ';'
            bindings = tuple(bindings_list)
        else:
            querystr += ';'
            bindings = ()

        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(querystr, bindings)
            tokens = []
            for entry in cursor:
                with GlobalDBHandler().conn.read_ctx() as other_cursor:
                    underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(other_cursor, entry[0])  # noqa: E501

                try:
                    token = EvmToken.deserialize_from_db(entry, underlying_tokens)  # noqa: E501
                    tokens.append(token)
                except UnknownAsset as e:
                    log.error(
                        f'Found unknown swapped_for asset {str(e)} in '
                        f'the DB when deserializing an EvmToken',
                    )

        return tokens

    @staticmethod
    def get_tokens_mappings(addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:  # noqa: E501
        """Gets mappings: address -> name for tokens whose address is in the provided list"""
        questionmarks = ','.join('?' * len(addresses))
        mappings = {}
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                f'SELECT evm_tokens.address, assets.name FROM evm_tokens INNER JOIN assets ON '
                f'evm_tokens.identifier = assets.identifier WHERE address IN ({questionmarks});',
                addresses,
            )
            for address, name in cursor:
                mappings[address] = name

        return mappings

    @staticmethod
    def add_evm_token_data(write_cursor: DBCursor, entry: EvmToken) -> None:
        """Adds ethereum token specific information into the global DB

        May raise InputError if the token already exists
        """
        try:
            write_cursor.execute(
                'INSERT INTO '
                'evm_tokens(identifier, token_kind, chain, address, decimals, protocol) '
                'VALUES(?, ?, ?, ?, ?, ?)',
                (
                    entry.identifier,
                    entry.token_kind.serialize_for_db(),
                    entry.chain.serialize_for_db(),
                    entry.evm_address,
                    entry.decimals,
                    entry.protocol,
                ),
            )
        except sqlite3.IntegrityError as e:
            exception_msg = str(e)
            if 'FOREIGN KEY' in exception_msg:
                # should not really happen since API should check for this
                msg = (
                    f'Ethereum token with address {entry.evm_address} can not be put '
                    f'in the DB due to asset with identifier {entry.identifier} dosent exist'
                )
            else:
                msg = f'Ethereum token with identifier {entry.identifier} already exists in the DB'  # noqa: E501
            raise InputError(msg) from e

        if entry.underlying_tokens is not None:
            GlobalDBHandler()._add_underlying_tokens(
                write_cursor=write_cursor,
                parent_token_identifier=entry.identifier,
                underlying_tokens=entry.underlying_tokens,
                chain=entry.chain,
            )

    @staticmethod
    def edit_evm_token(entry: EvmToken) -> str:
        """Edits an EVM token entry in the DB

        May raise InputError if there is an error during updating

        Returns the token's rotki identifier
        """
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'UPDATE common_asset_details SET symbol=?, coingecko=?, '
                    'cryptocompare=?, forked=? WHERE identifier=?;',
                    (
                        entry.symbol,
                        entry.coingecko,
                        entry.cryptocompare,
                        entry.forked.identifier if entry.forked else None,
                        entry.identifier,
                    ),
                )
                write_cursor.execute(
                    'UPDATE assets SET name=?, started=?, swapped_for=? WHERE identifier=?;',
                    (
                        entry.name,
                        entry.started,
                        entry.swapped_for.identifier if entry.swapped_for else None,
                        entry.identifier,
                    ),
                )
                write_cursor.execute(
                    'UPDATE evm_tokens SET token_kind=?, chain=?, address=?, decimals=?, '
                    'protocol=? WHERE identifier=?',
                    (
                        entry.token_kind.serialize_for_db(),
                        entry.chain.serialize_for_db(),
                        entry.evm_address,
                        entry.decimals,
                        entry.protocol,
                        entry.identifier,
                    ),
                )
                if write_cursor.rowcount != 1:
                    raise InputError(
                        f'Tried to edit non existing EVM token with address {entry.evm_address} at chain {entry.chain}',  # noqa: E501
                    )

                # Since this is editing, make sure no underlying tokens exist
                write_cursor.execute(
                    'DELETE from underlying_tokens_list WHERE parent_token_entry=?',
                    (entry.identifier,),
                )
                if entry.underlying_tokens is not None:  # and now add any if needed
                    GlobalDBHandler()._add_underlying_tokens(
                        write_cursor=write_cursor,
                        parent_token_identifier=entry.identifier,
                        underlying_tokens=entry.underlying_tokens,
                        chain=entry.chain,
                    )

                rotki_id = GlobalDBHandler().get_evm_token_identifier(write_cursor, entry.evm_address, entry.chain)  # noqa: E501
                if rotki_id is None:
                    raise InputError(
                        f'Unexpected DB state. EVM token {entry.evm_address} at chain '
                        f'{entry.chain} exists in the DB but its corresponding asset '
                        f'entry was not found.',
                    )

        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Failed to update DB entry for EVM token with address {entry.evm_address} at chain {entry.chain}'  # noqa: E501
                f'due to a constraint being hit. Make sure the new values are valid ',
            ) from e

        return rotki_id

    @staticmethod
    def delete_evm_token(
            write_cursor: DBCursor,
            address: ChecksumEvmAddress,
            chain: ChainID,
    ) -> str:
        """Deletes an EVM token from the global DB

        May raise InputError if the token does not exist in the DB.
        """
        # first get the identifier for the asset
        write_cursor.execute(
            'SELECT identifier from evm_tokens WHERE address=? AND chain=?',
            (address, chain.serialize_for_db()),
        )
        result = write_cursor.fetchone()
        if result is None:
            raise InputError(
                f'Tried to delete EVM token with address {address} at chain {chain} '
                f'but it was not found in the DB',
            )
        asset_identifier = result[0]
        GlobalDBHandler().delete_asset_by_identifier(asset_identifier)
        return asset_identifier

    @staticmethod
    def edit_custom_asset(data: Dict[str, Any]) -> None:
        """Edits an already existing custom asset in the DB

        The data should already be typed (as given in by marshmallow).

        May raise InputError if the token already exists or other error

        Returns the asset's identifier
        """
        identifier = data['identifier']
        forked_asset = data.get('forked', None)
        forked = forked_asset.identifier if forked_asset else None
        swapped_for_asset = data.get('swapped_for', None)
        swapped_for = swapped_for_asset.identifier if swapped_for_asset else None
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(
                    'UPDATE common_asset_details SET symbol=?, '
                    'coingecko=?, cryptocompare=?, forked=? WHERE identifier=?',
                    (
                        data.get('symbol'),
                        data.get('coingecko'),
                        data.get('cryptocompare', ''),
                        forked,
                        identifier,
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise InputError(
                    f'Failed to update DB entry for common_asset_details with identifier '
                    f'{identifier} due to a constraint being hit. Make sure the new values '
                    f'are valid.',
                ) from e

            if write_cursor.rowcount != 1:
                raise InputError(
                    f'Tried to edit non existing asset with identifier {identifier}',
                )

            try:
                write_cursor.execute(
                    'UPDATE assets SET name=?, type=?, started=?, swapped_for=? WHERE identifier=?',  # noqa: E501
                    (
                        data.get('name'),
                        data['asset_type'].serialize_for_db(),
                        data.get('started'),
                        swapped_for,
                        identifier,
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise InputError(
                    f'Failed to update DB entry for asset with identifier {identifier} '
                    f'due to a constraint being hit. Make sure the new values are valid.',
                ) from e

    @staticmethod
    def add_user_owned_assets(assets: List['Asset']) -> None:
        """Make sure all assets in the list are included in the user owned assets

        These assets are there so that when someone tries to delete assets from the global DB
        they don't delete assets that are owned by any local user.
        """
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.executemany(
                    'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES(?)',
                    [(x.identifier,) for x in assets if not x.identifier.startswith(NFT_DIRECTIVE)],  # noqa: E501
                )
        except sqlite3.IntegrityError as e:
            log.error(
                f'One of the following asset ids caused a DB IntegrityError ({str(e)}): '
                f'{",".join([x.identifier for x in assets])}',
            )  # should not ever happen but need to handle with informative log if it does

    @staticmethod
    def delete_asset_by_identifier(identifier: str) -> None:
        """Delete an asset by identifier EVEN if it's in the owned assets table
         May raise:
         - InputError if no asset with the provided identifier was found"""
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute('DELETE FROM assets WHERE identifier=?;', (identifier,))
            if write_cursor.rowcount != 1:
                raise InputError(
                    f'Tried to delete asset with identifier {identifier} '
                    f'but it was not found in the DB',
                )

    @staticmethod
    def get_assets_with_symbol(
            symbol: str,
            asset_type: Optional[AssetType] = None,
            chain: Optional[ChainID] = None,
    ) -> List[AssetData]:
        """Find all asset entries that have the given symbol"""
        eth_token_type = AssetType.EVM_TOKEN.serialize_for_db()    # pylint: disable=no-member
        extra_check_evm = ''
        evm_query_list: List[Union[int, str]] = [symbol, eth_token_type]
        if chain is not None:
            extra_check_evm += ' AND B.chain=? '
            evm_query_list.append(chain.serialize_for_db())

        extra_check_common = ''
        common_query_list: List[Union[int, str]] = [symbol, eth_token_type]
        if asset_type is not None:
            extra_check_common += ' AND A.type=? '
            common_query_list.append(asset_type.serialize_for_db())

        querystr = f"""
        SELECT A.identifier, A.type, B.address, B.chain, B.token_kind, B.decimals, A.name, C.symbol, A.started, null, A.swapped_for, C.coingecko, C.cryptocompare, B.protocol FROM assets as A LEFT OUTER JOIN evm_tokens as B
        ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE C.symbol=? COLLATE NOCASE AND A.type=?{extra_check_evm}
        UNION ALL
        SELECT A.identifier, A.type, null, null, null, null, A.name, B.symbol, A.started, B.forked, A.swapped_for, B.coingecko, B.cryptocompare, null FROM assets as A JOIN common_asset_details as B
        ON B.identifier = A.identifier WHERE B.symbol=? COLLATE NOCASE AND A.type!=?{extra_check_common};
        """  # noqa: E501
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(querystr, evm_query_list + common_query_list)
            assets = []
            for entry in cursor:
                asset_type = AssetType.deserialize_from_db(entry[1])
                evm_address: Optional[ChecksumEvmAddress]
                if asset_type == AssetType.EVM_TOKEN:
                    evm_address = string_to_evm_address(entry[2])
                else:
                    evm_address = None
                assets.append(AssetData(
                    identifier=entry[0],
                    asset_type=asset_type,
                    address=evm_address,
                    chain=ChainID.deserialize_from_db(entry[3]) if entry[3] is not None else None,
                    token_kind=EvmTokenKind.deserialize_from_db(entry[4]) if entry[4] is not None else None,  # noqa: E501
                    decimals=entry[5],
                    name=entry[6],
                    symbol=entry[7],
                    started=entry[8],
                    forked=entry[9],
                    swapped_for=entry[10],
                    coingecko=entry[11],
                    cryptocompare=entry[12],
                    protocol=entry[13],
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

        with GlobalDBHandler().conn.read_ctx() as cursor:
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
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.executemany(
                    """INSERT OR IGNORE INTO price_history(
                    from_asset, to_asset, source_type, timestamp, price
                    ) VALUES (?, ?, ?, ?, ?)
                    """, [x.serialize_for_db() for x in entries],
                )
        except sqlite3.IntegrityError as e:
            # roll back any of the executemany that may have gone in
            log.error(
                f'One of the given historical price entries caused a DB error. {str(e)}. '
                f'Will attempt to input them one by one',
            )

            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                for entry in entries:
                    try:
                        write_cursor.execute(
                            """INSERT OR IGNORE INTO price_history(
                            from_asset, to_asset, source_type, timestamp, price
                            ) VALUES (?, ?, ?, ?, ?)
                            """, entry.serialize_for_db(),
                        )
                    except sqlite3.IntegrityError as entry_error:
                        log.error(
                            f'Failed to add {str(entry)} due to {str(entry_error)}. Skipping entry addition',  # noqa: E501
                        )

    @staticmethod
    def add_single_historical_price(entry: HistoricalPrice) -> bool:
        """
        Adds the given historical price entries in the DB.
        Returns True if the operation succeeded and False otherwise
        """
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                serialized = entry.serialize_for_db()
                write_cursor.execute(
                    """INSERT OR IGNORE INTO price_history(
                    from_asset, to_asset, source_type, timestamp, price
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    serialized,
                )
        except sqlite3.IntegrityError as e:
            log.error(
                f'Failed to add single historical price. {str(e)}. ',
            )
            return False

        return True

    @staticmethod
    def get_manual_prices(
        from_asset: Optional[Asset],
        to_asset: Optional[Asset],
    ) -> List[Dict[str, Union[int, str]]]:
        """Returns prices added to the database by the user for an asset"""
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

        with GlobalDBHandler().conn.read_ctx() as cursor:
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
        querystr = (
            'UPDATE price_history SET price=? WHERE from_asset=? AND to_asset=? '
            'AND source_type=? AND timestamp=? '
        )
        entry_serialized = entry.serialize_for_db()
        # Price that is the last entry should be the first and the rest of the
        # positions are correct in the tuple
        params_update = entry_serialized[-1:] + entry_serialized[:-1]
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(querystr, params_update)

                if write_cursor.rowcount == 0:
                    return False
        except sqlite3.IntegrityError as e:
            log.error(
                f'Failed to edit manual historical prices from {entry.from_asset} '
                f'to {entry.to_asset} at timestamp: {str(entry.timestamp)} due to {str(e)}',
            )
            return False

        return True

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
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(querystr, bindings)
            if write_cursor.rowcount != 1:
                log.error(
                    f'Failed to delete historical price from {from_asset} to {to_asset} '
                    f'and timestamp: {str(timestamp)}.',
                )
                return False

        return True

    @staticmethod
    def delete_historical_prices(
            from_asset: 'Asset',
            to_asset: 'Asset',
            source: Optional[HistoricalPriceOracle] = None,
    ) -> None:
        querystr = 'DELETE FROM price_history WHERE from_asset=? AND to_asset=?'
        query_list = [from_asset.identifier, to_asset.identifier]
        if source is not None:
            querystr += ' AND source_type=?'
            query_list.append(source.serialize_for_db())

        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(querystr, tuple(query_list))
        except sqlite3.IntegrityError as e:
            log.error(
                f'Failed to delete historical prices from {from_asset} to {to_asset} '
                f'and source: {str(source)} due to {str(e)}',
            )

    @staticmethod
    def get_historical_price_range(
            from_asset: 'Asset',
            to_asset: 'Asset',
            source: Optional[HistoricalPriceOracle] = None,
    ) -> Optional[Tuple[Timestamp, Timestamp]]:
        querystr = 'SELECT MIN(timestamp), MAX(timestamp) FROM price_history WHERE from_asset=? AND to_asset=?'  # noqa: E501
        query_list = [from_asset.identifier, to_asset.identifier]
        if source is not None:
            querystr += ' AND source_type=?'
            query_list.append(source.serialize_for_db())

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query = cursor.execute(querystr, tuple(query_list))
            result = query.fetchone()
            if result is None or None in (result[0], result[1]):
                return None
            return result[0], result[1]

    @staticmethod
    def get_historical_price_data(source: HistoricalPriceOracle) -> List[Dict[str, Any]]:
        """Return a list of assets and first/last ts

        Only used by the API so just returning it as List of dicts from here"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
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

    @staticmethod
    def set_general_cache_values(
            write_cursor: DBCursor,
            key_parts: Iterable[Union[str, GeneralCacheType]],
            values: Iterable[str],
    ) -> None:
        """Function to update cache in globaldb. Inserts all values paired with the cache key.
        If any entry exists, overwrites it. The timestamp is always the current time."""
        cache_key = _compute_cache_key(key_parts)
        tuples = [(cache_key, value, ts_now()) for value in values]
        write_cursor.executemany(
            'INSERT OR REPLACE INTO general_cache '
            '(key, value, last_queried_ts) VALUES (?, ?, ?)',
            tuples,
        )

    @staticmethod
    def get_general_cache_values(
            key_parts: Iterable[Union[str, GeneralCacheType]],
    ) -> List[str]:
        """Function to read globaldb cache. Returns all the values that are paired with the key."""
        cache_key = _compute_cache_key(key_parts)
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute('SELECT value FROM general_cache WHERE key=?', (cache_key,))
            return [entry[0] for entry in cursor]

    @staticmethod
    def get_general_cache_last_queried_ts(
            key_parts: Iterable[Union[str, GeneralCacheType]],
            value: str,
    ) -> Optional[Timestamp]:
        """Function to get timestamp at which pair key - value was queried last time."""
        cache_key = _compute_cache_key(key_parts)
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT last_queried_ts FROM general_cache WHERE key=? AND value=?',
                (cache_key, value),
            )
            result = cursor.fetchone()
        if result is None:
            return None
        return result[0]

    @staticmethod
    def delete_general_cache(
            write_cursor: DBCursor,
            key_parts: Iterable[Union[str, GeneralCacheType]],
            value: Optional[str] = None,
    ) -> None:
        """Deletes from cache in globaldb. If value is None deletes all entries with the provided
        cache key. Otherwise, deletes only single entry `key - value`."""
        cache_key = _compute_cache_key(key_parts)
        if value is None:
            write_cursor.execute('DELETE FROM general_cache WHERE key=?', (cache_key,))
        else:
            write_cursor.execute('DELETE FROM general_cache WHERE key=? AND value=?', (cache_key, value))  # noqa: E501

    @staticmethod
    def hard_reset_assets_list(
        user_db: 'DBHandler',
        force: bool = False,
    ) -> Tuple[bool, str]:
        """
        Delete all custom asset entries and repopulate from the last
        builtin version
        """
        detach_database = 'DETACH DATABASE "clean_db";'

        with user_db.user_write() as user_db_cursor:
            root_dir = Path(__file__).resolve().parent.parent
            builtin_database = root_dir / 'data' / 'global.db'

            # Update owned assets
            user_db.update_owned_assets_in_globaldb(user_db_cursor)

            try:
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    # First check that the operation can be made. If the difference is not the
                    # empty set the operation is dangerous and the user should be notified.
                    diff_ids = GlobalDBHandler().get_user_added_assets(write_cursor, user_db_cursor, user_db=user_db, only_owned=True)  # noqa: E501
                    if len(diff_ids) != 0 and not force:
                        msg = 'There are assets that can not be deleted. Check logs for more details.'  # noqa: E501
                        return False, msg
                    write_cursor.execute(f'ATTACH DATABASE "{builtin_database}" AS clean_db;')
                    # Check that versions match
                    query = write_cursor.execute('SELECT value from clean_db.settings WHERE name="version";')  # noqa: E501
                    version = query.fetchone()
                    if version is None or int(version[0]) != _get_setting_value(write_cursor, 'version', GLOBAL_DB_VERSION):  # noqa: E501
                        write_cursor.execute(detach_database)
                        msg = (
                            'Failed to restore assets. Global database is not '
                            'updated to the latest version'
                        )
                        return False, msg

                    # If versions match drop tables
                    write_cursor.execute('DELETE FROM assets')
                    write_cursor.execute('DELETE FROM asset_collections')
                    # Copy assets
                    write_cursor.execute('PRAGMA foreign_keys = OFF;')
                    write_cursor.execute('INSERT INTO assets SELECT * FROM clean_db.assets;')
                    write_cursor.execute('INSERT INTO evm_tokens SELECT * FROM clean_db.evm_tokens;')  # noqa: E501
                    write_cursor.execute('INSERT INTO underlying_tokens_list SELECT * FROM clean_db.underlying_tokens_list;')  # noqa: E501
                    write_cursor.execute('INSERT INTO common_asset_details SELECT * FROM clean_db.common_asset_details;')  # noqa: E501
                    write_cursor.execute('INSERT INTO asset_collections SELECT * FROM clean_db.asset_collections')  # noqa: E501
                    write_cursor.execute('INSERT INTO multiasset_mappings SELECT * FROM clean_db.multiasset_mappings')  # noqa: E501
                    # Don't copy custom_assets since there are no custom assets in clean_db
                    write_cursor.execute('PRAGMA foreign_keys = ON;')

                    user_db_cursor.execute('PRAGMA foreign_keys = OFF;')
                    user_db_cursor.execute('DELETE FROM assets;')
                    # Get ids for assets to insert them in the user db
                    write_cursor.execute('SELECT identifier from assets')
                    ids = write_cursor.fetchall()
                    ids_proccesed = ", ".join([f'("{id[0]}")' for id in ids])
                    user_db_cursor.execute(f'INSERT INTO assets(identifier) VALUES {ids_proccesed};')  # noqa: E501
                    user_db_cursor.execute('PRAGMA foreign_keys = ON;')
                    # Update the owned assets table
                    user_db.update_owned_assets_in_globaldb(user_db_cursor)
            except sqlite3.Error as e:
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    write_cursor.execute(detach_database)
                log.error(f'Failed to restore assets in globaldb due to {str(e)}')
                return False, 'Failed to restore assets. Read logs to get more information.'

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(detach_database)

        return True, ''

    @staticmethod
    def soft_reset_assets_list() -> Tuple[bool, str]:
        """
        Resets assets to the state in the packaged global db. Custom assets added by the user
        won't be affected by this reset.
        """
        root_dir = Path(__file__).resolve().parent.parent
        builtin_database = root_dir / 'data' / 'global.db'
        detach_database = 'DETACH DATABASE "clean_db";'

        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(f'ATTACH DATABASE "{builtin_database}" AS clean_db;')
                # Check that versions match
                query = write_cursor.execute('SELECT value from clean_db.settings WHERE name="version";')  # noqa: E501
                version = query.fetchone()
                if version is None or int(version[0]) != _get_setting_value(write_cursor, 'version', GLOBAL_DB_VERSION):  # noqa: E501
                    write_cursor.execute(detach_database)
                    msg = (
                        'Failed to restore assets. Global database is not '
                        'updated to the latest version'
                    )
                    return False, msg
                # Get the list of ids that we will restore
                query = write_cursor.execute('SELECT identifier from clean_db.assets;')
                shipped_ids = set(query.fetchall())
                ids = ', '.join([f'"{id[0]}"' for id in shipped_ids])
                # If versions match drop tables
                write_cursor.execute(f'DELETE FROM assets WHERE identifier IN ({ids});')
                write_cursor.execute('DELETE FROM asset_collections')
                # Copy assets
                write_cursor.execute('PRAGMA foreign_keys = OFF;')
                write_cursor.execute('INSERT INTO assets SELECT * FROM clean_db.assets;')
                write_cursor.execute('INSERT INTO evm_tokens SELECT * FROM clean_db.evm_tokens;')  # noqa: E501
                write_cursor.execute('INSERT INTO underlying_tokens_list SELECT * FROM clean_db.underlying_tokens_list;')  # noqa: E501
                write_cursor.execute('INSERT INTO common_asset_details SELECT * FROM clean_db.common_asset_details;')  # noqa: E501
                write_cursor.execute('INSERT INTO asset_collections SELECT * FROM clean_db.asset_collections')  # noqa: E501
                write_cursor.execute('INSERT INTO multiasset_mappings SELECT * FROM clean_db.multiasset_mappings')  # noqa: E501
                # TODO: think about how to implement multiassets insertion
                write_cursor.execute('PRAGMA foreign_keys = ON;')
        except sqlite3.Error as e:
            log.error(f'Failed to restore assets in globaldb due to {str(e)}')
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(detach_database)
            return False, 'Failed to restore assets. Read logs to get more information.'

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(detach_database)
        return True, ''

    @staticmethod
    def get_user_added_assets(
            cursor: DBCursor,
            user_db_write_cursor: DBCursor,
            user_db: 'DBHandler',
            only_owned: bool = False,
    ) -> Set[str]:
        """
        Create a list of the asset identifiers added by the user. If only_owned
        the assets added by the user and at some point he had are returned.
        May raise:
        - sqlite3.Error if the user_db couldn't be correctly attached
        """
        root_dir = Path(__file__).resolve().parent.parent
        builtin_database = root_dir / 'data' / 'global.db'
        # Update the list of owned assets
        user_db.update_owned_assets_in_globaldb(user_db_write_cursor)
        if only_owned:
            query = cursor.execute('SELECT asset_id from user_owned_assets;')
        else:
            query = cursor.execute('SELECT identifier from assets;')
        user_ids = {tup[0] for tup in query}
        # Attach to the clean db packaged with rotki
        cursor.execute(f'ATTACH DATABASE "{builtin_database}" AS clean_db;')
        # Get built in identifiers
        query = cursor.execute('SELECT identifier from clean_db.assets;')
        shipped_ids = {tup[0] for tup in query}
        cursor.execute('DETACH DATABASE clean_db;')
        return user_ids - shipped_ids


def _reload_constant_assets(globaldb: GlobalDBHandler) -> None:
    """Reloads the details of the constant declared assets after reading from the DB"""
    if len(CONSTANT_ASSETS) != 0:
        identifiers = [x.identifier for x in CONSTANT_ASSETS]
    else:
        identifiers = None
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
        if entry.asset_type == AssetType.EVM_TOKEN:
            if db_entry.asset_type != AssetType.EVM_TOKEN:
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
            object.__setattr__(entry, 'evm_address', db_entry.address)
            object.__setattr__(entry, 'decimals', db_entry.decimals)
            object.__setattr__(entry, 'protocol', db_entry.protocol)
            # TODO: Not changing underlying tokens at the moment since none
            # of the constant ones have but perhaps in the future we should?
        else:
            if db_entry.asset_type == AssetType.EVM_TOKEN:
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
