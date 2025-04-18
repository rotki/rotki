import logging
import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, cast, overload

from gevent.lock import Semaphore

from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    Nft,
    UnderlyingToken,
)
from rotkehlchen.assets.ignored_assets_handling import IgnoredAssetsHandling
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants.assets import A_ETH, A_ETH2, CONSTANT_ASSETS
from rotkehlchen.constants.misc import (
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    GLOBALDB_NAME,
    GLOBALDIR_NAME,
    NFT_DIRECTIVE,
)
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType, DBCursor
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    ChecksumEvmAddress,
    CounterpartyAssetMappingDeleteEntry,
    CounterpartyAssetMappingUpdateEntry,
    EvmTokenKind,
    Location,
    LocationAssetMappingDeleteEntry,
    LocationAssetMappingUpdateEntry,
    Price,
    Timestamp,
)
from rotkehlchen.utils.misc import timestamp_to_date, ts_now
from rotkehlchen.utils.serialization import (
    deserialize_asset_with_oracles_from_db,
    deserialize_generic_asset_from_db,
)

from .upgrades.manager import configure_globaldb
from .utils import GLOBAL_DB_VERSION, globaldb_get_setting_value, initialize_globaldb

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.filtering import (
        AssetsFilterQuery,
        CounterpartyAssetMappingsFilterQuery,
        LocationAssetMappingsFilterQuery,
    )
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


_ALL_ASSETS_TABLES_JOINS = """
FROM assets LEFT JOIN common_asset_details on assets.identifier=common_asset_details.identifier
LEFT JOIN evm_tokens ON evm_tokens.identifier=assets.identifier
LEFT JOIN custom_assets ON custom_assets.identifier=assets.identifier
"""


ALL_ASSETS_TABLES_QUERY = """
SELECT assets.identifier, name, symbol, chain, assets.type, custom_assets.type """ + _ALL_ASSETS_TABLES_JOINS  # noqa: E501


ALL_ASSETS_TABLES_QUERY_WITH_COLLECTIONS = (
    'SELECT assets.identifier, assets.name, common_asset_details.symbol, chain, assets.type, custom_assets.type, collection_id, asset_collections.name, asset_collections.symbol, asset_collections.main_asset, protocol, common_asset_details.coingecko, common_asset_details.cryptocompare' +  # noqa: E501
    _ALL_ASSETS_TABLES_JOINS +
    'LEFT JOIN multiasset_mappings ON assets.identifier=multiasset_mappings.asset LEFT JOIN asset_collections ON multiasset_mappings.collection_id=asset_collections.id'  # noqa: E501
)


def _prioritize_manual_balances_query() -> tuple[str, Literal['A']]:
    """Prioritize manual price if it exists and choose the timestamp closest to the target.
    Return the order statement for the query and the type to prioritize already serialized.
    """
    return (
        ' ORDER BY CASE WHEN source_type=? THEN 0 ELSE 1 END, ABS(timestamp - ?)',
        'A',  # HistoricalPriceOracle.MANUAL.serialize_for_db(),
    )


