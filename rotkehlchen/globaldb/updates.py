import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.typing import AssetData, AssetType
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

from .handler import GlobalDBHandler, initialize_globaldb

log = logging.getLogger(__name__)

ASSETS_VERSION_KEY = 'assets_version'


def executeall(cursor: sqlite3.Cursor, statements: str) -> None:
    """Splits all statements and execute()s one by one to avoid the
    commit that executescript would do.

    TODO: Is there a better way? Couldn't find one
    """
    for statement in statements.split(';'):
        if statement == '':
            continue
        cursor.execute(statement)


def _replace_assets_from_db(
        connection: sqlite3.Connection,
        sourcedb_path: Path,
) -> None:
    cursor = connection.cursor()
    cursor.executescript(f"""
    ATTACH DATABASE "{sourcedb_path}" AS other_db;
    PRAGMA foreign_keys = OFF;
    DELETE FROM assets;
    DELETE FROM ethereum_tokens;
    DELETE FROM underlying_tokens_list;
    DELETE FROM common_asset_details;
    INSERT INTO assets SELECT * FROM other_db.assets;
    INSERT INTO ethereum_tokens SELECT * FROM other_db.ethereum_tokens;
    INSERT INTO underlying_tokens_list SELECT * FROM other_db.underlying_tokens_list;
    INSERT INTO common_asset_details SELECT * FROM other_db.common_asset_details;
    INSERT OR REPLACE INTO settings(name, value) VALUES("{ASSETS_VERSION_KEY}",
    (SELECT value FROM other_db.settings WHERE name="{ASSETS_VERSION_KEY}")
    );
    PRAGMA foreign_keys = ON;
    DETACH DATABASE "other_db";
    """)


def _force_remote(cursor: sqlite3.Cursor, local_asset: Asset, full_insert: str) -> None:
    """Force the remote entry into the database by deleting old one and doing the full insert.

    May raise an sqlite3 error if something fails.
    """
    cursor.executescript('PRAGMA foreign_keys = OFF;')
    if local_asset.asset_type == AssetType.ETHEREUM_TOKEN:
        token = EthereumToken.from_asset(local_asset)
        cursor.execute(
            'DELETE FROM ethereum_tokens WHERE address=?;',
            (token.ethereum_address,),  # type: ignore  # token != None
        )
    else:
        cursor.execute(
            'DELETE FROM common_asset_details WHERE asset_id=?;',
            (local_asset.identifier,),
        )
    cursor.execute(
        'DELETE FROM assets WHERE identifier=?;',
        (local_asset.identifier,),
    )
    cursor.executescript('PRAGMA foreign_keys = ON;')
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


