import json
import logging
import re
import sqlite3
from contextlib import suppress
from enum import Enum, auto
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, Optional, Union

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetData, AssetType
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, Timestamp
from rotkehlchen.utils.misc import is_production
from rotkehlchen.utils.network import query_file

from .handler import GlobalDBHandler, initialize_globaldb

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ASSETS_VERSION_KEY = 'assets_version'
ASSETS_UPDATES_URL = 'https://raw.githubusercontent.com/rotki/assets/{branch}/updates/{version}/updates.sql'  # noqa: E501
ASSET_COLLECTIONS_UPDATES_URL = 'https://raw.githubusercontent.com/rotki/assets/{branch}/updates/{version}/asset_collections_updates.sql'  # noqa: E501
ASSET_COLLECTIONS_MAPPINGS_UPDATES_URL = 'https://raw.githubusercontent.com/rotki/assets/{branch}/updates/{version}/asset_collections_mappings_updates.sql'  # noqa: E501
FIRST_VERSION_WITH_COLLECTIONS = 16


class UpdateFileType(Enum):
    ASSETS = auto()
    ASSET_COLLECTIONS = auto()
    ASSET_COLLECTIONS_MAPPINGS = auto()


def executeall(cursor: DBCursor, statements: str) -> None:
    """Splits all statements and execute()s one by one to avoid the
    commit that executescript would do.

    TODO: Is there a better way? Couldn't find one
    """
    for statement in statements.split(';'):
        if statement == '':
            continue
        cursor.execute(statement)


def _replace_assets_from_db(
        connection: 'DBConnection',
        sourcedb_path: Path,
) -> None:
    with connection.write_ctx() as cursor:
        cursor.executescript(f"""
        ATTACH DATABASE "{sourcedb_path}" AS other_db;
        PRAGMA foreign_keys = OFF;
        DELETE FROM assets;
        DELETE FROM evm_tokens;
        DELETE FROM underlying_tokens_list;
        DELETE FROM common_asset_details;
        DELETE FROM asset_collections;
        DELETE FROM multiasset_mappings;
        INSERT INTO assets SELECT * FROM other_db.assets;
        INSERT INTO evm_tokens SELECT * FROM other_db.evm_tokens;
        INSERT INTO underlying_tokens_list SELECT * FROM other_db.underlying_tokens_list;
        INSERT INTO common_asset_details SELECT * FROM other_db.common_asset_details;
        INSERT INTO asset_collections SELECT * FROM other_db.asset_collections;
        INSERT INTO multiasset_mappings SELECT * FROM other_db.multiasset_mappings;
        INSERT OR REPLACE INTO settings(name, value) VALUES("{ASSETS_VERSION_KEY}",
        (SELECT value FROM other_db.settings WHERE name="{ASSETS_VERSION_KEY}")
        );
        PRAGMA foreign_keys = ON;
        DETACH DATABASE "other_db";
        """)


def _force_remote_asset(cursor: DBCursor, local_asset: Asset, full_insert: str) -> None:
    """Force the remote entry into the database by deleting old one and doing the full insert.

    May raise an sqlite3 error if something fails.
    """
    cursor.execute(
        'DELETE FROM assets WHERE identifier=?;',
        (local_asset.identifier,),
    )
    # Insert new entry. Since identifiers are the same, no foreign key constrains should break
    executeall(cursor, full_insert)
    AssetResolver().clean_memory_cache(local_asset.identifier.lower())


class ParsedAssetData(NamedTuple):
    identifier: str
    asset_type: AssetType
    name: str
    symbol: str
    started: Optional[Timestamp]
    swapped_for: Optional[str]
    coingecko: Optional[str]
    cryptocompare: Optional[str]
    forked: Optional[str]


