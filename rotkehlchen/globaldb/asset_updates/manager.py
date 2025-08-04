import logging
import os
from collections import defaultdict
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Final, Literal

import requests
import rsqlite

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetData
from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.utils import initialize_globaldb
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import is_production
from rotkehlchen.utils.network import query_file

from .parsers import AssetCollectionParser, AssetParser, MultiAssetMappingsParser
from .types import UpdateFileType

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ASSETS_VERSION_KEY: Final = 'assets_version'
ASSETS_UPDATES_URL: Final = 'https://raw.githubusercontent.com/rotki/assets/{branch}/updates/{version}/updates.sql'
ASSET_COLLECTIONS_UPDATES_URL: Final = 'https://raw.githubusercontent.com/rotki/assets/{branch}/updates/{version}/asset_collections_updates.sql'
ASSET_COLLECTIONS_MAPPINGS_UPDATES_URL: Final = 'https://raw.githubusercontent.com/rotki/assets/{branch}/updates/{version}/asset_collections_mappings_updates.sql'
FIRST_VERSION_WITH_COLLECTIONS: Final = 16
FIRST_GLOBAL_DB_VERSION_WITH_COLLECTIONS: Final = 4
FIRST_VERSION_WITH_SOLANA_TOKENS: Final = 37


def executeall(cursor: DBCursor, statements: str) -> None:
    """Splits all statements and execute()s one by one to avoid the
    commit that executescript would do.

    TODO: Is there a better way? Couldn't find one
    """
    for statement in statements.split(';'):
        if statement == '':
            continue
        cursor.execute(statement)