class AssetsUpdater():

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        self.local_assets_version = GlobalDBHandler().get_setting_value(ASSETS_VERSION_KEY, 0)
        self.last_remote_checked_version = None
        self.conflicts: List[Tuple[AssetData, AssetData]] = []
        self.assets_re = re.compile(r'.*INSERT +INTO +assets\( *identifier *, *type *, *name *, *symbol *, *started *, *swapped_for *, *coingecko *, *cryptocompare *, *details_reference *\) +VALUES\((.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?)\).*?')  # noqa: E501
        self.ethereum_tokens_re = re.compile(r'.*INSERT +INTO +ethereum_tokens\( *address *, *decimals *, *protocol *\) +VALUES\((.*?),(.*?),(.*?)\).*')  # noqa: E501
        self.common_asset_details_re = re.compile(r'.*INSERT +INTO +common_asset_details\( *asset_id *, *forked *\) +VALUES\((.*?),(.*?)\).*')  # noqa: E501
        self.string_re = re.compile(r'.*"(.*?)".*')
        self.branch = 'master'
        if not getattr(sys, 'frozen', False):
            # not packaged -- must be in develop mode
            self.branch = 'develop'

    def _get_remote_info_json(self) -> Dict[str, Any]:
        url = f'https://raw.githubusercontent.com/rotki/assets/{self.branch}/updates/info.json'
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query Github {url} during assets update: {str(e)}') from e  # noqa: E501

        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(
                f'Could not parse assets update info as json from Github: {response.text}',
            ) from e

        return json_data

    def check_for_updates(self) -> Tuple[int, int, int]:
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
            raise RemoteError(f'Didnt find expected key {str(e)} in github assets json during update') from e  # noqa: E501
        except ValueError as e:
            raise RemoteError(f'{str(e)} in github assets json during update') from e

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
        match = self.assets_re.match(insert_text)
        if match is None:
            raise DeserializationError(
                f'At asset DB update could not parse asset data out of {insert_text}',
            )
        if len(match.groups()) != 9:
            raise DeserializationError(
                f'At asset DB update could not parse asset data out of {insert_text}',
            )

        raw_type = self._parse_str(match.group(2), 'asset type', insert_text)
        asset_type = AssetType.deserialize_from_db(raw_type)
        raw_started = self._parse_optional_int(match.group(5), 'started', insert_text)
        started = Timestamp(raw_started) if raw_started else None
        return ParsedAssetData(
            identifier=self._parse_str(match.group(1), 'identifier', insert_text),
            asset_type=asset_type,
            name=self._parse_str(match.group(3), 'name', insert_text),
            symbol=self._parse_str(match.group(4), 'symbol', insert_text),
            started=started,
            swapped_for=self._parse_optional_str(match.group(6), 'swapped_for', insert_text),
            coingecko=self._parse_optional_str(match.group(7), 'coingecko', insert_text),
            cryptocompare=self._parse_optional_str(match.group(8), 'cryptocompare', insert_text),
        )

    def _parse_ethereum_token_data(self, insert_text: str) -> Tuple[ChecksumEthAddress, Optional[int], Optional[str]]:  # noqa: E501
        match = self.ethereum_tokens_re.match(insert_text)
        if match is None:
            raise DeserializationError(
                f'At asset DB update could not parse ethereum token data out '
                f'of {insert_text}',
            )

        if len(match.groups()) != 3:
            raise DeserializationError(
                f'At asset DB update could not parse ethereum token data out of {insert_text}',
            )

        return (
            deserialize_ethereum_address(self._parse_str(match.group(1), 'address', insert_text)),
            self._parse_optional_int(match.group(2), 'decimals', insert_text),
            self._parse_optional_str(match.group(3), 'protocol', insert_text),
        )

    def _parse_full_insert(self, insert_text: str) -> AssetData:
        """Parses the full insert line for an asset to give information for the conflict to the user

        Note: In the future this needs to be different for each version
        May raise:
        - DeserializationError if the appropriate data is not found or if it can't
        be properly parsed.
        """
        asset_data = self._parse_asset_data(insert_text)
        forked = address = decimals = protocol = None
        if asset_data.asset_type == AssetType.ETHEREUM_TOKEN:
            address, decimals, protocol = self._parse_ethereum_token_data(insert_text)
        else:
            match = self.common_asset_details_re.match(insert_text)
            if match is None:
                raise DeserializationError(
                    f'At asset DB update could not parse common asset '
                    f'details data out of {insert_text}',
                )
            forked = self._parse_optional_str(match.group(2), 'forked', insert_text)

        return AssetData(  # types are not really proper here (except for asset_type)
            identifier=asset_data.identifier,
            name=asset_data.name,
            symbol=asset_data.symbol,
            asset_type=asset_data.asset_type,
            started=asset_data.started,
            forked=forked,
            swapped_for=asset_data.swapped_for,
            ethereum_address=address,
            decimals=decimals,
            cryptocompare=asset_data.cryptocompare,
            coingecko=asset_data.coingecko,
            protocol=protocol,
        )

    def _apply_single_version_update(
            self,
            cursor: sqlite3.Cursor,
            version: int,
            text: str,
            conflicts: Optional[Dict[Asset, Literal['remote', 'local']]],
    ) -> None:
        lines = text.splitlines()
        for action, full_insert in zip(*[iter(lines)] * 2):
            if full_insert == '*':
                full_insert = action

            try:
                remote_asset_data = self._parse_full_insert(full_insert)
            except DeserializationError as e:
                self.msg_aggregator.add_warning(
                    f'Skipping entry during assets update to v{version} due '
                    f'to a deserialization error. {str(e)}',
                )
                continue

            local_asset: Optional[Asset] = None
            try:
                local_asset = Asset(remote_asset_data.identifier)
            except UnknownAsset:
                pass

            try:
                executeall(cursor, action)
                if local_asset is not None:
                    AssetResolver().clean_memory_cache(local_asset.identifier.lower())
            except sqlite3.Error:  # https://docs.python.org/3/library/sqlite3.html#exceptions
                if local_asset is None:
                    try:  # if asset is not known then simply do an insertion
                        executeall(cursor, full_insert)
                    except sqlite3.Error as e:
                        self.msg_aggregator.add_warning(
                            f'Failed to add asset {remote_asset_data.identifier} in the '
                            f'DB during the v{version} assets update. Skipping entry. '
                            f'Error: {str(e)}',
                        )
                    continue  # fail or succeed continue to next entry

                # otherwise asset is known, so it's a conflict. Check if we can resolve
                resolution = conflicts.get(local_asset) if conflicts else None
                if resolution == 'local':
                    # do nothing, keep local
                    continue
                if resolution == 'remote':
                    try:
                        _force_remote(cursor, local_asset, full_insert)
                    except sqlite3.Error as e:
                        self.msg_aggregator.add_warning(
                            f'Failed to resolve conflict for {remote_asset_data.identifier} in '
                            f'the DB during the v{version} assets update. Skipping entry. '
                            f'Error: {str(e)}',
                        )
                    continue  # fail or succeed continue to next entry

                # else can't resolve. Mark it for the user to resolve.
                local_data = AssetResolver().get_asset_data(local_asset.identifier, False)
                self.conflicts.append((local_data, remote_asset_data))

        # at the very end update the current version in the DB
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (ASSETS_VERSION_KEY, str(version)),
        )

    def perform_update(
            self,
            up_to_version: Optional[int],
            conflicts: Optional[Dict[Asset, Literal['remote', 'local']]],
    ) -> Optional[List[Dict[str, Any]]]:
        """Performs an asset update by downloading new changes from the remote

        If `up_to_version` is given then changes up to and including that version are made.
        If not all possible changes are applied.

        For success returns None. If there is conflicts a list of conflicting
        assets identifiers is going to be returned.

        May raise:
            - RemoteError if there is a problem querying Github
        """
        if self.last_remote_checked_version is None:
            self.check_for_updates()

        self.conflicts = []  # reset the stored conflicts
        infojson = self._get_remote_info_json()
        local_schema_version = GlobalDBHandler().get_schema_version()
        data_directory = GlobalDBHandler()._data_directory
        assert data_directory is not None, 'data directory should be initialized at this point'
        global_db_path = data_directory / 'global_data' / 'global.db'
        with TemporaryDirectory() as tmpdirname:
            tempdbpath = Path(tmpdirname) / 'temp.db'
            connection = initialize_globaldb(tempdbpath)
            _replace_assets_from_db(connection, global_db_path)
            self._perform_update(
                connection=connection,
                conflicts=conflicts,
                local_schema_version=local_schema_version,
                infojson=infojson,
                up_to_version=up_to_version,
            )
            if len(self.conflicts) != 0:
                # close the temporary DB and return the conflicts
                connection.close()
                return [
                    {'identifier': x[0].identifier, 'local': x[0].serialize(), 'remote': x[1].serialize()}  # noqa: E501
                    for x in self.conflicts
                ]

            # otherwise we are sure the DB will work without conflicts so let's
            # now move the data to the actual global DB
            connection.close()
            connection = GlobalDBHandler()._conn
            _replace_assets_from_db(connection, tempdbpath)
            return None

    def _perform_update(
            self,
            connection: sqlite3.Connection,
            conflicts: Optional[Dict[Asset, Literal['remote', 'local']]],
            local_schema_version: int,
            infojson: Dict[str, Any],
            up_to_version: Optional[int],
    ) -> None:
        version = self.local_assets_version + 1
        target_version = min(up_to_version, self.last_remote_checked_version) if up_to_version else self.last_remote_checked_version   # type: ignore # noqa: E501
        # type ignore since due to check_for_updates we know last_remote_checked_version exists
        cursor = connection.cursor()
        while version <= target_version:
            try:
                min_schema_version = infojson['updates'][str(version)]['min_schema_version']
                max_schema_version = infojson['updates'][str(version)]['max_schema_version']
                if local_schema_version < min_schema_version or local_schema_version > max_schema_version:  # noqa: E501
                    self.msg_aggregator.add_warning(
                        f'Skipping assets update {version} since it requires a min '
                        f'schema of {min_schema_version} and max schema of {max_schema_version} '
                        f'while the local DB schema version is {local_schema_version}. '
                        f'You will have to follow an alternative method to '
                        f'obtain the assets of this update.',
                    )
                    cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        (ASSETS_VERSION_KEY, str(version)),
                    )
                    version += 1
                    continue
            except KeyError as e:
                log.error(
                    f'Remote info.json for version {version} did not contain '
                    f'key "{str(e)}". Skipping update.',
                )
                version += 1
                continue

            try:
                url = f'https://raw.githubusercontent.com/rotki/assets/{self.branch}/updates/{version}/updates.sql'  # noqa: E501
                response = requests.get(url)
            except requests.exceptions.RequestException as e:
                connection.rollback()
                raise RemoteError(f'Failed to query Github for {url} during assets update: {str(e)}') from e  # noqa: E501

            if response.status_code != 200:
                connection.rollback()
                raise RemoteError(
                    f'Github query for {url} failed with status code '
                    f'{response.status_code} and text: {response.text}',
                )

            self._apply_single_version_update(
                cursor=cursor,
                version=version,
                text=response.text,
                conflicts=conflicts,
            )
            version += 1

        if self.conflicts == []:
            connection.commit()
            return

        # In this case we have conflicts. Everything should also be rolled back
        connection.rollback()