class AssetsUpdater:

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        self.msg_aggregator = msg_aggregator
        self.local_assets_version = GlobalDBHandler().get_setting_value(ASSETS_VERSION_KEY, 0)
        self.last_remote_checked_version = -1  # integer value that represents no update
        self.conflicts: list[tuple[AssetData, AssetData]] = []
        self.assets_re = re.compile(r'.*INSERT +INTO +assets\( *identifier *, *name *, *type *\) +VALUES\(([^\)]*?),([^\)]*?),([^\)]*?)\).*?')  # noqa: E501
        self.evm_tokens_re = re.compile(r'.*INSERT +INTO +evm_tokens\( *identifier *, *token_kind *, *chain *, *address *, *decimals *, *protocol *\) +VALUES\(([^\)]*?),([^\)]*?),([^\)]*?),([^\)]*?),([^\)]*?),([^\)]*?)\).*')  # noqa: E501
        self.common_asset_details_re = re.compile(r'.*INSERT +INTO +common_asset_details\( *identifier *, *symbol *, *coingecko *, *cryptocompare *, *forked *, *started *, *swapped_for *\) +VALUES\((.*?),(.*?),(.*?),(.*?),(.*?),([^\)]*?),([^\)]*?)\).*')  # noqa: E501
        self.assets_collection_re = re.compile(r'.*INSERT +INTO +asset_collections\( *id *, *name *, *symbol *\) +VALUES +\(([^\)]*?),([^\)]*?),([^\)]*?)\).*?')  # noqa: E501
        self.multiasset_mappings_re = re.compile(r'.*INSERT +INTO +multiasset_mappings\( *collection_id *, *asset *\) +VALUES +\(([^\)]*?), *"([^\)]+?)"\).*?')  # noqa: E501
        self.string_re = re.compile(r'.*"(.*?)".*')
        self.branch = 'develop'
        if is_production():
            self.branch = 'master'

    def _get_remote_info_json(self) -> dict[str, Any]:
        url = f'https://raw.githubusercontent.com/rotki/assets/{self.branch}/updates/info.json'
        try:
            response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query Github {url} during assets update: {e!s}') from e  # noqa: E501

        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(
                f'Could not parse assets update info as json from Github: {response.text}',
            ) from e

        return json_data

    def check_for_updates(self) -> tuple[int, int, int]:
        """
        Checks the remote to see if there is new assets to get
        May raise:
           - RemoteError if there is a problem querying Github
        """
        self.local_assets_version = GlobalDBHandler().get_setting_value(ASSETS_VERSION_KEY, 0)
        json_data = self._get_remote_info_json()
        local_schema_version = GlobalDBHandler().get_schema_version()
        new_asset_changes = 0
        try:
            remote_version = json_data['latest']
            for string_version, entry in json_data['updates'].items():
                applicable_update = (
                    int(string_version) > self.local_assets_version and
                    entry['min_schema_version'] <= local_schema_version <= entry['max_schema_version']  # noqa: E501
                )
                if applicable_update:
                    new_asset_changes += entry['changes']
        except KeyError as e:
            raise RemoteError(f'Didnt find expected key {e!s} in github assets json during update') from e  # noqa: E501
        except ValueError as e:
            raise RemoteError(f'{e!s} in github assets json during update') from e

        self.last_remote_checked_version = remote_version
        return self.local_assets_version, remote_version, new_asset_changes

    def _parse_value(self, value: str) -> Optional[Union[str, int]]:
        match = self.string_re.match(value)
        if match is not None:
            return match.group(1)

        value = value.strip()
        if value == 'NULL':
            return None

        try:
            return int(value)
        except ValueError:
            return value

    def _parse_str(self, value: str, name: str, insert_text: str) -> str:
        result = self._parse_value(value)
        if not isinstance(result, str):
            raise DeserializationError(
                f'At asset DB update got invalid {name} {value} from {insert_text}',
            )
        return result

    def _parse_optional_str(self, value: str, name: str, insert_text: str) -> Optional[str]:
        result = self._parse_value(value)
        if result is not None and not isinstance(result, str):
            raise DeserializationError(
                f'At asset DB update got invalid {name} {value} from {insert_text}',
            )
        return result

    def _parse_optional_int(self, value: str, name: str, insert_text: str) -> Optional[int]:
        result = self._parse_value(value)
        if result is not None and not isinstance(result, int):
            raise DeserializationError(
                f'At asset DB update got invalid {name} {value} from {insert_text}',
            )
        return result

    def _parse_asset_data(self, insert_text: str) -> ParsedAssetData:
        assets_match = self.assets_re.match(insert_text)
        if assets_match is None:
            raise DeserializationError(
                f'At asset DB update could not parse asset data out of {insert_text}',
            )
        if len(assets_match.groups()) != 3:
            raise DeserializationError(
                f'At asset DB update could not parse asset data out of {insert_text}',
            )

        raw_type = self._parse_str(assets_match.group(3), 'asset type', insert_text)
        asset_type = AssetType.deserialize_from_db(raw_type)

        common_details_match = self.common_asset_details_re.match(insert_text)
        if common_details_match is None:
            raise DeserializationError(
                f'At asset DB update could not parse common asset '
                f'details data out of {insert_text}',
            )
        raw_started = self._parse_optional_int(common_details_match.group(6), 'started', insert_text)  # noqa: E501
        started = Timestamp(raw_started) if raw_started else None

        return ParsedAssetData(
            identifier=self._parse_str(common_details_match.group(1), 'identifier', insert_text),
            asset_type=asset_type,
            name=self._parse_str(assets_match.group(2), 'name', insert_text),
            symbol=self._parse_str(common_details_match.group(2), 'symbol', insert_text),
            started=started,
            swapped_for=self._parse_optional_str(common_details_match.group(7), 'swapped_for', insert_text),  # noqa: E501
            coingecko=self._parse_optional_str(common_details_match.group(3), 'coingecko', insert_text),  # noqa: E501
            cryptocompare=self._parse_optional_str(common_details_match.group(4), 'cryptocompare', insert_text),  # noqa: E501
            forked=self._parse_optional_str(common_details_match.group(5), 'forked', insert_text),
        )

    def _parse_evm_token_data(
            self,
            insert_text: str,
    ) -> tuple[ChecksumEvmAddress, Optional[int], Optional[str], Optional[ChainID], Optional[EvmTokenKind]]:  # noqa: E501
        match = self.evm_tokens_re.match(insert_text)
        if match is None:
            raise DeserializationError(
                f'At asset DB update could not parse evm token data out '
                f'of {insert_text}',
            )

        if len(match.groups()) != 6:
            raise DeserializationError(
                f'At asset DB update could not parse evm token data out of {insert_text}',
            )

        chain_value = self._parse_optional_int(
            value=match.group(3),
            name='chain',
            insert_text=insert_text,
        )
        if chain_value is not None:
            chain_id = ChainID(chain_value)
        else:
            chain_id = None

        token_kind_value = self._parse_optional_str(
            value=match.group(2),
            name='token_kind',
            insert_text=insert_text,
        )
        if token_kind_value is not None:
            token_kind = EvmTokenKind.deserialize_from_db(token_kind_value)
        else:
            token_kind = None

        return (
            deserialize_evm_address(self._parse_str(match.group(4), 'address', insert_text)),
            self._parse_optional_int(match.group(5), 'decimals', insert_text),
            self._parse_optional_str(match.group(6), 'protocol', insert_text),
            chain_id,
            token_kind,
        )

    def _parse_full_insert_assets(self, insert_text: str) -> AssetData:
        """Parses full insert line for an asset to give information for the conflict to the user

        Note: In the future this needs to be different for each version
        May raise:
        - DeserializationError if the appropriate data is not found or if it can't
        be properly parsed.
        """
        asset_data = self._parse_asset_data(insert_text)
        address = decimals = protocol = chain_id = token_kind = None
        if asset_data.asset_type == AssetType.EVM_TOKEN:
            address, decimals, protocol, chain_id, token_kind = self._parse_evm_token_data(insert_text)  # noqa: E501

        # types are not really proper here (except for asset_type, chain_id and token_kind)
        return AssetData(
            identifier=asset_data.identifier,
            name=asset_data.name,
            symbol=asset_data.symbol,
            asset_type=asset_data.asset_type,
            started=asset_data.started,
            forked=asset_data.forked,
            swapped_for=asset_data.swapped_for,
            address=address,
            chain_id=chain_id,
            token_kind=token_kind,
            decimals=decimals,
            cryptocompare=asset_data.cryptocompare,
            coingecko=asset_data.coingecko,
            protocol=protocol,
        )

    def _process_asset_collection(
            self,
            connection: 'DBConnection',
            action: str,
            full_insert: str,
    ) -> None:
        """Process the insertion of a new asset_collection"""
        collection_match = self.assets_collection_re.match(full_insert)
        if collection_match is None:
            log.error(f'Failed to match asset collection {full_insert}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {action}',
            )

        groups = collection_match.groups()
        if len(groups) != 3:
            log.error(f'Asset collection {full_insert} does not have the expected elements')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {action}',
            )

        try:
            with connection.savepoint_ctx() as cursor:
                cursor.execute(action)
        except sqlite3.Error:
            try:
                with connection.savepoint_ctx() as cursor:
                    cursor.execute(full_insert)
            except sqlite3.Error as e:
                log.error(
                    f'Failed to edit or add asset collection with name {groups[1]} and id '
                    f'{groups[0]}. {action}. Error: {e!s}',
                )

    def _process_multiasset_mapping(
            self,
            connection: 'DBConnection',
            action: str,
            full_insert: str,
    ) -> None:
        """
        Process the insertion of a new asset_collection mapping
        May raise:
        - DeserializationError
        - UnknownAsset
        """
        mapping_match = self.multiasset_mappings_re.match(full_insert)
        if mapping_match is None:
            log.error(f'Failed to match asset collection mapping {full_insert}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {action}',
            )

        groups = mapping_match.groups()
        if len(groups) != 2:
            log.error(f'Failed to find all elements in asset collection mapping {full_insert}')
            raise DeserializationError(
                f'At asset DB update could not parse asset collection data out of {action}',
            )

        # check that the asset exists and so does the collection
        with connection.read_ctx() as cursor:
            cursor.execute('SELECT COUNT(*) FROM assets where identifier=?', (groups[1],))
            if cursor.fetchone()[0] == 0:
                raise UnknownAsset(groups[1])

            cursor.execute(
                'SELECT COUNT(*) FROM asset_collections WHERE id=?',
                (self._parse_value(groups[0]),),
            )
            if cursor.fetchone()[0] != 1:
                raise DeserializationError(
                    f'Tried to add asset to collection with id {groups[0]} but it does not exist',
                )

        try:
            with connection.savepoint_ctx() as cursor:
                cursor.execute(action)
        except sqlite3.Error:
            try:
                with connection.savepoint_ctx() as cursor:
                    cursor.execute(full_insert)
            except sqlite3.Error as e:
                log.error(
                    f'Failed to edit asset collection mapping with asset {groups[1]} '
                    f'and id {groups[0]}. {action}. Error: {e!s}',
                )

    def _handle_asset_update(
            self,
            connection: 'DBConnection',
            remote_asset_data: AssetData,
            assets_conflicts: Optional[dict[Asset, Literal['remote', 'local']]],
            action: str,
            full_insert: str,
            version: int,
    ) -> None:
        """
        Given the already processed information for an asset try to store it in the globaldb
        and if it is not possible due to conflicts mark it to resolve later.
        """
        local_asset: Optional[Asset] = None
        with suppress(UnknownAsset):
            # we avoid querying the packaged db to prevent the copy of constant assets
            local_asset = Asset(remote_asset_data.identifier).check_existence(query_packaged_db=False)  # noqa: E501

        try:
            with connection.savepoint_ctx() as cursor:
                executeall(cursor, action)
                if local_asset is not None:
                    AssetResolver().clean_memory_cache(identifier=local_asset.identifier)
        except sqlite3.Error:  # https://docs.python.org/3/library/sqlite3.html#exceptions
            if local_asset is None:
                try:  # if asset is not known then simply do an insertion
                    with connection.savepoint_ctx() as cursor:
                        executeall(cursor, full_insert)
                except sqlite3.Error as e:
                    self.msg_aggregator.add_warning(
                        f'Failed to add asset {remote_asset_data.identifier} in the '
                        f'DB during the v{version} assets update. Skipping entry. '
                        f'Error: {e!s}',
                    )
                return  # fail or succeed continue to next entry

            if local_asset is not None:
                AssetResolver().clean_memory_cache(local_asset.identifier.lower())

            # otherwise asset is known, so it's a conflict. Check if we can resolve
            resolution = assets_conflicts.get(local_asset) if assets_conflicts else None
            if resolution == 'local':
                # do nothing, keep local
                return
            if resolution == 'remote':
                try:
                    with connection.savepoint_ctx() as cursor:
                        _force_remote_asset(cursor, local_asset, full_insert)
                except sqlite3.Error as e:
                    self.msg_aggregator.add_warning(
                        f'Failed to resolve conflict for {remote_asset_data.identifier} in '
                        f'the DB during the v{version} assets update. Skipping entry. '
                        f'Error: {e!s}',
                    )
                return  # fail or succeed continue to next entry

            # else can't resolve. Mark it for the user to resolve.
            # TODO: When assets refactor is finished, remove the usage of AssetData here
            local_data = GlobalDBHandler().get_all_asset_data(
                mapping=False,
                serialized=False,
                specific_ids=[local_asset.identifier],
            )[0]
            self.conflicts.append((local_data, remote_asset_data))

    def _apply_single_version_update(
            self,
            connection: 'DBConnection',
            version: int,
            text: str,
            assets_conflicts: Optional[dict[Asset, Literal['remote', 'local']]],
            update_file_type: UpdateFileType,
    ) -> None:
        """
        Process the queried file and apply special rules depending on the type of file
        (assets updates, collections updates or mappings updates) set in update_file_type.

        If conflicts appear while processing the assets those are handled. Deserialization
        errors are caught and the user is warned about them.
        """
        lines = text.splitlines()
        for action, full_insert in zip(*[iter(lines)] * 2):
            if full_insert.strip() == '*':
                full_insert = action  # noqa: PLW2901

            if update_file_type == UpdateFileType.ASSETS:
                remote_asset_data = None
                try:
                    remote_asset_data = self._parse_full_insert_assets(full_insert)
                except DeserializationError as e:
                    log.error(
                        f'Failed to add asset with action {action} during update to v{version}',
                    )
                    self.msg_aggregator.add_warning(
                        f'Skipping entry during assets update to v{version} due '
                        f'to a deserialization error. {e!s}',
                    )

                if remote_asset_data is not None:
                    self._handle_asset_update(
                        connection=connection,
                        remote_asset_data=remote_asset_data,
                        assets_conflicts=assets_conflicts,
                        action=action,
                        full_insert=full_insert,
                        version=version,
                    )
            elif update_file_type == UpdateFileType.ASSET_COLLECTIONS:
                try:
                    self._process_asset_collection(
                        connection=connection,
                        action=action,
                        full_insert=full_insert,
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(
                        f'Skipping entry during assets collection update to v{version} due '
                        f'to a deserialization error. {e!s}',
                    )
            else:
                assert update_file_type == UpdateFileType.ASSET_COLLECTIONS_MAPPINGS
                try:
                    self._process_multiasset_mapping(
                        connection=connection,
                        action=action,
                        full_insert=full_insert,
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(
                        f'Skipping entry during assets collection multimapping update to '
                        f'v{version} due to a deserialization error. {e!s}',
                    )
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Tried to add unknown asset {e.identifier} to collection of assets. Skipping',  # noqa: E501
                    )

        # at the very end update the current version in the DB
        connection.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (ASSETS_VERSION_KEY, str(version)),
        )

    def perform_update(
            self,
            up_to_version: Optional[int],
            conflicts: Optional[dict[Asset, Literal['remote', 'local']]],
    ) -> Optional[list[dict[str, Any]]]:
        """Performs an asset update by downloading new changes from the remote

        If `up_to_version` is given then changes up to and including that version are made.
        If not all possible changes are applied.

        For success returns None. If there is conflicts a list of conflicting
        assets identifiers is going to be returned.

        May raise:
            - RemoteError if there is a problem querying Github
        """
        if self.last_remote_checked_version == -1:
            self.check_for_updates()

        self.conflicts = []  # reset the stored conflicts
        infojson = self._get_remote_info_json()
        local_schema_version = GlobalDBHandler().get_schema_version()
        data_directory = GlobalDBHandler()._data_directory
        assert data_directory is not None, 'data directory should be initialized at this point'
        global_db_path = data_directory / 'global_data' / 'global.db'

        # We retrieve first all the files required for the different updates that will be performed
        updates = self._retrieve_update_files(
            local_schema_version=local_schema_version,
            infojson=infojson,
            up_to_version=up_to_version,
        )

        with TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)
            temp_db_name = 'temp.db'
            temp_db_connection, _ = initialize_globaldb(
                global_dir=tmpdir,
                db_filename=temp_db_name,
                sql_vm_instructions_cb=GlobalDBHandler().conn.sql_vm_instructions_cb,
            )

            # use a critical section to avoid modifications in the globaldb during the update
            # process since we ignore any possible change in the user globaldb once we started
            # the update.
            with GlobalDBHandler().conn.critical_section():
                log.info('Starting assets update. Copying content from the user globaldb')
                _replace_assets_from_db(temp_db_connection, global_db_path)
                self._perform_update(
                    connection=temp_db_connection,
                    assets_conflicts=conflicts,
                    up_to_version=up_to_version,
                    updates=updates,
                )

                temp_db_connection.close()
                if len(self.conflicts) != 0:
                    return [
                        {'identifier': x[0].identifier, 'local': x[0].serialize(), 'remote': x[1].serialize()}  # noqa: E501
                        for x in self.conflicts
                    ]

                # otherwise we are sure the DB will work without conflicts so let's
                # now move the data to the actual global DB
                log.info('Finishing assets update. Replacing users globaldb with the updated information')  # noqa: E501
                _replace_assets_from_db(GlobalDBHandler().conn, tmpdir / temp_db_name)

        return None

    def _perform_update(
            self,
            connection: 'DBConnection',
            assets_conflicts: Optional[dict[Asset, Literal['remote', 'local']]],
            up_to_version: Optional[int],
            updates: dict[int, dict[UpdateFileType, str]],
    ) -> None:
        """
        Apply to the db the different sql updates from the `updates` argument
        """
        target_version = min(up_to_version, self.last_remote_checked_version) if up_to_version else self.last_remote_checked_version   # noqa: E501
        for version in range(self.local_assets_version + 1, target_version + 1):
            log.info(f'Applying assets update from {version}')
            if version not in updates:
                continue

            self._apply_single_version_update(
                connection=connection,
                version=version,
                text=updates[version][UpdateFileType.ASSETS],
                assets_conflicts=assets_conflicts,
                update_file_type=UpdateFileType.ASSETS,
            )

            if version >= FIRST_VERSION_WITH_COLLECTIONS:
                self._apply_single_version_update(
                    connection=connection,
                    version=version,
                    text=updates[version][UpdateFileType.ASSET_COLLECTIONS],
                    assets_conflicts=None,
                    update_file_type=UpdateFileType.ASSET_COLLECTIONS,
                )
                self._apply_single_version_update(
                    connection=connection,
                    version=version,
                    text=updates[version][UpdateFileType.ASSET_COLLECTIONS_MAPPINGS],
                    assets_conflicts=None,
                    update_file_type=UpdateFileType.ASSET_COLLECTIONS_MAPPINGS,
                )

        if self.conflicts == []:
            connection.commit()
            return

        # In this case we have conflicts. Everything should also be rolled back
        connection.rollback()

    def _retrieve_update_files(
            self,
            local_schema_version: int,
            infojson: dict[str, Any],
            up_to_version: Optional[int],
    ) -> dict[int, dict[UpdateFileType, str]]:
        """
        Query the assets update repository to retrieve the pending updates before trying to
        apply them. It returns a dict that maps each version to their update files.

        May raise:
        - RemoteError if there is a problem querying github
        """
        updates = {}
        target_version = min(up_to_version, self.last_remote_checked_version) if up_to_version else self.last_remote_checked_version   # noqa: E501
        # type ignore since due to check_for_updates we know last_remote_checked_version exists
        for version in range(self.local_assets_version + 1, target_version + 1):
            try:
                min_schema_version = infojson['updates'][str(version)]['min_schema_version']
                max_schema_version = infojson['updates'][str(version)]['max_schema_version']
                if local_schema_version < min_schema_version:
                    self.msg_aggregator.add_warning(
                        f'Skipping assets update {version} since it requires a min schema of '
                        f'{min_schema_version}. Please upgrade rotki to get this assets update',
                    )
                    break  # get out of the loop

                if local_schema_version > max_schema_version:
                    self.msg_aggregator.add_warning(
                        f'Skipping assets update {version} since it requires a min '
                        f'schema of {min_schema_version} and max schema of {max_schema_version} '
                        f'while the local DB schema version is {local_schema_version}. '
                        f'You will have to follow an alternative method to '
                        f'obtain the assets of this update. Easiest would be to reset global DB.',
                    )
                    continue
            except KeyError as e:
                log.error(
                    f'Remote info.json for version {version} did not contain '
                    f'key "{e!s}". Skipping update.',
                )
                continue

            assets_url = ASSETS_UPDATES_URL.format(branch=self.branch, version=version)
            asset_collections_url = ASSET_COLLECTIONS_UPDATES_URL.format(branch=self.branch, version=version)  # noqa: E501
            asset_collections_mappings_url = ASSET_COLLECTIONS_MAPPINGS_UPDATES_URL.format(branch=self.branch, version=version)  # noqa: E501

            assets_file = query_file(url=assets_url, is_json=False)
            if version >= FIRST_VERSION_WITH_COLLECTIONS:
                asset_collections_file = query_file(url=asset_collections_url, is_json=False)
                asset_collections_mappings_file = query_file(
                    url=asset_collections_mappings_url,
                    is_json=False,
                )
            else:
                asset_collections_file, asset_collections_mappings_file = '', ''

            updates[version] = {
                UpdateFileType.ASSETS: assets_file,
                UpdateFileType.ASSET_COLLECTIONS: asset_collections_file,
                UpdateFileType.ASSET_COLLECTIONS_MAPPINGS: asset_collections_mappings_file,
            }

        return updates