class GlobalDBHandler:
    """A singleton class controlling the global DB"""
    __instance: Optional['GlobalDBHandler'] = None
    _data_directory: Path | None = None
    _packaged_db_conn: DBConnection | None = None
    conn: DBConnection
    used_backup: bool  # specifies if the global DB was restored from a backup
    packaged_db_lock: Semaphore
    msg_aggregator: 'MessagesAggregator | None' = None

    def __new__(
            cls,
            data_dir: Path | None = None,
            sql_vm_instructions_cb: int | None = None,
            perform_assets_updates: bool | None = None,
            msg_aggregator: 'MessagesAggregator | None' = None,
    ) -> 'GlobalDBHandler':
        """
        Initializes the GlobalDB.

        If the data dir is given it uses the already existing global DB in that directory,
        of if there is none copies the built-in one there.

        If perform_assets_updates is True any assets data will be updated before applying
        schema-breaking changes.

        May raise:
        - DBSchemaError if GlobalDB's schema is malformed
        """
        if GlobalDBHandler.__instance is not None:
            return GlobalDBHandler.__instance
        assert data_dir is not None, 'First instantiation of GlobalDBHandler should have a data_dir'  # noqa: E501
        assert sql_vm_instructions_cb is not None, 'First instantiation of GlobalDBHandler should have a sql_vm_instructions_cb'  # noqa: E501
        assert msg_aggregator is not None, 'First instantiation of GlobalDBHandler should have a messages_aggregator'  # noqa: E501
        assert perform_assets_updates is not None, 'First instantiation of GlobalDBHandler should have a perform_assets_updates'  # noqa: E501

        GlobalDBHandler.__instance = object.__new__(cls)
        GlobalDBHandler.__instance._data_directory = data_dir
        GlobalDBHandler.__instance.msg_aggregator = msg_aggregator

        global_dir = data_dir / GLOBALDIR_NAME
        global_dir.mkdir(parents=True, exist_ok=True)
        if not (global_dir / GLOBALDB_NAME).is_file():
            # if no global db exists, copy the built-in file
            root_dir = Path(__file__).resolve().parent.parent
            builtin_data_dir = root_dir / 'data'
            shutil.copyfile(builtin_data_dir / GLOBALDB_NAME, global_dir / GLOBALDB_NAME)

        GlobalDBHandler.__instance.conn, GlobalDBHandler.__instance.used_backup = initialize_globaldb(  # noqa: E501
            global_dir=global_dir,
            db_filename=GLOBALDB_NAME,
            sql_vm_instructions_cb=sql_vm_instructions_cb,
        )
        GlobalDBHandler.__instance.packaged_db_lock = Semaphore()

        # initialise the asset resolver here since asset updater class might require it.
        AssetResolver(globaldb=GlobalDBHandler.__instance, constant_assets=CONSTANT_ASSETS)
        configure_globaldb(
            global_dir=global_dir,
            db_filename=GLOBALDB_NAME,
            msg_aggregator=msg_aggregator,
            globaldb=GlobalDBHandler.__instance if perform_assets_updates else None,
            connection=GlobalDBHandler.__instance.conn,
        )
        return GlobalDBHandler.__instance

    def filepath(self) -> Path:
        """This should only be called after initialization of the global DB"""
        return self._data_directory / GLOBALDIR_NAME / GLOBALDB_NAME  # type: ignore [operator]

    def cleanup(self) -> None:
        self.conn.close()
        if self._packaged_db_conn is not None:
            self._packaged_db_conn.close()

    @staticmethod
    def packaged_db_conn() -> DBConnection:
        """Return a DBConnection instance for the packaged global db."""
        if GlobalDBHandler()._packaged_db_conn is not None:
            # mypy does not recognize the initialization as that of a singleton
            return GlobalDBHandler()._packaged_db_conn  # type: ignore

        packaged_db_path = Path(__file__).resolve().parent.parent / 'data' / GLOBALDB_NAME
        packaged_db_conn = DBConnection(
            path=packaged_db_path,
            connection_type=DBConnectionType.GLOBAL,
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        )
        GlobalDBHandler()._packaged_db_conn = packaged_db_conn
        return packaged_db_conn

    @staticmethod
    def get_schema_version() -> int:
        """Get the version of the DB Schema"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            return globaldb_get_setting_value(cursor, 'version', GLOBAL_DB_VERSION)

    @staticmethod
    def get_setting_value(name: str, default_value: int) -> int:
        """Get the value of a setting or default. Typing is always int for now"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            return globaldb_get_setting_value(cursor, name, default_value)

    @staticmethod
    def add_setting_value(name: str, value: Any) -> None:
        """Add the value of a setting"""
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                (name, str(value)),
            )

    @staticmethod
    def add_asset(asset: AssetWithNameAndType) -> None:
        """
        Add an asset in the DB.

        May raise InputError in case of error, meaning asset exists or some constraint hit"""
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT INTO assets(identifier, name, type) '
                    'VALUES(?, ?, ?);',
                    (
                        asset.identifier,
                        asset.name,
                        asset.asset_type.serialize_for_db(),
                    ),
                )
                if asset.asset_type == AssetType.CUSTOM_ASSET:
                    write_cursor.execute(
                        'INSERT INTO custom_assets(identifier, type, notes) VALUES(?, ?, ?)',
                        cast('CustomAsset', asset).serialize_for_db(),
                    )
                    return

                # since the asset is not a custom asset it can only be an asset with oracles
                asset = cast('AssetWithOracles', asset)
                forked, started, swapped_for = None, None, None
                if asset.is_crypto():
                    if asset.is_evm_token():
                        asset = cast('EvmToken', asset)
                        GlobalDBHandler.add_evm_token_data(write_cursor, asset)
                    else:
                        asset = cast('CryptoAsset', asset)

                    forked = asset.forked.identifier if asset.forked else None
                    started = asset.started
                    swapped_for = asset.swapped_for.identifier if asset.swapped_for else None

                write_cursor.execute(
                    'INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for)'  # noqa: E501
                    'VALUES(?, ?, ?, ?, ?, ?, ?);',
                    (
                        asset.identifier,
                        asset.symbol,
                        asset.coingecko,
                        asset.cryptocompare,
                        forked,
                        started,
                        swapped_for,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Failed to add asset {asset.identifier} into the assets table due to {e!s}',
            ) from e

    @staticmethod
    def retrieve_assets(userdb: 'DBHandler', filter_query: 'AssetsFilterQuery') -> tuple[list[dict[str, Any]], int]:  # noqa: E501
        """
        Returns a tuple that contains a list of assets details and a
        count of those assets that match the filter query.
        May raise:
        - DeserializationError
        """
        assets_info, offset, limit = {}, None, None
        if filter_query.pagination is not None and filter_query.pagination.limit is not None:
            # we don't apply pagination yet, but after skipping the ignored assets below
            limit = filter_query.pagination.limit
            offset = filter_query.pagination.offset

        prepared_filter_query, bindings = filter_query.prepare(with_pagination=False)
        parent_query = """
        SELECT A.identifier AS identifier, A.type, B.address, B.decimals, A.name, C.symbol,
        C.started, C.forked, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain,
        B.token_kind, D.notes, D.type AS custom_asset_type FROM
        assets as A
        LEFT JOIN common_asset_details AS C ON C.identifier = A.identifier
        LEFT JOIN evm_tokens as B ON B.identifier = A.identifier
        LEFT JOIN custom_assets as D ON D.identifier = A.identifier
        """
        query = f'SELECT * FROM ({parent_query}) {prepared_filter_query}'
        should_skip = filter_query.ignored_assets_handling.get_should_skip_handler()
        with userdb.conn.read_ctx() as cursor:
            ignored_assets = userdb.get_ignored_asset_ids(cursor)

        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(query, bindings)
            for entry in cursor:
                if should_skip(entry[0], ignored_assets):
                    continue
                if offset is not None and offset > 0:
                    offset -= 1  # keep track of the skipped rows to respect the offset
                    continue

                asset_type = AssetType.deserialize_from_db(entry[1])
                data = {
                    'identifier': entry[0],
                    'asset_type': str(asset_type),
                    'name': entry[4],
                }
                # for evm tokens and crypto assets
                common_data = {
                    'symbol': entry[5],
                    'started': entry[6],
                    'swapped_for': entry[8],
                    'forked': entry[7],
                    'cryptocompare': entry[10],
                    'coingecko': entry[9],
                }
                if asset_type == AssetType.FIAT:
                    data.update({
                        'symbol': entry[5],
                        'started': entry[6],
                    })
                elif asset_type == AssetType.EVM_TOKEN:
                    data.update({
                        'address': entry[2],
                        'evm_chain': ChainID.deserialize_from_db(entry[12]).to_name(),
                        'token_kind': EvmTokenKind.deserialize_from_db(entry[13]).serialize(),
                        'decimals': entry[3],
                        'underlying_tokens': None,
                        'protocol': entry[11],
                    })
                    data.update(common_data)
                elif AssetType.is_crypto_asset(asset_type):
                    data.update(common_data)
                elif asset_type == AssetType.CUSTOM_ASSET:
                    data.update({
                        'notes': entry[14],
                        'custom_asset_type': entry[15],
                    })
                else:
                    raise NotImplementedError(f'Unsupported AssetType {asset_type} found in the DB. Should never happen')  # noqa: E501
                assets_info[data['identifier']] = data
                if limit is not None and len(assets_info) >= limit:
                    break

            # Get the identifier of the EVM tokens in the filter and query the underlying tokens
            # where parent_token_entry is in that set of identifiers. We need to join with
            # evm_tokens since the address column is present there. There are 3 methods to filter:
            # 1. Use JOIN and apply the same filters with them.
            # 2. Use a subquery to get identifiers of assets and filter using IN.
            # 3. Directly pass the set of identifiers instead of a subquery and filter using IN.
            # @yabirgb tested 1 and 2, where 1 took on average 1.53 seconds and 2 took 1.17 seconds
            # 2nd is faster and 3rd is fastest because there the frontend limit the number of
            # results before hand, in the range from 10 to 100 and this guarantees that the size of
            # the query is small.
            underlying_tokens_query = (
                f'SELECT parent_token_entry, address, token_kind, weight FROM '
                f'underlying_tokens_list LEFT JOIN evm_tokens ON '
                f'underlying_tokens_list.identifier=evm_tokens.identifier '
                f'WHERE parent_token_entry IN ({",".join(["?"] * len(assets_info))})'
            )
            # populate all underlying tokens
            for entry in cursor.execute(underlying_tokens_query, list(assets_info.keys())):
                if assets_info[entry[0]]['underlying_tokens'] is None:
                    assets_info[entry[0]]['underlying_tokens'] = []
                assets_info[entry[0]]['underlying_tokens'].append(
                    UnderlyingToken.deserialize_from_db((entry[1], entry[2], entry[3])).serialize(),  # noqa: E501
                )

            # get `entries_found`. In the case of handling the ignored assets we need to manually
            # count the assets found since the information needed is both in the
            # userdb (ignored assets) and the globaldb (filtered identifiers)
            query, bindings = filter_query.prepare(with_pagination=False)
            if filter_query.ignored_assets_handling == IgnoredAssetsHandling.NONE:
                total_found_query = f'SELECT COUNT(*) FROM ({parent_query}) ' + query
                entries_found = cursor.execute(total_found_query, bindings).fetchone()[0]
            else:
                total_found_query = f'SELECT identifier FROM ({parent_query}) ' + query
                cursor.execute(total_found_query, bindings)
                identifiers = {row[0] for row in cursor}
                if filter_query.ignored_assets_handling == IgnoredAssetsHandling.EXCLUDE:
                    entries_found = len(identifiers.difference(ignored_assets))
                else:  # IgnoredAssetsHandling.SHOW_ONLY
                    entries_found = len(identifiers.intersection(ignored_assets))

        return list(assets_info.values()), entries_found

    @staticmethod
    def get_assets_mappings(identifiers: list[str]) -> tuple[dict[str, dict], dict[str, dict[str, str]]]:  # noqa: E501
        """
        Given a list of asset identifiers, return a list of asset information
        (id, name, symbol, collection) for those identifiers and a dictionary that maps the
        collection id to their properties.
        """
        result: dict[str, dict[str, Any]] = {}
        asset_collections = {}
        identifiers_query = f'assets.identifier IN ({",".join("?" * len(identifiers))})'
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                ALL_ASSETS_TABLES_QUERY_WITH_COLLECTIONS +
                ' WHERE ' + identifiers_query,
                tuple(identifiers),
            )
            for entry in cursor:
                result[entry[0]] = {
                    'name': entry[1],
                    'symbol': entry[2],
                    'asset_type': AssetType.deserialize_from_db(entry[4]).serialize(),
                }
                if entry[3] is not None:
                    result[entry[0]].update({'evm_chain': ChainID.deserialize_from_db(entry[3]).to_name()})  # noqa: E501
                if entry[5] is not None:
                    result[entry[0]].update({'custom_asset_type': entry[5]})
                if entry[6] is not None:
                    result[entry[0]].update({'collection_id': str(entry[6])})
                    if entry[6] not in asset_collections:
                        asset_collections[str(entry[6])] = {
                            'name': entry[7],
                            'symbol': entry[8],
                            'main_asset': entry[9],
                        }
                if entry[10] == SPAM_PROTOCOL:
                    result[entry[0]].update({'is_spam': True})
                if entry[11] is not None:
                    result[entry[0]].update({'coingecko': entry[11]})
                if entry[12] is not None:
                    result[entry[0]].update({'cryptocompare': entry[12]})
        return result, asset_collections

    @staticmethod
    def search_assets(filter_query: 'AssetsFilterQuery', db: 'DBHandler') -> list[dict[str, Any]]:
        """Returns a list of asset details that match the search query provided."""
        search_result = []
        should_skip = filter_query.ignored_assets_handling.get_should_skip_handler()
        with db.conn.read_ctx() as cursor:
            treat_eth2_as_eth = db.get_settings(cursor).treat_eth2_as_eth
            ignored_assets = db.get_ignored_asset_ids(cursor)

        query, bindings = filter_query.prepare(without_ignored_asset_filter=True)
        query = ALL_ASSETS_TABLES_QUERY + query
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(query, bindings)
            found_eth = False
            for entry in cursor:
                if should_skip(entry[0], ignored_assets):
                    continue

                if treat_eth2_as_eth is True and entry[0] in (A_ETH.identifier, A_ETH2.identifier):
                    if found_eth is False:
                        search_result.append({
                            'identifier': 'ETH',
                            'name': 'Ethereum',
                            'symbol': 'ETH',
                            'is_custom_asset': False,
                        })
                        found_eth = True
                    continue

                entry_info = {
                    'identifier': entry[0],
                    'name': entry[1],
                    'symbol': entry[2],
                    'is_custom_asset': AssetType.deserialize_from_db(entry[4]) == AssetType.CUSTOM_ASSET,  # noqa: E501
                }
                if entry[3] is not None:
                    entry_info['evm_chain'] = ChainID.deserialize_from_db(entry[3]).to_name()
                if entry[5] is not None:
                    entry_info['custom_asset_type'] = entry[5]

                search_result.append(entry_info)

        return search_result

    @overload
    @staticmethod
    def get_all_asset_data(
            mapping: Literal[True],
            serialized: bool = False,
            specific_ids: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        ...

    @overload
    @staticmethod
    def get_all_asset_data(
            mapping: Literal[False],
            serialized: bool = False,
            specific_ids: list[str] | None = None,
    ) -> list[AssetData]:
        ...

    @staticmethod
    def get_all_asset_data(
            mapping: bool,
            serialized: bool = False,
            specific_ids: list[str] | None = None,
    ) -> list[AssetData] | dict[str, dict[str, Any]]:
        """Return all asset data from the DB or all data matching the given ids

        If mapping is True, return them as a Dict of identifier to data
        If mapping is False, return them as a List of AssetData
        """
        result: list[AssetData] | dict[str, dict[str, Any]]
        if mapping:
            result = {}
        else:
            result = []
        specific_ids_query = ''
        if specific_ids is not None:
            specific_ids_query = f'AND A.identifier in ({",".join("?" * len(specific_ids))})'
        querystr = f"""
        SELECT A.identifier, A.type, B.address, B.decimals, A.name, C.symbol, C.started, null, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain, B.token_kind FROM assets as A JOIN evm_tokens as B
        ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE A.type = '{AssetType.EVM_TOKEN.serialize_for_db()}' {specific_ids_query}
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, B.symbol,  B.started, B.forked, B.swapped_for, B.coingecko, B.cryptocompare, null, null, null from assets as A JOIN common_asset_details as B
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
                evm_address: ChecksumEvmAddress | None
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
                    chain_id=chain,
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
    ) -> AssetData | None:
        """Get all details of a single asset by identifier

        Returns None if identifier can't be matched to an asset
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT A.identifier, A.type, A.name, B.symbol, B.started, B.swapped_for, '
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
                    f'{e!s}. Skipping',
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
            chain_id=chain,
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
    ) -> list[UnderlyingToken] | None:
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
            underlying_tokens: list[UnderlyingToken],
            chain_id: ChainID,
    ) -> None:
        """Add the underlying tokens for the parent token

        May raise InputError
        """
        for underlying_token in underlying_tokens:
            if evm_address_to_identifier(
                address=underlying_token.address,
                chain_id=chain_id,
                token_type=underlying_token.token_kind,
            ) == parent_token_identifier:
                raise InputError(f'{parent_token_identifier} cannot be its own underlying token')

            # make sure underlying token address is tracked if not already there
            asset_id = GlobalDBHandler.get_evm_token_identifier(
                cursor=write_cursor,
                address=underlying_token.address,
                chain_id=chain_id,
            )
            if asset_id is None:
                try:  # underlying token does not exist. Track it
                    asset_id = underlying_token.get_identifier(parent_chain=chain_id)
                    write_cursor.execute(
                        'INSERT INTO assets(identifier, name, type)'
                        'VALUES(?, ?, ?);',
                        (asset_id, None, AssetType.EVM_TOKEN.serialize_for_db()),
                    )
                    write_cursor.execute(
                        'INSERT INTO evm_tokens(identifier, address, chain, token_kind)'
                        'VALUES(?, ?, ?, ?)',
                        (
                            asset_id,
                            underlying_token.address,
                            chain_id.serialize_for_db(),
                            underlying_token.token_kind.serialize_for_db(),
                        ),
                    )
                    write_cursor.execute(
                        'INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for)'  # noqa: E501
                        'VALUES(?, ?, ?, ?, ?, ?, ?)',
                        (asset_id, None, None, '', None, None, None),
                    )
                except sqlite3.IntegrityError as e:
                    raise InputError(
                        f'Failed to add underlying tokens for {parent_token_identifier} '
                        f'due to {e!s}',
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
                    f'due to {e!s}',
                ) from e

    @staticmethod
    def get_evm_token_identifier(
            cursor: DBCursor,
            address: ChecksumEvmAddress,
            chain_id: ChainID,
    ) -> str | None:
        """Returns the asset identifier of an EVM token by address if it can be found"""
        query = cursor.execute(
            'SELECT identifier from evm_tokens WHERE address=? AND chain=?;',
            (address, chain_id.serialize_for_db()),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None

        return result[0][0]

    @staticmethod
    def check_asset_exists(asset: AssetWithOracles) -> list[str] | None:
        """
        Checks if an asset of a given type, symbol and name exists in the DB already

        For non ethereum tokens with no unique identifier like an address this is the
        only way to check if something already exists in the DB.

        If it exists it returns a list of the identifiers of the assets.
        """
        cursor = GlobalDBHandler().conn.cursor()
        query = cursor.execute(
            'SELECT A.identifier from assets AS A JOIN common_asset_details as C '
            'ON A.identifier=C.identifier WHERE A.type=? AND A.name=? AND C.symbol=?;',
            (asset.asset_type.serialize_for_db(), asset.name, asset.symbol),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None

        return [x[0] for x in result]

    @staticmethod
    def get_evm_token(address: ChecksumEvmAddress, chain_id: ChainID) -> EvmToken | None:
        """Gets all details for an evm token by its address

        If no token for the given address can be found None is returned.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT A.identifier, B.address, B.chain, B.token_kind, B.decimals, C.name, '
                'A.symbol, A.started, A.swapped_for, A.coingecko, A.cryptocompare, B.protocol '
                'FROM evm_tokens AS B JOIN '
                'common_asset_details AS A ON B.identifier = A.identifier '
                'JOIN assets AS C on C.identifier=A.identifier WHERE B.address=? AND B.chain=?;',
                (address, chain_id.serialize_for_db()),
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
                f'Found unknown swapped_for asset {e!s} in '
                f'the DB when deserializing an EvmToken',
            )
            return None

    @staticmethod
    def get_evm_tokens(
            chain_id: ChainID,
            exceptions: set[ChecksumEvmAddress] | None = None,
            protocol: str | None = None,
            ignore_spam: bool = True,
    ) -> list[EvmToken]:
        """Gets all ethereum tokens from the DB

        Can also accept filtering parameters.
        - List of addresses to ignore via exceptions
        - Protocol for which to return tokens
        - ignore_spam (default True) to filter out "spam protocol" assets
        """
        querystr = (
            'SELECT A.identifier, B.address,  B.chain, B.token_kind, B.decimals, A.name, '
            'C.symbol, C.started, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol '
            'FROM evm_tokens as B LEFT OUTER JOIN '
            'assets AS A on B.identifier = A.identifier JOIN common_asset_details AS C ON '
            'C.identifier = B.identifier WHERE B.chain = ? '
        )
        bindings_list: list[str | (int | ChecksumEvmAddress)] = [chain_id.serialize_for_db()]
        if exceptions is not None or protocol is not None or ignore_spam is True:
            querystr_additions = []
            if exceptions is not None:
                questionmarks = '?' * len(exceptions)
                querystr_additions.append(f'B.address NOT IN ({",".join(questionmarks)}) ')
                bindings_list.extend(exceptions)
            if protocol is not None:
                querystr_additions.append('B.protocol=? ')
                bindings_list.append(protocol)
            if ignore_spam:  # NB: != for nullable needs to be accompanied by IS NULL
                querystr_additions.append('(B.protocol!=? OR protocol IS NULL) ')
                bindings_list.append(SPAM_PROTOCOL)

            querystr += 'AND ' + 'AND '.join(querystr_additions) + ';'
        else:
            querystr += ';'

        bindings = tuple(bindings_list)
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(querystr, bindings)
            tokens = []
            for entry in cursor:
                with GlobalDBHandler().conn.read_ctx() as other_cursor:
                    underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(other_cursor, entry[0])  # noqa: E501

                try:
                    token = EvmToken.deserialize_from_db(entry, underlying_tokens)
                    tokens.append(token)
                except UnknownAsset as e:
                    log.error(
                        f'Found unknown swapped_for asset {e!s} in '
                        f'the DB when deserializing an EvmToken',
                    )

        return tokens

    @staticmethod
    def get_token_detection_data(
            chain_id: ChainID,
            exceptions: set[ChecksumEvmAddress],
            protocol: str | None = None,
    ) -> tuple[list[EvmTokenDetectionData], list[EvmTokenDetectionData]]:
        """Query EVM token data from the database for token detection.

        Retrieves basic token information including identifier, address, and decimals.
        Tokens in the exceptions set are excluded from results. If a token doesn't have
        decimals we default to 18.

        Returns a tuple of (erc20_tokens, erc721_tokens) with each list containing
        token detection data for that type.
        """
        erc20_tokens, erc721_tokens = [], []
        query = 'SELECT identifier, address, token_kind, decimals FROM evm_tokens WHERE chain=?'
        bindings: list[int | str] = [chain_id.serialize_for_db()]
        if protocol is not None:
            query += ' AND protocol=?'
            bindings.append(protocol)

        erc721_token_kind = EvmTokenKind.ERC721.serialize_for_db()
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(query, bindings)
            for identifier, address, token_kind, decimals in cursor:
                if address in exceptions:
                    continue

                details = EvmTokenDetectionData(
                    identifier=identifier,
                    address=address,
                    decimals=decimals if decimals is not None else DEFAULT_TOKEN_DECIMALS,  # TODO: at least two tokens are missing the decimals in my DB and also the EvmToken class allows decimals to be None. We need to think if that is correct and if we should enforce or not for all the erc20s to have decimals.  # noqa: E501
                )
                if token_kind == erc721_token_kind:
                    erc721_tokens.append(details)
                else:
                    erc20_tokens.append(details)

        return erc20_tokens, erc721_tokens

    @staticmethod
    def get_addresses_by_protocol(chain_id: ChainID, protocol: str) -> tuple[ChecksumEvmAddress, ...]:  # noqa: E501
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT address FROM evm_tokens WHERE protocol=? AND chain=?',
                (protocol, chain_id.serialize_for_db()),
            )
            return tuple(string_to_evm_address(entry[0]) for entry in cursor)

    @staticmethod
    def get_token_name(address: ChecksumEvmAddress, chain_id: ChainID) -> str | None:
        """Gets address -> name for the token and given chain if existing"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT assets.name FROM evm_tokens INNER JOIN assets ON '
                'evm_tokens.identifier = assets.identifier WHERE address = ? and chain = ?',
                (address, chain_id.serialize_for_db()),
            )
            result = cursor.fetchone()
            return result if result is None else result[0]

    @staticmethod
    def add_evm_token_data(write_cursor: DBCursor, entry: EvmToken) -> None:
        """Adds ethereum token specific information into the global DB

        May raise InputError if the token already exists or we fail to add the underlying tokens
        """
        try:
            write_cursor.execute(
                'INSERT INTO '
                'evm_tokens(identifier, token_kind, chain, address, decimals, protocol) '
                'VALUES(?, ?, ?, ?, ?, ?)',
                (
                    entry.identifier,
                    entry.token_kind.serialize_for_db(),
                    entry.chain_id.serialize_for_db(),
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
                    f'in the DB due to asset with identifier {entry.identifier} doesnt exist'
                )
            else:
                msg = f'Ethereum token with identifier {entry.identifier} already exists in the DB'
            raise InputError(msg) from e

        if entry.underlying_tokens is not None:
            GlobalDBHandler._add_underlying_tokens(
                write_cursor=write_cursor,
                parent_token_identifier=entry.identifier,
                underlying_tokens=entry.underlying_tokens,
                chain_id=entry.chain_id,
            )

    @staticmethod
    def edit_evm_token(entry: EvmToken) -> str:
        """Edits an EVM token entry in the DB

        May raise InputError if there is an error during updating

        Returns the token's rotki identifier and clears the cache of the asset resolver
        """
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'UPDATE common_asset_details SET symbol=?, coingecko=?, '
                    'cryptocompare=?, forked=?, started=?, swapped_for=? WHERE identifier=?;',
                    (
                        entry.symbol,
                        entry.coingecko,
                        entry.cryptocompare,
                        entry.forked.identifier if entry.forked else None,
                        entry.started,
                        entry.swapped_for.identifier if entry.swapped_for else None,
                        entry.identifier,
                    ),
                )
                write_cursor.execute(
                    'UPDATE assets SET name=?, type=? WHERE identifier=?;',
                    (
                        entry.name,
                        AssetType.EVM_TOKEN.serialize_for_db(),
                        entry.identifier,
                    ),
                )
                write_cursor.execute(
                    'UPDATE evm_tokens SET token_kind=?, chain=?, address=?, decimals=?, '
                    'protocol=? WHERE identifier=?',
                    (
                        entry.token_kind.serialize_for_db(),
                        entry.chain_id.serialize_for_db(),
                        entry.evm_address,
                        entry.decimals,
                        entry.protocol,
                        entry.identifier,
                    ),
                )
                if write_cursor.rowcount != 1:
                    raise InputError(
                        f'Tried to edit non existing EVM token with address {entry.evm_address} at chain {entry.chain_id}',  # noqa: E501
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
                        chain_id=entry.chain_id,
                    )

                rotki_id = GlobalDBHandler.get_evm_token_identifier(write_cursor, entry.evm_address, entry.chain_id)  # noqa: E501
                if rotki_id is None:
                    raise InputError(
                        f'Unexpected DB state. EVM token {entry.evm_address} at chain '
                        f'{entry.chain_id} exists in the DB but its corresponding asset '
                        f'entry was not found.',
                    )

        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Failed to update DB entry for EVM token with address {entry.evm_address} at chain {entry.chain_id}'  # noqa: E501
                f'due to a constraint being hit. Make sure the new values are valid ',
            ) from e

        AssetResolver.clean_memory_cache(entry.identifier)
        return rotki_id

    @staticmethod
    def set_token_protocol_if_missing(token: EvmToken, new_protocol: str) -> None:
        """Update the protocol of the evm token and clean the resolver cache"""
        if token.protocol == new_protocol:
            return

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'UPDATE evm_tokens SET protocol = ? WHERE identifier = ?;',
                (new_protocol, token.identifier),
            )

        AssetResolver.clean_memory_cache(token.identifier)

    @staticmethod
    def edit_user_asset(asset: AssetWithOracles) -> None:
        """Edits an already existing user asset in the DB. Atm only AssetWithOracles are supported.

        May raise InputError if the token already exists or other error
        """
        try:
            asset.check_existence()
        except UnknownAsset as e:
            raise InputError(
                f'Tried to edit non existing asset with identifier {asset.identifier}',
            ) from e

        if asset.is_evm_token():
            GlobalDBHandler.edit_evm_token(asset)  # type: ignore[arg-type]  # It's evm token as guaranteed by the if
            return

        details_update_query = 'UPDATE common_asset_details SET symbol=?, coingecko=?, cryptocompare=?'  # noqa: E501
        details_update_bindings: tuple = (asset.symbol, asset.coingecko, asset.cryptocompare)
        if asset.is_crypto():
            asset = cast('CryptoAsset', asset)
            details_update_query += ', forked=?, started=?, swapped_for=?'
            details_update_bindings += (
                asset.forked.identifier if asset.forked else None,
                asset.started,
                asset.swapped_for.identifier if asset.swapped_for else None,
            )
        details_update_query += ' WHERE identifier=?'
        details_update_bindings += (asset.identifier,)
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(details_update_query, details_update_bindings)
            except sqlite3.IntegrityError as e:
                raise InputError(
                    f'Failed to update DB entry for common_asset_details with identifier '
                    f'{asset.identifier} due to a constraint being hit. Make sure the new values '
                    f'are valid.',
                ) from e

            if write_cursor.rowcount != 1:
                raise InputError(
                    f'Tried to edit non existing asset with identifier {asset.identifier}',
                )

            try:
                write_cursor.execute(
                    'UPDATE assets SET name=?, type=? WHERE identifier=?',
                    (
                        asset.name,
                        asset.asset_type.serialize_for_db(),
                        asset.identifier,
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise InputError(
                    f'Failed to update DB entry for asset with identifier {asset.identifier} '
                    f'due to a constraint being hit. Make sure the new values are valid.',
                ) from e

    @staticmethod
    def add_user_owned_assets(assets: list['Asset']) -> None:
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
                f'One of the following asset ids caused a DB IntegrityError ({e!s}): '
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
            asset_type: AssetType | None = None,
            chain_id: ChainID | None = None,
    ) -> list[AssetWithOracles]:
        """Find all asset entries that have the given symbol"""
        evm_token_type = AssetType.EVM_TOKEN.serialize_for_db()    # pylint: disable=no-member
        extra_check_evm = ''
        evm_query_list: list[int | str] = [evm_token_type, symbol]
        if chain_id is not None:
            extra_check_evm += ' AND B.chain=? '
            evm_query_list.append(chain_id.serialize_for_db())

        extra_check_common = ''
        common_query_list: list[int | str] = [
            evm_token_type,
            AssetType.CUSTOM_ASSET.serialize_for_db(),
            symbol,
        ]
        if asset_type is not None:
            extra_check_common += ' AND A.type=? '
            common_query_list.append(asset_type.serialize_for_db())

        querystr = f"""
        SELECT A.identifier, A.type, B.address, B.decimals, A.name, C.symbol, C.started, null, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain, B.token_kind, null, null FROM assets as A JOIN evm_tokens as B
        ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE A.type = ? AND C.symbol = ? COLLATE NOCASE{extra_check_evm}
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, B.symbol, B.started, B.forked, B.swapped_for, B.coingecko, B.cryptocompare, null, null, null, null, null from assets as A JOIN common_asset_details as B
        ON B.identifier = A.identifier WHERE A.type != ? AND A.type != ? AND B.symbol = ? COLLATE NOCASE{extra_check_common}
        """  # noqa: E501
        assets = []
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(querystr, evm_query_list + common_query_list)
            for entry in cursor.fetchall():
                asset_type = AssetType.deserialize_from_db(entry[1])
                underlying_tokens: list[UnderlyingToken] | None = None
                if asset_type == AssetType.EVM_TOKEN:
                    underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(
                        cursor=cursor,
                        parent_token_identifier=entry[0],
                    )

                try:
                    asset = deserialize_asset_with_oracles_from_db(
                        asset_type=asset_type,
                        asset_data=entry,
                        underlying_tokens=underlying_tokens,
                    )
                except UnknownAsset as e:
                    log.error(f'Asset with identifier {entry[0]} is missing either name, symbol or decimals. {e!s}')  # noqa: E501
                    continue
                except (DeserializationError, WrongAssetType) as e:
                    log.error(f'Asset with identifier {entry[0]} has wrong asset type. {e!s}')
                    continue

                if hasattr(asset, 'protocol') and asset.protocol == 'spam':
                    continue

                assets.append(asset)

        return assets

    @staticmethod
    def get_historical_price(
            from_asset: 'Asset',
            to_asset: 'Asset',
            timestamp: Timestamp,
            max_seconds_distance: int,
            source: HistoricalPriceOracle | None = None,
    ) -> Optional['HistoricalPrice']:
        """Gets the price around a particular timestamp

        If no price can be found returns None
        """
        querystr = (
            'SELECT from_asset, to_asset, source_type, timestamp, price FROM price_history '
            'WHERE from_asset=? AND to_asset=? AND timestamp between ? AND ?'
        )
        querylist = [from_asset.identifier, to_asset.identifier, timestamp - max_seconds_distance, timestamp + max_seconds_distance]  # noqa: E501
        if source is not None:
            querystr += ' AND source_type=? '
            querylist.append(source.serialize_for_db())

        # prioritize manual price if it exists and choose the timestamp closest to the target
        order_str, priority_type = _prioritize_manual_balances_query()
        querystr += order_str
        querylist += [priority_type, timestamp]

        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (result := cursor.execute(querystr, querylist).fetchone()) is None:
                return None

        return HistoricalPrice.deserialize_from_db(result)

    @staticmethod
    def get_historical_prices(
            query_data: list[tuple['Asset', 'Asset', Timestamp]],
            max_seconds_distance: int,
            source: HistoricalPriceOracle | None = None,
    ) -> list[HistoricalPrice | None]:
        """Given a list of from/to/timestamp data to query returns all values
        that could be found in the DB and None for those that could not be found.
        """
        querystr = (
            'SELECT from_asset, to_asset, source_type, timestamp, price '
            'FROM price_history WHERE from_asset=? AND to_asset=? AND timestamp BETWEEN ? AND ?'
        )
        querylist: list[tuple] = []
        if source is not None:
            querystr += ' AND source_type=? '
            serialized_source = source.serialize_for_db()
            for from_asset, to_asset, timestamp in query_data:
                querylist.append((from_asset.identifier, to_asset.identifier, timestamp - max_seconds_distance, timestamp + max_seconds_distance, serialized_source))  # noqa: E501

        else:
            for from_asset, to_asset, timestamp in query_data:
                querylist.append((from_asset.identifier, to_asset.identifier, timestamp - max_seconds_distance, timestamp + max_seconds_distance))  # noqa: E501

        order_str, priority_type = _prioritize_manual_balances_query()
        querystr += order_str
        prices_results: list[HistoricalPrice | None] = []
        with GlobalDBHandler().conn.read_ctx() as cursor:
            for query_entry, (_, _, queried_timestamp) in zip(querylist, query_data, strict=True):
                # to the params add the arguments to prioritize manual prices
                result = cursor.execute(querystr, query_entry + (priority_type, queried_timestamp)).fetchone()  # below last index of the result tuple is ignored in deserialize  # noqa: E501
                if result is None:
                    prices_results.append(None)
                    continue

                db_price = HistoricalPrice.deserialize_from_db(result)
                prices_results.append(HistoricalPrice(
                    from_asset=db_price.from_asset,
                    to_asset=db_price.to_asset,
                    source=db_price.source,
                    timestamp=queried_timestamp,  # Use original queried timestamp
                    price=db_price.price,
                ))

        return prices_results

    @staticmethod
    def add_historical_prices(entries: list['HistoricalPrice']) -> None:
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
                f'One of the given historical price entries caused a DB error. {e!s}. '
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
                            f'Failed to add {entry!s} due to {entry_error!s}. Skipping entry addition',  # noqa: E501
                        )

    @staticmethod
    def add_single_historical_price(entry: HistoricalPrice) -> bool:
        """
        Adds the given historical price entries in the DB.
        Returns True if the operation succeeded and False otherwise.
        If the price for the specified asset pair, oracle type and timestamp already exists,
        it is replaced.
        """
        try:
            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                serialized = entry.serialize_for_db()
                write_cursor.execute(
                    """INSERT OR REPLACE INTO price_history(
                    from_asset, to_asset, source_type, timestamp, price
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    serialized,
                )
        except sqlite3.IntegrityError as e:
            log.error(
                f'Failed to add single historical price. {e!s}. ',
            )
            return False

        return True

    @staticmethod
    def add_manual_latest_price(from_asset: Asset, to_asset: Asset, price: Price) -> set[Asset]:
        """
        Adds manual current price and turns previously known manual current price into a
        historical manual price.

        Returns a sets of asset from pairs involving `from_asset` to invalidate their
        cached prices.
        May raise:
        - InputError if some db constraint was hit. Probably means manual price duplication.
        """
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            try:
                write_cursor.execute(
                    'UPDATE price_history SET source_type=? WHERE source_type=? AND from_asset=?',
                    (
                        HistoricalPriceOracle.MANUAL.serialize_for_db(),
                        HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(),
                        from_asset.identifier,
                    ),
                )
            except sqlite3.IntegrityError as e:
                # if we got an error, do an extra query to give more information to the user.
                # In case of an error there has to be a corresponding entry in the db.
                with GlobalDBHandler().conn.read_ctx() as cursor:
                    timestamp = cursor.execute(
                        'SELECT timestamp FROM price_history WHERE source_type=? AND from_asset=?',
                        (
                            HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(),
                            from_asset.identifier,
                        ),
                    ).fetchone()[0]
                raise InputError(
                    f'Failed to add manual current price because manual price already exists '
                    f'at {timestamp_to_date(ts=timestamp)}',
                ) from e
            try:
                write_cursor.execute(
                    'INSERT INTO '
                    'price_history(from_asset, to_asset, source_type, timestamp, price) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (
                        from_asset.identifier,
                        to_asset.identifier,
                        HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(),
                        ts_now(),
                        str(price),
                    ),
                )
            except sqlite3.IntegrityError as e:
                # Means foreign keys failure. Should not happen since is checked by marshmallow
                raise InputError(f'Failed to add manual current price due to: {e!s}') from e

            #  invalidate the cached price for the assets that are using manual current as type and
            # and that are connected to the given asset
            write_cursor.execute(
                'SELECT from_asset, to_asset FROM price_history WHERE source_type=? AND (from_asset=? OR to_asset=?)',  # noqa: E501
                (HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(), from_asset.identifier, from_asset.identifier),  # noqa: E501
            )
            return {Asset(asset) for entry in write_cursor for asset in entry}

    @staticmethod
    def get_manual_current_price(asset: Asset) -> tuple[Asset, Price] | None:
        """Reads manual current price of an asset. If no price is found returns None."""
        with GlobalDBHandler().conn.read_ctx() as read_cursor:
            result = read_cursor.execute(
                'SELECT to_asset, price FROM price_history WHERE source_type=? AND from_asset=?',
                (HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(), asset.identifier),
            ).fetchone()

        if result is None:
            return None

        return Asset(result[0]), deserialize_price(result[1])

    @staticmethod
    def get_all_manual_latest_prices(
            from_asset: Asset | None = None,
            to_asset: Asset | None = None,
    ) -> list[tuple[str, str, str]]:
        """Returns all the manual current prices in the price_history table"""
        query = 'SELECT from_asset, to_asset, price FROM price_history WHERE source_type=?'
        bindings = [HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db()]
        if from_asset is not None:
            query += ' AND from_asset=?'
            bindings.append(from_asset.identifier)
        if to_asset is not None:
            query += ' AND to_asset=?'
            bindings.append(to_asset.identifier)

        with GlobalDBHandler().conn.read_ctx() as read_cursor:
            read_cursor.execute(query, bindings)
            return read_cursor.fetchall()

    @staticmethod
    def delete_manual_latest_price(asset: Asset) -> set[Asset]:
        """
        Deletes manual current price from globaldb and returns the set of assets to invalidate

        May raise:
        - InputError if asset was not found in the price_history table
        """
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # get asset pairs to invalidate their prices from cache after deletion
            write_cursor.execute(
                'SELECT from_asset, to_asset FROM price_history WHERE source_type=? AND (from_asset=? OR to_asset=?);',  # noqa: E501
                (HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(), asset.identifier, asset.identifier),  # noqa: E501
            )
            assets_to_invalidate = {Asset(asset) for entry in write_cursor for asset in entry}

            # Execute the deletion
            write_cursor.execute(
                'DELETE FROM price_history WHERE source_type=? AND from_asset=?',
                (HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(), asset.identifier),
            )
            if write_cursor.rowcount != 1:
                raise InputError(
                    f'Not found manual current price to delete for asset {asset!s}',
                )

            return assets_to_invalidate

    @staticmethod
    def get_manual_prices(
            from_asset: Asset | None,
            to_asset: Asset | None,
    ) -> list[dict[str, int | str]]:
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
                f'to {entry.to_asset} at timestamp: {entry.timestamp!s} due to {e!s}',
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
                    f'and timestamp: {timestamp!s}.',
                )
                return False

        return True

    @staticmethod
    def delete_historical_prices(
            from_asset: 'Asset',
            to_asset: 'Asset',
            source: HistoricalPriceOracle | None = None,
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
                f'and source: {source!s} due to {e!s}',
            )

    @staticmethod
    def get_historical_price_range(
            from_asset: 'Asset',
            to_asset: 'Asset',
            source: HistoricalPriceOracle | None = None,
    ) -> tuple[Timestamp, Timestamp] | None:
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
    def get_historical_price_data(source: HistoricalPriceOracle) -> list[dict[str, Any]]:
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

    def hard_reset_assets_list(
            self,
            user_db: 'DBHandler',
            force: bool = False,
    ) -> tuple[bool, str]:
        """
        Delete all custom asset entries and repopulate from the last
        builtin version
        """
        root_dir = Path(__file__).resolve().parent.parent
        builtin_database = root_dir / 'data' / GLOBALDB_NAME
        # Update owned assets
        with user_db.conn.read_ctx() as cursor:
            user_db.update_owned_assets_in_globaldb(cursor)

        with self.conn.read_ctx() as read_cursor:
            # First check that the operation can be made. If the difference is not the
            # empty set the operation is dangerous and the user should be notified.
            with user_db.user_write() as user_db_cursor:
                diff_ids = self.get_user_added_assets(
                    cursor=read_cursor,
                    user_db_write_cursor=user_db_cursor,
                    user_db=user_db,
                    only_owned=True,
                )
                if len(diff_ids) != 0 and not force:
                    msg = 'There are assets that can not be deleted. Check logs for more details.'
                    return False, msg

            with self.packaged_db_lock:
                read_cursor.execute(f"ATTACH DATABASE '{builtin_database}' AS clean_db;")
                try:
                    # Check that versions match
                    query = read_cursor.execute("SELECT value from clean_db.settings WHERE name='version';")  # noqa: E501
                    version = query.fetchone()
                    if version is None or int(version[0]) != globaldb_get_setting_value(read_cursor, 'version', GLOBAL_DB_VERSION):  # noqa: E501
                        msg = (
                            'Failed to restore assets. Global database is not '
                            'updated to the latest version'
                        )
                        return False, msg

                    with self.conn.write_ctx() as write_cursor:
                        # If versions match drop tables
                        write_cursor.execute('DELETE FROM assets')
                        write_cursor.execute('DELETE FROM asset_collections')
                        # Copy assets
                        write_cursor.switch_foreign_keys('OFF')
                        write_cursor.execute('INSERT INTO assets SELECT * FROM clean_db.assets;')
                        write_cursor.execute('INSERT INTO evm_tokens SELECT * FROM clean_db.evm_tokens;')  # noqa: E501
                        write_cursor.execute('INSERT INTO underlying_tokens_list SELECT * FROM clean_db.underlying_tokens_list;')  # noqa: E501
                        write_cursor.execute('INSERT INTO common_asset_details SELECT * FROM clean_db.common_asset_details;')  # noqa: E501
                        write_cursor.execute('INSERT INTO asset_collections SELECT * FROM clean_db.asset_collections')  # noqa: E501
                        write_cursor.execute('INSERT INTO multiasset_mappings SELECT * FROM clean_db.multiasset_mappings')  # noqa: E501
                        # Don't copy custom_assets since there are no custom assets in clean_db
                        write_cursor.switch_foreign_keys('ON')

                        with user_db.user_write() as user_db_cursor:
                            user_db_cursor.switch_foreign_keys('OFF')
                            user_db_cursor.execute('DELETE FROM assets;')
                            # Get ids for assets to insert them in the user db
                            write_cursor.execute('SELECT identifier from assets')
                            ids = write_cursor.fetchall()
                            ids_processed = ', '.join([f"('{identifier[0]}')" for identifier in ids])  # noqa: E501
                            user_db_cursor.execute(f'INSERT INTO assets(identifier) VALUES {ids_processed};')  # noqa: E501
                            user_db_cursor.switch_foreign_keys('ON')

                    with user_db.conn.read_ctx() as cursor:
                        # Update the owned assets table
                        user_db.update_owned_assets_in_globaldb(cursor)

                except sqlite3.Error as e:
                    log.error(f'Failed to restore assets in globaldb due to {e!s}')
                    return False, 'Failed to restore assets. Read logs to get more information.'
                finally:  # on the way out always detach the DB. Make sure no transaction is active
                    with self.conn.critical_section_and_transaction_lock():
                        read_cursor.execute("DETACH DATABASE 'clean_db';")

        return True, ''

    def soft_reset_assets_list(self) -> tuple[bool, str]:
        """
        Resets assets to the state in the packaged global db. Custom assets added by the user
        won't be affected by this reset.
        """
        root_dir = Path(__file__).resolve().parent.parent
        builtin_database = root_dir / 'data' / GLOBALDB_NAME

        with self.packaged_db_lock:
            try:
                with self.conn.read_ctx() as read_cursor:
                    read_cursor.execute(f"ATTACH DATABASE '{builtin_database}' AS clean_db;")
                    # Check that versions match
                    query = read_cursor.execute("SELECT value from clean_db.settings WHERE name='version';")  # noqa: E501
                    version = query.fetchone()
                    if version is None or int(version[0]) != globaldb_get_setting_value(read_cursor, 'version', GLOBAL_DB_VERSION):  # noqa: E501
                        msg = (
                            'Failed to restore assets. Global database is not '
                            'updated to the latest version'
                        )
                        return False, msg

                    # Get the list of ids that we will restore
                    query = read_cursor.execute('SELECT identifier from clean_db.assets;')
                    shipped_asset_ids = set(query.fetchall())
                    asset_ids = ', '.join([f"'{identifier[0]}'" for identifier in shipped_asset_ids])  # noqa: E501
                    query = read_cursor.execute('SELECT id FROM clean_db.asset_collections')
                    shipped_collection_ids = set(query.fetchall())
                    collection_ids = ', '.join([f"'{identifier[0]}'" for identifier in shipped_collection_ids])  # noqa: E501

                with self.conn.write_ctx() as write_cursor:
                    # If versions match drop tables
                    write_cursor.switch_foreign_keys('OFF')
                    write_cursor.execute(f'DELETE FROM assets WHERE identifier IN ({asset_ids});')
                    write_cursor.execute(f'DELETE FROM evm_tokens WHERE identifier IN ({asset_ids});')  # noqa: E501
                    write_cursor.execute(f'DELETE FROM underlying_tokens_list WHERE parent_token_entry IN ({asset_ids});')  # noqa: E501
                    write_cursor.execute(f'DELETE FROM common_asset_details WHERE identifier IN ({asset_ids});')  # noqa: E501
                    write_cursor.execute(f'DELETE FROM asset_collections WHERE id IN ({collection_ids})')  # noqa: E501
                    write_cursor.execute(f'DELETE FROM multiasset_mappings WHERE collection_id IN ({collection_ids})')  # noqa: E501
                    # Copy assets
                    write_cursor.execute('INSERT INTO assets SELECT * FROM clean_db.assets;')
                    write_cursor.execute('INSERT INTO evm_tokens SELECT * FROM clean_db.evm_tokens;')  # noqa: E501
                    write_cursor.execute('INSERT INTO underlying_tokens_list SELECT * FROM clean_db.underlying_tokens_list;')  # noqa: E501
                    write_cursor.execute('INSERT INTO common_asset_details SELECT * FROM clean_db.common_asset_details;')  # noqa: E501
                    write_cursor.execute('INSERT INTO asset_collections SELECT * FROM clean_db.asset_collections')  # noqa: E501
                    write_cursor.execute('INSERT INTO multiasset_mappings SELECT * FROM clean_db.multiasset_mappings')  # noqa: E501
                    # TODO: think about how to implement multiassets insertion
                    write_cursor.switch_foreign_keys('ON')
            except sqlite3.Error as e:
                log.error(f'Failed to restore assets in globaldb due to {e!s}')
                return False, 'Failed to restore assets. Read logs to get more information.'
            finally:  # on the way out always detach the DB. Make sure no transaction is active
                with self.conn.transaction_lock, self.conn.read_ctx() as read_cursor:
                    read_cursor.execute("DETACH DATABASE 'clean_db';")

        return True, ''

    @staticmethod
    def get_user_added_assets(
            cursor: DBCursor,
            user_db_write_cursor: DBCursor,
            user_db: 'DBHandler',
            only_owned: bool = False,
    ) -> set[str]:
        """
        Create a list of the asset identifiers added by the user.

        If only_owned the assets added by the user and at some point he had are returned.
        Given cursor of the Global DB must be read only

        May raise:
        - sqlite3.Error if the user_db couldn't be correctly attached
        """
        # Update the list of owned assets
        user_db.update_owned_assets_in_globaldb(user_db_write_cursor)
        if only_owned:
            query = cursor.execute('SELECT asset_id from user_owned_assets;')
        else:
            query = cursor.execute('SELECT identifier from assets;')
        user_ids = {tup[0] for tup in query}

        # Get built in identifiers
        with GlobalDBHandler().packaged_db_conn().read_ctx() as packaged_cursor:
            query = packaged_cursor.execute('SELECT identifier from assets;')
            shipped_ids = {tup[0] for tup in query}

        return user_ids - shipped_ids

    @staticmethod
    def resolve_asset(
            identifier: str,
            use_packaged_db: bool = False,
    ) -> AssetWithNameAndType:
        """
        Resolve asset in only one query to the database

        If `use_packaged_db` is True, it checks the packaged global db.

        The functions called here could also potentially raise WrongAssetType
        but due to the way they are called they should not. The expected type
        is always based on what type the asset already has in DB when called
        from this function.

        May raise:
        - UnknownAsset if the asset is not found in the database
        """
        if identifier.startswith(NFT_DIRECTIVE):
            return Nft(identifier)
        query = """
        SELECT A.identifier, A.type, B.address, B.decimals, A.name, C.symbol, C.started, null, C.swapped_for, C.coingecko, C.cryptocompare, B.protocol, B.chain, B.token_kind, null, null FROM assets as A JOIN evm_tokens as B
        ON B.identifier = A.identifier JOIN common_asset_details AS C ON C.identifier = B.identifier WHERE A.type = ? AND A.identifier = ?
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, B.symbol, B.started, B.forked, B.swapped_for, B.coingecko, B.cryptocompare, null, null, null, null, null from assets as A JOIN common_asset_details as B
        ON B.identifier = A.identifier WHERE A.type != ? AND A.type != ? AND A.identifier = ?
        UNION ALL
        SELECT A.identifier, A.type, null, null, A.name, null, null, null, null, null, null, null, null, null, B.notes, B.type FROM assets AS A JOIN custom_assets AS B on A.identifier=B.identifier WHERE A.identifier = ?
        """  # noqa: E501
        connection = GlobalDBHandler().packaged_db_conn() if use_packaged_db is True else GlobalDBHandler().conn  # noqa: E501
        with connection.read_ctx() as cursor:
            cursor.execute(
                query,
                (
                    AssetType.EVM_TOKEN.serialize_for_db(),
                    identifier,
                    AssetType.EVM_TOKEN.serialize_for_db(),
                    AssetType.CUSTOM_ASSET.serialize_for_db(),
                    identifier,
                    identifier,
                ),
            )

            asset_data = cursor.fetchone()
            if asset_data is None:
                raise UnknownAsset(identifier)

            asset_type = AssetType.deserialize_from_db(asset_data[1])
            underlying_tokens = None
            if asset_type == AssetType.EVM_TOKEN:
                underlying_tokens = GlobalDBHandler().fetch_underlying_tokens(
                    cursor=cursor,
                    parent_token_identifier=identifier,
                )

            return deserialize_generic_asset_from_db(
                asset_type=asset_type,
                asset_data=asset_data,
                underlying_tokens=underlying_tokens,
            )

    def resolve_asset_from_packaged_and_store(self, identifier: str) -> AssetWithNameAndType:
        """
        Reads an asset from the packaged globaldb and adds it to the database if missing or edits
        the local version of the asset overwriting it with that of the packaged DB.

        May raise:
        - UnknownAsset
        """
        asset = self.resolve_asset(
            identifier=identifier,
            use_packaged_db=True,
        )
        # make sure that the asset is saved on the user's global db. First check if it exists
        with self.conn.read_ctx() as cursor:
            asset_count = cursor.execute(
                'SELECT COUNT(*) FROM assets WHERE identifier=?',
                (identifier,),
            ).fetchone()[0]

        if asset_count == 0:
            # the asset doesn't exist and need to be added
            self.add_asset(asset)
        elif asset.asset_type == AssetType.EVM_TOKEN:
            # in this case the asset exists and needs to be updated
            self.edit_evm_token(cast('EvmToken', asset))
        else:
            self.edit_user_asset(cast('CryptoAsset', asset))

        return asset

    @staticmethod
    def get_asset_type(identifier: str, use_packaged_db: bool = False) -> AssetType:
        """
        For a given identifier return the type of the asset associated to that identifier.
        If `use_packaged_db` is True, it checks the packaged global db.

        May raise:
        - UnknownAsset: if the asset is not present in the database
        """
        if identifier.startswith(NFT_DIRECTIVE):
            return AssetType.NFT

        connection = GlobalDBHandler().packaged_db_conn() if use_packaged_db is True else GlobalDBHandler().conn  # noqa: E501
        with connection.read_ctx() as cursor:
            type_in_db = cursor.execute(
                'SELECT type FROM assets WHERE identifier=?',
                (identifier,),
            ).fetchone()

        if type_in_db is None:  # should not happen
            raise UnknownAsset(identifier)

        return AssetType.deserialize_from_db(type_in_db[0])

    @staticmethod
    def asset_id_exists(identifier: str, use_packaged_db: bool = False) -> str:
        """
        For a given identifier return the normalized identifier if it exists.
        If `use_packaged_db` is True, it checks the packaged global db.

        May raise:
        - UnknownAsset: if the asset is not present in the database
        """
        if identifier.startswith(NFT_DIRECTIVE):
            return identifier

        connection = GlobalDBHandler.packaged_db_conn() if use_packaged_db is True else GlobalDBHandler().conn  # noqa: E501
        with connection.read_ctx() as cursor:
            normalized_id = cursor.execute(
                'SELECT identifier FROM assets WHERE identifier=?',
                (identifier,),
            ).fetchone()

        if normalized_id is None:  # should not happen
            raise UnknownAsset(identifier)

        return normalized_id[0]

    @staticmethod
    def get_collection_main_asset(identifier: str) -> str | None:
        """Return the main asset in a collection for a given asset identifier.

        TODO: There's still a need for hierarchical collections
        https://github.com/rotki/rotki/issues/8639
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
               'SELECT ac.main_asset FROM asset_collections AS ac '
               'INNER JOIN multiasset_mappings AS mm ON mm.collection_id = ac.id '
               'WHERE mm.asset = ?',
               (identifier,),
            )
            result = cursor.fetchone()

        return result[0] if result is not None else None

    @staticmethod
    def asset_in_collection(collection_id: int, asset_id: str) -> bool:
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM multiasset_mappings WHERE collection_id=? AND asset=?',
                (collection_id, asset_id),
            )
            return cursor.fetchone()[0] == 1

    @staticmethod
    def get_or_write_abi(serialized_abi: str, abi_name: str | None = None) -> int:
        """
        Finds and returns the id of the given abi.
        If the abi doesn't exist in the db, inserts it there.
        """
        # check if the abi is already present in the database
        with GlobalDBHandler().conn.read_ctx() as cursor:
            existing_abi_id = cursor.execute(
                'SELECT id FROM contract_abi WHERE value=?',
                (serialized_abi,),
            ).fetchone()

        if existing_abi_id is not None:
            return existing_abi_id[0]
        else:
            with GlobalDBHandler().conn.write_ctx() as cursor:
                cursor.execute(
                    'INSERT INTO contract_abi(name, value) VALUES(?, ?)',
                    (abi_name, serialized_abi),
                )
                return cursor.lastrowid

    @staticmethod
    def get_assets_in_same_collection(identifier: str) -> tuple[Asset, ...]:
        """
        Query the assets that belong to the collection of the queried asset. If the
        asset isn't in any collection we return a list with the asset queried.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT MM.asset FROM multiasset_mappings AS MM JOIN asset_collections AS AC '
                'ON MM.collection_id = AC.id WHERE MM.collection_id = (SELECT collection_id '
                'FROM multiasset_mappings WHERE asset=?)',
                (identifier,),
            )
            collection_assets = tuple(Asset(row[0]) for row in cursor)

        if len(collection_assets) == 0:
            return (Asset(identifier),)

        return collection_assets

    @staticmethod
    def get_assetid_from_exchange_name(exchange: Location | None, symbol: str, default: str) -> str:  # noqa: E501
        """Returns the asset's identifier from the ticker symbol of the given exchange according to
        location_asset_mappings table. Use exchange=None to get the common id for all exchanges.
        If the mapping is not present returns default."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if exchange is not None and cursor.execute(
                'SELECT COUNT(*) FROM location_unsupported_assets WHERE location=? AND exchange_symbol=?',  # noqa: E501
                (exchange.serialize_for_db(), symbol),
            ).fetchone()[0] > 0:
                raise UnsupportedAsset(symbol)

            location_filter, bindings = '', [symbol]
            if exchange is not None:
                location_filter = 'location IS ? OR'
                bindings.append(exchange.serialize_for_db())
            identifier = cursor.execute(
                f'SELECT local_id FROM location_asset_mappings WHERE exchange_symbol=? AND ({location_filter} location IS NULL)',  # noqa: E501
                bindings,
            ).fetchone()

        return default if identifier is None else identifier[0]

    @staticmethod
    def query_asset_mappings_by_type(
            dict_keys: tuple[str, str, str],
            mapping_type: Literal['location', 'counterparty'],
            query_columns: Literal['local_id, location, exchange_symbol', 'local_id, counterparty, symbol'],  # noqa: E501
            filter_query: Union['LocationAssetMappingsFilterQuery', 'CounterpartyAssetMappingsFilterQuery'],  # noqa: E501
            location_or_counterparty_reader_callback: Callable,
    ) -> tuple[list[dict[str, str | Location | None]], int, int]:
        """Query asset mappings based on the mapping type.

        Returns:
          - A list of mapping dictionaries.
          - The count of mappings matching the filter.
          - The total count of mappings.

        For location mappings, keys are: 'asset', 'location', 'location_symbol'.
        For counterparty mappings, keys are: 'asset', 'counterparty', 'counterparty_symbol'.
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            mappings_total = cursor.execute(
                f'SELECT COUNT(*) FROM {mapping_type}_asset_mappings',
            ).fetchone()[0]

            query, bindings = filter_query.prepare(with_pagination=False)
            mappings_count = cursor.execute(
                f'SELECT COUNT(*) FROM {mapping_type}_asset_mappings {query}', bindings,
            ).fetchone()[0]

            query, bindings = filter_query.prepare()
            cursor.execute(
                f'SELECT {query_columns} FROM {mapping_type}_asset_mappings {query}', bindings,
            )
            return [
                location_or_counterparty_reader_callback(dict(zip(dict_keys, entry, strict=False)))
                for entry in cursor
            ], mappings_count, mappings_total

    @staticmethod
    def _execute_mapping_operation(
            entries: list[LocationAssetMappingUpdateEntry] | list[LocationAssetMappingDeleteEntry] | list[CounterpartyAssetMappingDeleteEntry] | list[CounterpartyAssetMappingUpdateEntry],  # noqa: E501
            sql_query: str,
            error_msg: str,
            sql_bindings_fn: Callable,
            skip_errors: bool = False,
            pre_check_fn: Callable | None = None,
    ) -> None:
        """Generic function to handle asset mapping operations.

        - entries: List of mapping entries to process.
        - error_msg: Template for the error message in case of operation failure.
        - sql_bindings_fn: A function that accepts an entry and returns a tuple of values to bind into sql_query.
        - skip_errors: If True, errors during execution will be logged instead of stopping execution.
        - pre_check_fn: Optional function to perform a pre-execution check.
        - sql_query: SQL statement to execute. This should be a parameterized query (using placeholders)
                     that works with the bindings provided by sql_bindings_fn.

        May raise:
            - InputError if operations fail and skip_errors is False
        """  # noqa: E501
        with (globaldb := GlobalDBHandler()).conn.write_ctx() as write_cursor:
            for entry in entries:
                msg = error_msg.format(entry=entry)
                try:
                    if pre_check_fn is not None:
                        with globaldb.conn.read_ctx() as cursor:
                            pre_check_fn(cursor, entry)

                    write_cursor.execute(sql_query, sql_bindings_fn(entry))
                    if sql_query.startswith(('UPDATE', 'DELETE')) and write_cursor.rowcount != 1:
                        if skip_errors:
                            log.error(msg)
                        else:
                            raise InputError(msg)

                except sqlite3.IntegrityError as e:
                    if skip_errors:
                        log.error(msg)
                    else:
                        raise InputError(msg) from e

    @staticmethod
    def add_location_asset_mappings(
            entries: list[LocationAssetMappingUpdateEntry],
            skip_errors: bool = False,
    ) -> None:
        """Adds the given mapping entries of asset identifiers and their symbols in the given
        location to the location_asset_mappings table.

        May Raise (if skip_errors is False):
        - InputError if any of the pairs of location and exchange_symbol already exist"""
        GlobalDBHandler._execute_mapping_operation(
            entries=entries,
            skip_errors=skip_errors,
            pre_check_fn=GlobalDBHandler._location_asset_mapping_null_precheck,
            sql_bindings_fn=lambda entry: entry.serialize_for_db(),
            sql_query='INSERT INTO location_asset_mappings(local_id, exchange_symbol, location) VALUES(?, ?, ?)',  # noqa: E501
            error_msg='Failed to add the location asset mapping of {entry} because it already exists in the DB.',  # noqa: E501
        )

    @staticmethod
    def _location_asset_mapping_null_precheck(cursor: 'DBCursor', entry: LocationAssetMappingUpdateEntry) -> None:  # noqa: E501
        if (
                entry.location is None and
                cursor.execute(
                    'SELECT COUNT(*) FROM location_asset_mappings WHERE location IS NULL AND local_id=? AND exchange_symbol=?',  # noqa: E501
                    entry.serialize_for_db()[:2],  # the asset and the exchange symbol.
                ).fetchone()[0] > 0
        ):
            raise sqlite3.IntegrityError('Entry already exists in the DB')

    @staticmethod
    def update_location_asset_mappings(
            entries: list[LocationAssetMappingUpdateEntry],
            skip_errors: bool = False,
    ) -> None:
        """Updates the mapped asset identifiers in the location_asset_mappings table based on their
        location symbol.

        May Raise (if skip_errors is False):
        - InputError if any of the pairs of location and exchange_symbol does not exist"""
        GlobalDBHandler._execute_mapping_operation(
            entries=entries,
            skip_errors=skip_errors,
            sql_bindings_fn=lambda entry: entry.serialize_for_db(),
            sql_query='UPDATE location_asset_mappings SET local_id=? WHERE exchange_symbol=? AND location IS ?',  # noqa: E501
            error_msg='Failed to update the location asset mapping of {entry} because it does not exist in the DB.',  # noqa: E501
        )

    @staticmethod
    def delete_location_asset_mappings(
            entries: list[LocationAssetMappingDeleteEntry],
            skip_errors: bool = False,
    ) -> None:
        """Deletes the mappings of given asset identifiers in the given location from the
        location_asset_mappings table.

        May Raise (if skip_errors is False):
        - InputError if any of the pairs of location and exchange_symbol does not exist"""
        GlobalDBHandler._execute_mapping_operation(
            entries=entries,
            skip_errors=skip_errors,
            sql_bindings_fn=lambda entry: entry.serialize_for_db(),
            sql_query='DELETE FROM location_asset_mappings WHERE exchange_symbol=? AND location IS ?',  # noqa: E501
            error_msg='Failed to delete the location asset mapping of {entry} because it does not exist in the DB.',  # noqa: E501
        )

    @staticmethod
    def add_counterparty_asset_mappings(
            entries: list[CounterpartyAssetMappingUpdateEntry],
            skip_errors: bool = False,
    ) -> None:
        """Adds the given mapping entries of asset identifiers and their symbols for the given
        counterparty to the counterparty_asset_mappings table.

        May raise (if skip_errors is False):
            - InputError if any of the pairs of counterparty and symbol already exist
        """
        GlobalDBHandler._execute_mapping_operation(
            entries=entries,
            skip_errors=skip_errors,
            sql_bindings_fn=lambda entry: entry.serialize_for_db(),
            sql_query='INSERT INTO counterparty_asset_mappings(local_id, symbol, counterparty) VALUES(?, ?, ?)',  # noqa: E501
            error_msg='Failed to add the counterparty asset mapping of {entry} because it already exists in the DB.',  # noqa: E501
        )

    @staticmethod
    def update_counterparty_asset_mappings(
            entries: list[CounterpartyAssetMappingUpdateEntry],
            skip_errors: bool = False,
    ) -> None:
        """Updates the mapped asset identifiers in the counterparty_asset_mappings table
        based on their counterparty symbol.

        May raise(if skip_errors is False):
            - InputError if any of the pairs of counterparty and symbol does not exist
        """
        GlobalDBHandler._execute_mapping_operation(
            entries=entries,
            skip_errors=skip_errors,
            sql_bindings_fn=lambda entry: entry.serialize_for_db(),
            sql_query='UPDATE counterparty_asset_mappings SET local_id=? WHERE symbol=? AND counterparty=?',  # noqa: E501
            error_msg='Failed to update the counterparty asset mapping of {entry} because it does not exist in the DB.',  # noqa: E501
        )

    @staticmethod
    def delete_counterparty_asset_mappings(
            entries: list[CounterpartyAssetMappingDeleteEntry],
            skip_errors: bool = False,
    ) -> None:
        """Deletes the mappings of given asset identifiers for the given counterparty from the
        counterparty_asset_mappings table.

        May raise (if skip_errors is False):
            - InputError if any of the pairs of counterparty and symbol does not exist
        """
        GlobalDBHandler._execute_mapping_operation(
            entries=entries,
            skip_errors=skip_errors,
            sql_bindings_fn=lambda entry: entry.serialize_for_db(),
            sql_query='DELETE FROM counterparty_asset_mappings WHERE symbol=? AND counterparty=?',
            error_msg='Failed to delete the counterparty asset mapping of {entry} because it does not exist in the DB.',  # noqa: E501
        )

    @staticmethod
    def get_protocol_for_asset(asset_identifier: str) -> str | None:
        """Get the protocol of the asset with the given identifier."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            return protocol[0] if (protocol := cursor.execute(
                'SELECT protocol FROM evm_tokens WHERE identifier=?;',
                (asset_identifier,),
            ).fetchone()) is not None else None

    def clear_locks(self) -> None:
        """release the locks in the globaldb.

        We saw that when killing a greenlet the locks are not released and has to
        be done manually.
        It won't raise errors if the lock is over-released
        https://www.gevent.org/api/gevent.lock.html#gevent.lock.Semaphore.release
        The killall that happens in this logic can trigger a greenlet switch as per
        https://github.com/gevent/gevent/issues/1473#issuecomment-548327614
        """
        self.packaged_db_lock.release()
        self.conn.transaction_lock.release()
        self.conn.in_callback.release()