def _replace_assets_from_db_cursor(
        write_cursor: 'DBCursor',
        sourcedb_path: Path,
) -> None:
    # First handle token_kinds & asset_types since other tables reference it
    required_tables = [
        'token_kinds',
        'asset_types',
        'assets',
        'evm_tokens',
        'underlying_tokens_list',
        'common_asset_details',
        'asset_collections',
        'multiasset_mappings',
        'settings',
    ]
    script_parts = ['PRAGMA foreign_keys = OFF;']
    write_cursor.execute(f"ATTACH DATABASE '{sourcedb_path}' AS other_db;")
    if (  # add solana_tokens table only if source db version supports it
        (result := write_cursor.execute('SELECT value FROM other_db.settings WHERE name=?;', (ASSETS_VERSION_KEY,)).fetchone()) is not None and   # noqa: E501
        int(result[0]) >= FIRST_VERSION_WITH_SOLANA_TOKENS
    ):
        required_tables.append('solana_tokens')

    write_cursor.execute(
        """SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name IN ({})
        """.format(','.join('?' * len(required_tables))),
        required_tables,
    )
    if write_cursor.fetchone()[0] < len(required_tables):
        schemas = {}
        for table in required_tables:
            if (schema := write_cursor.execute(
                "SELECT sql FROM other_db.sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()):
                raw_schema = schema[0]
                schema_def = raw_schema.split('CREATE TABLE')[1].split('(', 1)[1]
                schemas[table] = schema_def

        for table, schema in schemas.items():
            script_parts.append(f'CREATE TABLE IF NOT EXISTS {table} ({schema};')

    # Always do the delete and insert
    for table in required_tables:
        script_parts.extend([
            f'DELETE FROM {table};',
            f'INSERT INTO {table} SELECT * FROM other_db.{table};',
        ])
    script_parts.extend([
        f"INSERT OR REPLACE INTO settings(name, value) VALUES('{ASSETS_VERSION_KEY}',"
        f"(SELECT value FROM other_db.settings WHERE name='{ASSETS_VERSION_KEY}'));",
        'PRAGMA foreign_keys = ON;',
        "DETACH DATABASE 'other_db';",
    ])
    write_cursor.executescript('\n'.join(script_parts))


def _replace_assets_from_db(
        connection: 'DBConnection',
        sourcedb_path: Path,
) -> None:
    """Replace asset-related tables with data from source database.

    Handles: token_kinds, asset_types, assets, evm_tokens, solana_tokens,
    underlying_tokens_list, common_asset_details, asset_collections, multiasset_mappings.
    """
    with connection.write_ctx() as write_cursor:
        _replace_assets_from_db_cursor(write_cursor, sourcedb_path)


def _force_remote_asset(cursor: DBCursor, local_asset: Asset, full_insert: str) -> None:
    """Force the remote entry into the database by deleting old one and doing the full insert.

    May raise an sqlite3 error if something fails.
    """
    # we get the multiasset and underlying asset mappings before removing the asset because
    # these mappings get deleted when the asset is removed because of foreign key relation
    multiasset_mappings = cursor.execute(  # get its multiasset mappings
        'SELECT collection_id, asset FROM multiasset_mappings WHERE asset=?;',
        (local_asset.identifier,),
    ).fetchall()
    underlying_assets = cursor.execute(  # get its underlying_assets mappings
        'SELECT parent_token_entry, weight, identifier FROM underlying_tokens_list '
        'WHERE identifier=? OR parent_token_entry=?;',
        (local_asset.identifier, local_asset.identifier),
    ).fetchall()

    try:
        collection = cursor.execute(
            'SELECT * FROM asset_collections WHERE main_asset=?;',
            (local_asset.identifier,),
        ).fetchone()
    except rsqlite.Error:
        # If query fails due to missing main_asset
        # column (pre-v10 schema), set collection to None
        collection = None

    cursor.execute(
        'DELETE FROM assets WHERE identifier=?;',
        (local_asset.identifier,),
    )

    # Insert new entry. Since identifiers are the same, no foreign key constraints should break
    executeall(cursor, full_insert)
    if collection:
        cursor.execute(  # reinsert the collection since it was cascade-deleted
            'INSERT OR IGNORE INTO asset_collections VALUES (?, ?, ?, ?)',
            collection,
        )
    # now add the old mappings back into the db
    if len(multiasset_mappings) > 0:
        cursor.executemany(  # add the old multiasset mappings
            'INSERT INTO multiasset_mappings (collection_id, asset) VALUES (?, ?);',
            multiasset_mappings,
        )
    if len(underlying_assets) > 0:
        cursor.executemany(  # add the old underlying assets
            'INSERT INTO underlying_tokens_list (parent_token_entry, weight, identifier) '
            'VALUES (?, ?, ?);',
            underlying_assets,
        )
    AssetResolver.clean_memory_cache(local_asset.identifier.lower())


class AssetsUpdater:

    def __init__(self, msg_aggregator: 'MessagesAggregator', globaldb: 'GlobalDBHandler') -> None:
        self.globaldb = globaldb
        self.msg_aggregator = msg_aggregator
        self.local_assets_version = globaldb.get_setting_value(ASSETS_VERSION_KEY, 0)
        self.last_remote_checked_version = -1  # integer value that represents no update
        self.conflicts: dict[str, tuple[AssetData, AssetData]] = {}
        self.asset_parser = AssetParser()
        self.asset_collection_parser = AssetCollectionParser()
        self.multiasset_mappings_parser = MultiAssetMappingsParser()
        self.branch = os.getenv('GITHUB_BASE_REF', 'develop')
        if is_production():
            self.branch = 'master'

    def _get_remote_info_json(self) -> dict[str, Any]:
        url = f'https://raw.githubusercontent.com/rotki/assets/{self.branch}/updates/info.json'
        try:
            response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query Github {url} during assets update: {e!s}') from e

        try:
            json_data = response.json()
        except requests.exceptions.RequestException as e:
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
        self.local_assets_version = self.globaldb.get_setting_value(ASSETS_VERSION_KEY, 0)
        json_data = self._get_remote_info_json()
        local_schema_version = self.globaldb.get_schema_version()
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

    def _process_asset_collection(
            self,
            connection: 'DBConnection',
            action: str,
            full_insert: str,
            version: int,
    ) -> None:
        """Process the insertion of a new asset_collection.
        May raise:
            - DeserializationError
        """
        result = self.asset_collection_parser.parse(
            insert_text=full_insert,
            connection=connection,
            version=version,
        )
        try:
            with connection.savepoint_ctx() as cursor:
                executeall(cursor, action)
        except rsqlite.Error:
            try:
                with connection.savepoint_ctx() as cursor:
                    executeall(cursor, full_insert)
            except rsqlite.Error as e:
                log.error(
                    f'Failed to edit or add asset collection with values {result}. '
                    f'{action}. Error: {e!s}',
                )

    def _process_multiasset_mapping(
            self,
            connection: 'DBConnection',
            action: str,
            full_insert: str,
            version: int,
    ) -> None:
        """
        Process the insertion of a new asset_collection mapping
        May raise:
        - DeserializationError
        - UnknownAsset
        """
        result = self.multiasset_mappings_parser.parse(
            insert_text=full_insert,
            connection=connection,
            version=version,
        )
        try:
            with connection.savepoint_ctx() as cursor:
                executeall(cursor, action)
        except rsqlite.Error:
            try:
                with connection.savepoint_ctx() as cursor:
                    executeall(cursor, full_insert)
            except rsqlite.Error as e:
                log.error(
                    f'Failed to edit asset collection mapping with values {result}. '
                    f'{action}. Error: {e!s}',
                )

    def _handle_asset_update(
            self,
            connection: 'DBConnection',
            remote_asset_data: AssetData,
            assets_conflicts: dict[Asset, Literal['remote', 'local']] | None,
            action: str,
            full_insert: str,
            version: int,
    ) -> None:
        """
        Given the already processed information for an asset try to store it in the globaldb
        and if it is not possible due to conflicts mark it to resolve later.
        """
        local_asset: Asset | None = None
        with suppress(UnknownAsset):
            # we avoid querying the packaged db to prevent the copy of constant assets
            local_asset = Asset(remote_asset_data.identifier).check_existence(query_packaged_db=False)  # noqa: E501

        try:
            with connection.savepoint_ctx() as cursor:
                # if the action is to update an asset, but it doesn't exist in the DB
                if action.strip().startswith('UPDATE') and cursor.execute(
                    'SELECT COUNT(*) FROM assets WHERE identifier=?',
                    (remote_asset_data.identifier,),
                ).fetchone()[0] == 0:
                    executeall(cursor, full_insert)  # we apply the full insert query
                else:
                    executeall(cursor, action)

                if local_asset is not None:
                    AssetResolver().clean_memory_cache(identifier=local_asset.identifier)
        except rsqlite.Error:  # https://docs.python.org/3/library/sqlite3.html#exceptions
            if local_asset is None:
                try:  # if asset is not known then simply do an insertion
                    with connection.savepoint_ctx() as cursor:
                        executeall(cursor, full_insert)
                except rsqlite.Error as e:
                    self.msg_aggregator.add_warning(
                        f'Failed to add asset {remote_asset_data.identifier} in the '
                        f'DB during the v{version} assets update. Skipping entry. '
                        f'Error: {e!s}',
                    )
                return  # fail or succeed continue to next entry

            if local_asset is not None:
                AssetResolver().clean_memory_cache(local_asset.identifier.lower())

            # otherwise asset is known, so it's a conflict. Check if we can resolve
            try:
                resolution = assets_conflicts[local_asset] if assets_conflicts is not None else None  # noqa: E501
            except KeyError:
                resolution = None

            if resolution == 'local':
                # do nothing, keep local
                return
            if resolution == 'remote':
                try:
                    with connection.savepoint_ctx() as cursor:
                        _force_remote_asset(cursor, local_asset, full_insert)
                except rsqlite.Error as e:
                    self.msg_aggregator.add_warning(
                        f'Failed to resolve conflict for {remote_asset_data.identifier} in '
                        f'the DB during the v{version} assets update. Skipping entry. '
                        f'Error: {e!s}',
                    )
                return  # fail or succeed continue to next entry

            # else can't resolve. Mark it for the user to resolve.
            # TODO: When assets refactor is finished, remove the usage of AssetData here
            local_data = self.globaldb.get_all_asset_data(
                mapping=False,
                serialized=False,
                specific_ids=[local_asset.identifier],
            )[0]
            # always take the last one, if there is multiple conflicts for a single asset
            self.conflicts[local_asset.identifier] = (local_data, remote_asset_data)

    def _apply_single_version_update(
            self,
            connection: 'DBConnection',
            version: int,
            text: str,
            assets_conflicts: dict[Asset, Literal['remote', 'local']] | None,
            update_file_type: UpdateFileType,
    ) -> None:
        """
        Process the queried file and apply special rules depending on the type of file
        (assets updates, collections updates or mappings updates) set in update_file_type.

        If conflicts appear while processing the assets those are handled. Deserialization
        errors are caught and the user is warned about them.
        """
        lines = [x for x in text.splitlines() if x.strip() != '']
        try:  # strip() check above is to remove empty lines (say trailing newline in the file
            for action_raw, full_insert_raw in zip(*[iter(lines)] * 2, strict=True):

                action: str = action_raw.strip()
                if (full_insert := full_insert_raw.strip()) == '*':
                    full_insert = action

                # We now enforce single quote. If any of the old updates some here
                # with double quotes we need to replace them here
                # https://github.com/rotki/rotki/issues/6368
                # TODO: Get rid of all those
                full_insert = self.asset_parser.standardize_quotes(full_insert)
                action = self.asset_parser.standardize_quotes(action)

                if (
                    (update_file_type in (  # handle update/delete for collections
                        UpdateFileType.ASSET_COLLECTIONS_MAPPINGS,
                        UpdateFileType.ASSET_COLLECTIONS,
                    ) and action.startswith(('UPDATE', 'DELETE'))) or
                    (update_file_type == UpdateFileType.ASSETS and action.startswith('DELETE'))  # handle deleting assets  # noqa: E501
                ):
                    try:
                        with connection.write_ctx() as write_cursor:
                            executeall(write_cursor, action)
                    except rsqlite.Error as e:
                        log.error(
                            f'Failed to apply update/delete statement {action} from '
                            f'{update_file_type} update v{version} due to {e}. Skipping... ',
                        )

                elif update_file_type == UpdateFileType.ASSETS:  # update or insert assets
                    remote_asset_data = None
                    try:
                        remote_asset_data = self.asset_parser.parse(
                            insert_text=full_insert,
                            connection=connection,
                            version=version,
                        )
                    except DeserializationError as e:
                        log.error(
                            f'Failed to add asset with action {action} during update to v{version}',  # noqa: E501
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
                            version=version,
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
                            version=version,
                        )
                    except DeserializationError as e:
                        self.msg_aggregator.add_warning(
                            f'Skipping entry during assets collection multimapping update due '
                            f'to a deserialization error. {e!s}',
                        )
                    except UnknownAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Tried to add unknown asset {e.identifier} to collection of assets. Skipping',  # noqa: E501
                        )
        except ValueError:
            self.msg_aggregator.add_error(
                f'Last entry of update {update_file_type} has an odd number of '
                f'lines. Skipping. Report this to the developers',
            )

        # at the very end update the current version in the DB
        connection.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (ASSETS_VERSION_KEY, str(version)),
        )

    def perform_update(
            self,
            up_to_version: int | None,
            conflicts: dict[Asset, Literal['remote', 'local']] | None,
    ) -> list[dict[str, Any]] | None:
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

        self.conflicts = {}  # reset the stored conflicts
        infojson = self._get_remote_info_json()
        local_schema_version = self.globaldb.get_schema_version()
        data_directory = self.globaldb._data_directory
        assert data_directory is not None, 'data directory should be initialized at this point'
        global_db_path = data_directory / GLOBALDIR_NAME / GLOBALDB_NAME

        # We retrieve first all the files required for the different updates that will be performed
        updates = self._retrieve_update_files(
            local_schema_version=local_schema_version,
            infojson=infojson,
            up_to_version=up_to_version,
        )

        with TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)
            temp_db_name = 'temp.db'
            # here, the global db just needs to be initialised and not
            # configured since its already up to date with the latest data.
            temp_db_connection, _ = initialize_globaldb(
                global_dir=tmpdir,
                db_filename=temp_db_name,
                sql_vm_instructions_cb=self.globaldb.conn.sql_vm_instructions_cb,
            )

            # open write_ctx early to avoid modifications in the globaldb during the update
            # process since we ignore any possible change in the user globaldb once we started
            # the update.
            with self.globaldb.conn.write_ctx() as globaldb_write_cursor:
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
                        for x in self.conflicts.values()
                    ]

                # otherwise we are sure the DB will work without conflicts so let's
                # now move the data to the actual global DB
                log.info('Finishing assets update. Replacing users globaldb with the updated information')  # noqa: E501
                _replace_assets_from_db_cursor(globaldb_write_cursor, tmpdir / temp_db_name)

        return None

    def _perform_update(
            self,
            connection: 'DBConnection',
            assets_conflicts: dict[Asset, Literal['remote', 'local']] | None,
            up_to_version: int | None,
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

        if len(self.conflicts) == 0:
            connection.commit()
            return

        # In this case we have conflicts. Everything should also be rolled back
        connection.rollback()

    def _fetch_single_update_file(
            self,
            url: str,
    ) -> str:
        """Fetch a single update file from github and return its content.
        If the file is not found then return an empty string.

        May raise:
        - RemoteError if failed to fetch the file with status code other that 404."""
        try:
            return query_file(url=url, is_json=False)
        except RemoteError as e:
            if e.error_code == HTTPStatus.NOT_FOUND:
                log.warning(f'Assets update file not found from {url}: {e!s}')
                return ''  # this is a no-op when the upgrade doesn't have any mappings
            else:
                raise

    def _retrieve_update_files(
            self,
            local_schema_version: int,
            infojson: dict[str, Any],
            up_to_version: int | None,
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

            assets_file = self._fetch_single_update_file(url=assets_url)

            if version >= FIRST_VERSION_WITH_COLLECTIONS:
                asset_collections_file = self._fetch_single_update_file(url=asset_collections_url)
                asset_collections_mappings_file = self._fetch_single_update_file(url=asset_collections_mappings_url)  # noqa: E501
            else:
                asset_collections_file, asset_collections_mappings_file = '', ''

            updates[version] = {
                UpdateFileType.ASSETS: assets_file,
                UpdateFileType.ASSET_COLLECTIONS: asset_collections_file,
                UpdateFileType.ASSET_COLLECTIONS_MAPPINGS: asset_collections_mappings_file,
            }

        return updates

    def apply_pending_compatible_updates(self) -> None:
        """Apply any pending asset updates that are compatible with the current DB version
        before upgrading to target_db_version.

        This ensures we don't miss any asset updates that would become incompatible
        after the DB upgrade.
        """
        try:
            max_compatible_version = None
            info_json = self._get_remote_info_json()
            if (latest_assets_version := info_json.get('latest')) is None:
                log.error('Missing latest version in info json. Skipping updates')
                return

            if (current_db_version := self.globaldb.get_schema_version()) < FIRST_GLOBAL_DB_VERSION_WITH_COLLECTIONS:  # noqa: E501
                log.error(f'Global DB version too old for collections. {current_db_version=}, required={FIRST_GLOBAL_DB_VERSION_WITH_COLLECTIONS}')  # noqa: E501
                return

            start_version = max(FIRST_VERSION_WITH_COLLECTIONS, self.local_assets_version + 1)
            # Find the highest compatible assets version for current DB version
            for version in range(start_version, latest_assets_version + 1):
                update_info = info_json['updates'][str(version)]
                if update_info['min_schema_version'] <= current_db_version <= update_info['max_schema_version']:  # noqa: E501
                    max_compatible_version = version
                elif update_info['min_schema_version'] > current_db_version:
                    break  # Stop at first incompatible version

            # Apply updates up to the highest compatible version
            if max_compatible_version is not None:
                log.debug(
                    'Found compatible assets version. Updating assets',
                    from_version=self.local_assets_version,
                    to_version=max_compatible_version,
                    global_db_version=current_db_version,
                )

                self.perform_update(
                    up_to_version=max_compatible_version,
                    conflicts=defaultdict(lambda: 'remote'),  # always choose remote
                )
        except (DeserializationError, RemoteError, UnknownAsset, KeyError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(f'Failed to apply pending asset updates during global DB upgrade due to: {msg}')  # noqa: E501
