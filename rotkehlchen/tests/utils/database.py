import os
import random
from dataclasses import asdict
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING, Any
from unittest.mock import _patch, patch

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import BlockchainAccountData, BlockchainAccounts
from rotkehlchen.chain.evm.nodes import populate_rpc_nodes_in_database
from rotkehlchen.constants.misc import USERDB_NAME
from rotkehlchen.db.checks import db_script_normalizer
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.constants import DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.types import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def maybe_include_etherscan_key(db: DBHandler, include_etherscan_key: bool) -> None:
    if not include_etherscan_key:
        return
    # Add the tests only etherscan API key
    if os.environ.get('MATRIX_JOB', 'others') == 'api':
        eth_api_key = 'R7QNMZJF1Z5EZM96GMSZSQKHQK3V2TBKW5'
    else:
        eth_api_key = '8JT7WQBB2VQP5C3416Y8X3S8GBA3CVZKP4'

    with db.user_write() as write_cursor:
        db.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.ETHERSCAN,
                api_key=ApiKey(eth_api_key),
            )])


def maybe_include_cryptocompare_key(db: DBHandler, include_cryptocompare_key: bool) -> None:
    if not include_cryptocompare_key:
        return
    keys = [
        'a4a36d7fd1835cc1d757186de8e7357b4478b73923933d09d3689140ecc23c03',
        'e929bcf68fa28715fa95f3bfa3baa3b9a6bc8f12112835586c705ab038ee06aa',
        '5159ca00f2579ef634b7f210ad725550572afbfb44e409460dd8a908d1c6416a',
        '6781b638eca6c3ca51a87efcdf0b9032397379a0810c5f8198a25493161c318d',
    ]
    # Add the tests only etherscan API key
    with db.user_write() as write_cursor:
        db.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.CRYPTOCOMPARE,
                api_key=ApiKey(random.choice(keys)),
            )])


def add_blockchain_accounts_to_db(db: DBHandler, blockchain_accounts: BlockchainAccounts) -> None:
    try:
        with db.user_write() as cursor:
            for name, value in asdict(blockchain_accounts).items():
                db.add_blockchain_accounts(
                    write_cursor=cursor,
                    account_data=[BlockchainAccountData(
                        chain=SupportedBlockchain(name.upper()),
                        address=x,
                    ) for x in value],
                )
    except InputError as e:
        raise AssertionError(
            f'Got error at test setup blockchain account addition: {e!s} '
            f'Probably using two different databases or too many fixtures initialized. '
            f'For example do not initialize both a rotki api server and another DB at same time',
        ) from e


def add_settings_to_test_db(
        db: DBHandler,
        db_settings: dict[str, Any] | None,
        ignored_assets: list[Asset] | None,
        data_migration_version: int | None,
) -> None:
    settings = {
        # DO not submit usage analytics during tests
        'submit_usage_analytics': False,
        'main_currency': DEFAULT_TESTS_MAIN_CURRENCY,
    }
    # Set the given db_settings. The pre-set values have priority unless overridden here
    if db_settings is not None:
        settings.update(db_settings)

    with db.user_write() as write_cursor:
        db.set_settings(write_cursor=write_cursor, settings=ModifiableDBSettings(**settings))  # type: ignore
        if ignored_assets:
            for asset in ignored_assets:
                db.add_to_ignored_assets(write_cursor=write_cursor, asset=asset)

    if data_migration_version is not None:
        with db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('last_data_migration', data_migration_version),
            )


def add_tags_to_test_db(db: DBHandler, tags: list[dict[str, Any]]) -> None:
    with db.user_write() as cursor:
        for tag in tags:
            db.add_tag(
                cursor,
                name=tag['name'],
                description=tag.get('description', None),
                background_color=tag['background_color'],
                foreground_color=tag['foreground_color'],
            )


def add_manually_tracked_balances_to_test_db(
        db: DBHandler,
        balances: list[ManuallyTrackedBalance],
) -> None:
    with db.user_write() as cursor:
        db.add_manually_tracked_balances(cursor, balances)


def mock_dbhandler_update_owned_assets() -> _patch:
    """Just make sure update owned assets does nothing for older DB tests"""
    return patch(
        'rotkehlchen.db.dbhandler.DBHandler.update_owned_assets_in_globaldb',
        lambda x, y: None,
    )


def mock_dbhandler_sync_globaldb_assets() -> _patch:
    """Just make sure add globalds assetids does nothing for older DB tests"""
    return patch(
        'rotkehlchen.db.dbhandler.DBHandler.sync_globaldb_assets',
        lambda x, y: None,
    )


def mock_db_schema_sanity_check() -> _patch:
    return patch(
        'rotkehlchen.db.drivers.gevent.DBConnection.schema_sanity_check',
        new=lambda x: None,
    )


def _use_prepared_db(user_data_dir: Path, filename: str) -> None:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', filename),
        user_data_dir / USERDB_NAME,
    )


def perform_new_db_unlock_actions(db: DBHandler, new_db_unlock_actions: tuple[str]) -> None:
    """Decide actions to perform at new DB unlock for a specific test depending on arguments"""
    if 'rpc_nodes' in new_db_unlock_actions:
        with (
            db.user_write() as write_cursor,
            GlobalDBHandler().conn.read_ctx() as globaldb_cursor,
        ):
            populate_rpc_nodes_in_database(
                db_write_cursor=write_cursor,
                globaldb_cursor=globaldb_cursor,
            )


def run_no_db_upgrades(self) -> bool:
    """Patched version of DBUpgradeManager to not run any upgrades but still
    return true for fresh DB and false otherwise

    Keep up to date with actual upgrade_manager.py:DBUpgradeError.run_upgrades
    """
    with self.db.conn.write_ctx() as cursor:
        try:
            self.db.get_setting(cursor, 'version')
        except sqlcipher.OperationalError:  # pylint: disable=no-member
            return True  # fresh database. Nothing to upgrade.

    return False


def clean_ignored_assets(database: DBHandler):
    """Some tests need to be simplified by removing all pre-ignored assets
    from the global DB sync or elsewhere so they start clean"""
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM multisettings WHERE name=?', ('ignored_asset',))


def column_exists(cursor: 'DBCursor', table_name: str, column_name: str) -> bool:
    columns = [row[1] for row in cursor.execute(f'PRAGMA table_info({table_name})')]
    return column_name in columns


def index_exists(cursor: 'DBCursor', name: str, schema: str | None = None) -> bool:
    exists: bool = cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=?", (name,),
    ).fetchone()[0] == 1
    if exists and schema is not None:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,))
        return db_script_normalizer(cursor.fetchone()[0].lower()) == db_script_normalizer(schema.lower())  # noqa: E501
    return exists
