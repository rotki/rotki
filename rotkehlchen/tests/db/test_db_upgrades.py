import json
import os
import shutil
import urllib.parse
from contextlib import ExitStack, contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_COW, A_ETH
from rotkehlchen.constants.misc import (
    AIRDROPSDIR_NAME,
    ALLASSETIMAGESDIR_NAME,
    APPDIR_NAME,
    ASSETIMAGESDIR_NAME,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    IMAGESDIR_NAME,
    USERDB_NAME,
)
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.data_import.importers.constants import ROTKI_EVENT_PREFIX
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.checks import sanity_check_impl
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.upgrade_manager import (
    MIN_SUPPORTED_USER_DB_VERSION,
    UPGRADES_LIST,
    DBUpgradeProgressHandler,
)
from rotkehlchen.db.upgrades.v37_v38 import DEFAULT_POLYGON_NODES_AT_V38
from rotkehlchen.db.upgrades.v39_v40 import PREFIX
from rotkehlchen.db.utils import table_exists
from rotkehlchen.errors.api import RotkehlchenPermissionError
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.exchanges.coinbase import CB_EVENTS_PREFIX
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.tests.utils.constants import A_LTC
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    column_exists,
    mock_db_schema_sanity_check,
    mock_dbhandler_sync_globaldb_assets,
    mock_dbhandler_update_owned_assets,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    ChainID,
    Location,
    SupportedBlockchain,
    Timestamp,
    TokenKind,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import HexBytes
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def make_serialized_group_identifier(location: Location, raw_group_identifier: bytes) -> str:
    """Creates a serialized group identifier using the logic at the moment of v32_v33 upgrade"""
    if location == Location.KRAKEN or raw_group_identifier.startswith(b'rotki_events'):
        return raw_group_identifier.decode()

    hex_representation = raw_group_identifier.hex()
    if hex_representation.startswith('0x') is True:
        return hex_representation
    return '0x' + hex_representation


def assert_tx_hash_is_bytes(
        old: list,
        new: list,
        tx_hash_index: int,
        is_history_event: bool = False,
) -> None:
    """This function does the following:
    - Checks that the entries for `tx_hash_index` provided for `old` is string type.
    - Checks that the entries for `tx_hash_index` provided for `new` is bytes type.
    - Checks that comparing the entries after converting the bytes to its string equivalent yields
    the same as its `old` counterpart.
    """
    for z_old, z_new in zip(old, new, strict=True):
        assert isinstance(z_new[tx_hash_index], bytes)
        assert isinstance(z_old[tx_hash_index], str)
        l_new = list(z_new)
        if is_history_event is True:
            l_new[tx_hash_index] = make_serialized_group_identifier(
                location=Location.deserialize_from_db(l_new[4]),
                raw_group_identifier=l_new[1],
            )
        else:
            l_new[tx_hash_index] = str(deserialize_evm_tx_hash(l_new[tx_hash_index]))
        assert list(z_old) == l_new


@contextmanager
def target_patch(target_version: int):
    """Patches the upgrades to stop at target_version and also sets
    ROTKEHLCHEN_DB_VERSION to the target_version"""
    a = patch(
        'rotkehlchen.db.upgrade_manager.ROTKEHLCHEN_DB_VERSION',
        new=target_version,
    )
    b = patch(
        'rotkehlchen.db.dbhandler.ROTKEHLCHEN_DB_VERSION',
        new=target_version,
    )
    new_upgrades_list = [
        upgrade for upgrade in UPGRADES_LIST if upgrade.from_version < target_version
    ]

    c = patch(
        'rotkehlchen.db.upgrade_manager.UPGRADES_LIST',
        new=new_upgrades_list,
    )

    with a, b, c:
        yield (a, b, c)


def _init_db_with_target_version(
        target_version: int,
        user_data_dir: Path,
        msg_aggregator: MessagesAggregator,
        resume_from_backup: bool,
) -> DBHandler:
    no_tables_created_after_init = patch(
        'rotkehlchen.db.dbhandler.DB_SCRIPT_CREATE_TABLES',
        new='',
    )
    with ExitStack() as stack:
        stack.enter_context(target_patch(target_version=target_version))
        stack.enter_context(mock_db_schema_sanity_check())
        stack.enter_context(no_tables_created_after_init)
        if target_version <= 50:
            stack.enter_context(mock_dbhandler_update_owned_assets())
            stack.enter_context(mock_dbhandler_sync_globaldb_assets())
        return DBHandler(
            user_data_dir=user_data_dir,
            password='123',
            msg_aggregator=msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
            resume_from_backup=resume_from_backup,
        )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_26_to_27(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 26 to version 27.

    - Recreates balancer events, uniswap events, amm_swaps. Deletes balancer pools
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v26_rotkehlchen.db')
    db_v26 = _init_db_with_target_version(
        target_version=26,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    # Checks before migration
    cursor = db_v26.conn.cursor()
    assert cursor.execute(
        "SELECT COUNT(*) from used_query_ranges WHERE name LIKE 'uniswap%';",
    ).fetchone()[0] == 2
    assert cursor.execute(
        "SELECT COUNT(*) from used_query_ranges WHERE name LIKE 'balancer%';",
    ).fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges;').fetchone()[0] == 6
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from balancer_pools;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 1

    db_v26.logout()
    # Migrate to v27
    db = _init_db_with_target_version(
        target_version=27,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges;').fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 0

    # Finally also make sure that we have updated to the target version
    with db.conn.read_ctx() as cursor:
        assert db.get_setting(cursor, 'version') == 27
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_27_to_28(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 27 to version 28.

    - Adds a new column 'version' to the 'yearn_vaults_events' table
    - Delete aave events
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v27_rotkehlchen.db')
    db_v27 = _init_db_with_target_version(
        target_version=27,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v27.conn.cursor()

    # Checks before migration
    assert cursor.execute('SELECT COUNT(*) FROM aave_events;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from yearn_vaults_events;').fetchone()[0] == 1

    db_v27.logout()
    # Migrate to v28
    db = _init_db_with_target_version(
        target_version=28,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM pragma_table_info('yearn_vaults_events') "
        "WHERE name='version'",
    )
    assert cursor.fetchone()[0] == 1

    cursor.execute('SELECT count(*) from yearn_vaults_events;')
    assert cursor.fetchone()[0] == 1

    # Check that the version is correct for the event in db
    cursor.execute('SELECT version from yearn_vaults_events;')
    assert cursor.fetchone()[0] == 1

    # Check that aave_events got deleted
    assert cursor.execute('SELECT COUNT(*) FROM aave_events;').fetchone()[0] == 0

    # Finally also make sure that we have updated to the target version
    with db.conn.read_ctx() as cursor:
        assert db.get_setting(cursor, 'version') == 28
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_28_to_29(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 28 to version 29.

    - Updates the primary key of blockchain accounts to take into account chain type
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v28_rotkehlchen.db')
    db_v28 = _init_db_with_target_version(
        target_version=28,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v28.conn.cursor()

    expected_accounts = [
        ('AVAX', '0x84D34f4f83a87596Cd3FB6887cFf8F17Bf5A7B83', ''),
        ('BTC', '39bAC3Mr6RfT2V3Z8qShD7mA9JT1Phmvap', ''),
        ('ETH', '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', 'Address with internal txs'),
        ('ETH', '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', 'address that sends'),
        ('ETH', '0x902CAe163C2B222285035aAEB9A25e6BA02Fa27B', 'address that receives'),
    ]
    expected_xpubs = [('xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk', '/m/0/0', 'label1')]  # noqa: E501
    expected_xpub_mappings = [
        ('39bAC3Mr6RfT2V3Z8qShD7mA9JT1Phmvap', 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk', '/m/0/0', 0, 1),  # noqa: E501
    ]
    # Checks before migration
    assert cursor.execute('SELECT * FROM blockchain_accounts;').fetchall() == expected_accounts
    assert cursor.execute('SELECT * FROM xpubs;').fetchall() == expected_xpubs
    assert cursor.execute('SELECT * FROM xpub_mappings;').fetchall() == expected_xpub_mappings
    expected_transactions_before = [
        ('0xbf5a8870576098c23fb2736ad4832db401a04a52000e6064294711acddb1dac5', 12690344, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 0),  # noqa: E501
        ('0x67884a2e791e3d93f5dc1a57019f3ac612693c7fe70fbb74d5e6e61b307cf5d9', 12691582, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 1),  # noqa: E501
        ('0xfb90c1e3f50016d95c8b6d37b7f85aa9a9d4e6f2da0caf9abaa2e25395e53e57', 12719998, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 2),  # noqa: E501
        ('0x49783d098aa710e05d6fc37f5aa28cf4743c0c8cee57a65f2d66fd7a869e06ac', 12773277, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 3),  # noqa: E501
        ('0x5107cd6fa8c62435ab223134a3eecb94c2feea3084962421c73416329bc5ac49', 12817184, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 4),  # noqa: E501
        ('0xe4d7486814e50aa11af7e8034bb1d48fa04cde6051fb557324a5001e36426f31', 12856423, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 5),  # noqa: E501
        ('0x7c293ef356957263f164c16fe38730cd7bd6b1ffef0b2f5cc21851a9b43ca5cf', 12895650, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 6),  # noqa: E501
        ('0xc8141b1260613f1281ea375402be9291f2330b240cf16bcdb0dc1dfe70a02722', 12931687, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 7),  # noqa: E501
        ('0x841e78e62ad89c5de0100d27acce3593b52f0a2880366144ddfffc622e99c559', 12978963, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 8),  # noqa: E501
        ('0x3617e90dae481ebd5f906d2f325940ba334a1a37f966f9945926fb36d518a5a3', 13030277, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 9),  # noqa: E501
        ('0xff76780c18b8e8b1cae08af25ffe571d9862eb3587b0e8a705effadb3c9dfce2', 13047542, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 10),  # noqa: E501
        ('0x8342dbd4b0befe23f5d0da0ef5e5aeb52c323fb939e242de8a8afeaae16e0f1c', 13087523, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 11),  # noqa: E501
        ('0x07c51405f1046d85c6bb534fd8e8b9822935d33f7c96cf840611f719f4de8b52', 13145936, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 12),  # noqa: E501
        ('0xf88c83f6c5725fbeff1969dc1b26c1d29c1435d457d092c14bee349ecc04781a', 12689445, '0x2602669a92fCCF44e5319fF51B0F453aAb9Db021', '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', -1),  # noqa: E501
        ('0x548d45b53482ad22e7d8f0ae81a8b52e99d9582f3dad38bdf1fadc7911c99201', 13086898, '0x2602669a92fCCF44e5319fF51B0F453aAb9Db021', '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', -1),  # noqa: E501
        ('0xa32075632ea2fa55c52dfe6ab361b4b9bf33ece75e78ae5f113aba8a91c20a28', 13145936, '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', '0x902CAe163C2B222285035aAEB9A25e6BA02Fa27B', 1),  # noqa: E501
        ('0x53d2205f3f4e4d4f083878253c1b6c1cf9476fb70a53f97255425837cf472b9f', 12096043, '0x85b931A32a0725Be14285B66f1a22178c672d69B', '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', 650479),  # noqa: E501
        ('0x04fb485b37b0a6107613ac6a9df403037ef41c523e562559bbfaa773f23c0ff8', 12096288, '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', '0x3E66B66Fd1d0b02fDa6C811Da9E0547970DB2f21', 0),  # noqa: E501
    ]
    transactions_before_query = cursor.execute('SELECT tx_hash, block_number, from_address, to_address, nonce from ethereum_transactions;')  # noqa: E501
    transactions_before = [(
        '0x' + entry[0].hex(),
        entry[1],
        entry[2],
        entry[3],
        entry[4],
    ) for entry in transactions_before_query]
    assert transactions_before == expected_transactions_before

    db_v28.logout()
    # Migrate to v29
    db = _init_db_with_target_version(
        target_version=29,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()

    # check same data is there
    assert cursor.execute('SELECT * FROM blockchain_accounts;').fetchall() == expected_accounts
    assert cursor.execute('SELECT * FROM xpubs;').fetchall() == expected_xpubs
    assert cursor.execute(
        'SELECT address, xpub, derivation_path, account_index, derived_index FROM xpub_mappings;',
    ).fetchall() == expected_xpub_mappings
    # Check transactions are migrated and internal ones removed
    expected_transactions_after = [
        ('0xbf5a8870576098c23fb2736ad4832db401a04a52000e6064294711acddb1dac5', 12690344, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 0),  # noqa: E501
        ('0x67884a2e791e3d93f5dc1a57019f3ac612693c7fe70fbb74d5e6e61b307cf5d9', 12691582, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 1),  # noqa: E501
        ('0xfb90c1e3f50016d95c8b6d37b7f85aa9a9d4e6f2da0caf9abaa2e25395e53e57', 12719998, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 2),  # noqa: E501
        ('0x49783d098aa710e05d6fc37f5aa28cf4743c0c8cee57a65f2d66fd7a869e06ac', 12773277, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 3),  # noqa: E501
        ('0x5107cd6fa8c62435ab223134a3eecb94c2feea3084962421c73416329bc5ac49', 12817184, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 4),  # noqa: E501
        ('0xe4d7486814e50aa11af7e8034bb1d48fa04cde6051fb557324a5001e36426f31', 12856423, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 5),  # noqa: E501
        ('0x7c293ef356957263f164c16fe38730cd7bd6b1ffef0b2f5cc21851a9b43ca5cf', 12895650, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 6),  # noqa: E501
        ('0xc8141b1260613f1281ea375402be9291f2330b240cf16bcdb0dc1dfe70a02722', 12931687, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 7),  # noqa: E501
        ('0x841e78e62ad89c5de0100d27acce3593b52f0a2880366144ddfffc622e99c559', 12978963, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 8),  # noqa: E501
        ('0x3617e90dae481ebd5f906d2f325940ba334a1a37f966f9945926fb36d518a5a3', 13030277, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 9),  # noqa: E501
        ('0xff76780c18b8e8b1cae08af25ffe571d9862eb3587b0e8a705effadb3c9dfce2', 13047542, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 10),  # noqa: E501
        ('0x8342dbd4b0befe23f5d0da0ef5e5aeb52c323fb939e242de8a8afeaae16e0f1c', 13087523, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 11),  # noqa: E501
        ('0x07c51405f1046d85c6bb534fd8e8b9822935d33f7c96cf840611f719f4de8b52', 13145936, '0xb99Db59b12d43465848B11478AccBe491F4c6A4E', '0x9B9647431632AF44be02ddd22477Ed94d14AacAa', 12),  # noqa: E501
        ('0xa32075632ea2fa55c52dfe6ab361b4b9bf33ece75e78ae5f113aba8a91c20a28', 13145936, '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', '0x902CAe163C2B222285035aAEB9A25e6BA02Fa27B', 1),  # noqa: E501
        ('0x53d2205f3f4e4d4f083878253c1b6c1cf9476fb70a53f97255425837cf472b9f', 12096043, '0x85b931A32a0725Be14285B66f1a22178c672d69B', '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', 650479),  # noqa: E501
        ('0x04fb485b37b0a6107613ac6a9df403037ef41c523e562559bbfaa773f23c0ff8', 12096288, '0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749', '0x3E66B66Fd1d0b02fDa6C811Da9E0547970DB2f21', 0),    # noqa: E501
    ]
    transactions_after_query = cursor.execute('SELECT tx_hash, block_number, from_address, to_address, nonce from ethereum_transactions;')  # noqa: E501
    transactions_after = [(
        '0x' + entry[0].hex(),
        entry[1],
        entry[2],
        entry[3],
        entry[4],
    ) for entry in transactions_after_query]
    assert transactions_after == expected_transactions_after

    # check that uniswap_events table was renamed
    assert table_exists(cursor, 'uniswap_events') is False
    assert table_exists(cursor, 'amm_events') is True

    # Finally also make sure that we have updated to the target version
    with db.conn.read_ctx() as cursor:
        assert db.get_setting(cursor, 'version') == 29
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_29_to_30(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 29 to version 30.

    - Updates the primary key of blockchain accounts to take into account chain type
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v29_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=30,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    # Finally also make sure that we have updated to the target version
    with db.conn.read_ctx() as cursor:
        assert db.get_setting(cursor, 'version') == 30
    cursor = db.conn.cursor()
    # Check that existing balances are not considered as liabilities after migration
    cursor.execute('SELECT category FROM manually_tracked_balances;')
    assert cursor.fetchone() == ('A',)
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_30_to_31(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 30 to version 31.

    Also checks that this code upgrade works even if the DB is affected by
    https://github.com/rotki/rotki/issues/3744 and does not have a version
    setting set. Checks that the version is detected as at least v30 by missing
    the eth2_validators table.

    - Upgrades the ETH2 tables
    - Deletes ignored ethereum transactions ids
    - Deletes kraken trades and used query ranges
    """
    msg_aggregator = MessagesAggregator()
    # Check we have data in the eth2 tables before the DB upgrade
    _use_prepared_db(user_data_dir, 'v30_rotkehlchen.db')
    db_v30 = _init_db_with_target_version(
        target_version=30,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v30.conn.cursor()
    result = cursor.execute('SELECT COUNT(*) FROM eth2_deposits;')
    assert result.fetchone()[0] == 1
    result = cursor.execute('SELECT COUNT(*) FROM eth2_daily_staking_details;')
    assert result.fetchone()[0] == 356
    result = cursor.execute('SELECT * FROM ignored_actions;')
    assert result.fetchall() == [('C', '0x1'), ('C', '0x2'), ('A', '0x3'), ('B', '0x4')]
    result = cursor.execute('SELECT COUNT(*) FROM trades;')
    assert result.fetchone()[0] == 2
    result = cursor.execute('SELECT COUNT(*) FROM asset_movements;')
    assert result.fetchone()[0] == 1
    result = cursor.execute('SELECT * FROM used_query_ranges;')
    assert result.fetchall() == [
        ('ethtxs_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
        ('eth2_deposits_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 1602667372, 1637575118),
        ('kraken_trades_kraken1', 0, 1634850532),
        ('kraken_asset_movements_kraken1', 0, 1634850532),
    ]

    db_v30.logout()
    _use_prepared_db(user_data_dir, 'v30_rotkehlchen.db')
    db = _init_db_with_target_version(
        target_version=31,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )

    cursor = db.conn.cursor()
    # Finally also make sure that we have updated to the target version
    assert db.get_setting(cursor, 'version') == 31
    cursor = db.conn.cursor()
    # Check that the new table is created
    assert table_exists(cursor, 'eth2_validators') is True
    result = cursor.execute('SELECT COUNT(*) FROM eth2_deposits;')
    assert result.fetchone()[0] == 0
    result = cursor.execute('SELECT COUNT(*) FROM eth2_daily_staking_details;')
    assert result.fetchone()[0] == 0
    result = cursor.execute('SELECT * FROM ignored_actions;')
    assert result.fetchall() == [('A', '0x3'), ('B', '0x4')]
    result = cursor.execute('SELECT COUNT(*) FROM trades;')
    assert result.fetchone()[0] == 0
    result = cursor.execute('SELECT COUNT(*) FROM asset_movements;')
    assert result.fetchone()[0] == 1
    result = cursor.execute('SELECT * FROM used_query_ranges;')
    assert result.fetchall() == [
        ('ethtxs_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
        ('eth2_deposits_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 1602667372, 1637575118),
        ('kraken_asset_movements_kraken1', 0, 1634850532),
    ]
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_31_to_32(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 31 to version 32.

    - Check that subtype is correctly updated
    - Check that gitcoin data is properly delete
    - Check that trades with fee missing, sets fee_currency to NULL and vice versa
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v31_rotkehlchen.db')
    db_v31 = _init_db_with_target_version(
        target_version=31,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v31.conn.cursor()
    result = cursor.execute('SELECT rowid from history_events')
    old_ids = {row[0] for row in result}
    assert len(old_ids) == 19
    cursor.execute(
        'SELECT subtype from history_events',
    )
    subtypes = [row[0] for row in cursor]
    assert set(subtypes) == {
        'staking deposit asset',
        'staking receive asset',
        None,
        'fee',
        'staking remove asset',
    }
    # check used query ranges
    result = cursor.execute('SELECT * from used_query_ranges').fetchall()
    assert result == [
        ('ethtxs_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
        ('eth2_deposits_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 1602667372, 1637575118),
        ('kraken_asset_movements_kraken1', 0, 1634850532),
        ('gitcoingrants_0x4362BBa5a26b07db048Bc2603f843E21Ac22D75E', 1, 2),
    ]
    # Check gitcoin ledger actions are there
    result = cursor.execute('SELECT * from ledger_actions').fetchall()
    assert result == [
        (1, 1, 'A', 'A', '1', 'ETH', None, None, None, None),
        (2, 2, 'A', '^', '1', 'ETH', None, None, None, None),
        (3, 3, 'A', '^', '1', 'ETH', None, None, None, None),
    ]
    result = cursor.execute('SELECT * from ledger_actions_gitcoin_data').fetchall()
    assert result == [(2, '0x1', 1, 1, 'A'), (3, '0x2', 1, 1, 'B')]
    # Check that the other gitcoin tables exist at this point
    for name in ('gitcoin_tx_type', 'ledger_actions_gitcoin_data', 'gitcoin_grant_metadata'):
        assert table_exists(cursor, name)

    manual_balance_before = cursor.execute(
        'SELECT asset, label, amount, location, category FROM '
        'manually_tracked_balances;',
    ).fetchall()

    # check that the trades with invalid fee/fee_currency are present at this point
    trades_before = cursor.execute('SELECT * FROM trades WHERE id != ? AND id != ?', ('foo1', 'foo2')).fetchall()  # noqa: E501
    assert trades_before == [
        ('1111111', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', '3.4', 'USD', None, None),  # noqa: E501
        ('1111112', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', '3.4', None, None, None),  # noqa: E501
        ('1111113', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', None, 'USD', None, None),  # noqa: E501
    ]
    # Check that there are invalid pairs of (event_identifier, sequence_index)
    base_entries_query = "SELECT * from history_events WHERE event_identifier='KRAKEN-REMOTE-ID3'"
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 4
    assert len([True for event in result if event[-1] is not None]) == 2

    base_entries_query = "SELECT * from history_events WHERE event_identifier='KRAKEN-REMOTE-ID4'"
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 3

    # check that user_credential_mappings with setting_name=PAIRS are present
    selected_binance_markets_before = cursor.execute("SELECT * from user_credentials_mappings WHERE setting_name='PAIRS'").fetchall()  # noqa: E501
    assert selected_binance_markets_before == [
        ('binance', 'E', 'PAIRS', 'pro'),
        ('binanceus', 'S', 'PAIRS', 'abc'),
    ]

    tag_mappings_before = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings').fetchall()  # noqa: E501
    assert tag_mappings_before == [
        ('LABEL1', 'TAG1'),
        ('LABEL2', 'TAG2'),
    ]

    # Check that we have old staking events
    expected_timestamp = 16099501664486
    cursor.execute("SELECT COUNT(*) FROM history_events WHERE subtype='staking remove asset' AND type='unstaking'")  # noqa: E501
    assert cursor.fetchone() == (1,)
    cursor.execute("SELECT COUNT(*), timestamp FROM history_events WHERE subtype='staking receive asset' AND type='unstaking'")  # noqa: E501
    assert cursor.fetchone() == (1, expected_timestamp)

    db_v31.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=32,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    cursor.execute('SELECT subtype FROM history_events')
    subtypes = {row[0] for row in cursor}
    assert subtypes == {'deposit asset', 'receive wrapped', 'reward', 'fee', None, 'remove asset'}
    result = cursor.execute('SELECT identifier FROM history_events ORDER BY identifier')
    assert [x[0] for x in result] == list(range(1, 20)), 'identifier column should be added'
    # check used query range got delete and rest are intact
    result = cursor.execute('SELECT * from used_query_ranges').fetchall()
    assert result == [
        ('ethtxs_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
        ('eth2_deposits_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 1602667372, 1637575118),
        ('kraken_asset_movements_kraken1', 0, 1634850532),
    ]
    # Check that the non-gitcoin ledger action is still there
    result = cursor.execute('SELECT * from ledger_actions').fetchall()
    assert result == [(1, 1, 'A', 'A', '1', 'ETH', None, None, None, None)]
    # Check that all gitcoin tables are deleted
    for name in ('gitcoin_tx_type', 'ledger_actions_gitcoin_data', 'gitcoin_grant_metadata'):
        assert table_exists(cursor, name) is False

    manual_balance_after = cursor.execute(
        'SELECT asset, label, amount, location, category FROM '
        'manually_tracked_balances;',
    ).fetchall()

    manual_balance_expected = [
        ('1CR', 'LABEL1', '34.5', 'A', 'B'),
        ('2GIVE', 'LABEL2', '0.3', 'B', 'B'),
        ('1CR', 'LABEL3', '3', 'A', 'A'),
    ]
    assert manual_balance_expected == manual_balance_before == manual_balance_after

    manual_balance_ids = cursor.execute('SELECT id FROM manually_tracked_balances;').fetchall()

    assert [x[0] for x in manual_balance_ids] == [1, 2, 3]

    # Check that trades with fee missing sets fee_currency to NULL and vice versa
    trades_expected = cursor.execute('SELECT * FROM trades WHERE id != ? AND id != ?', ('foo1', 'foo2')).fetchall()  # noqa: E501
    assert trades_expected == [
        ('1111111', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', '3.4', 'USD', None, None),  # noqa: E501
        ('1111112', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', None, None, None, None),  # noqa: E501
        ('1111113', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', None, None, None, None),  # noqa: E501
    ]

    # Check that sequence indices are unique for the same event identifier
    base_entries_query = "SELECT * from history_events WHERE event_identifier='KRAKEN-REMOTE-ID3'"
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 5

    base_entries_query = "SELECT * from history_events WHERE event_identifier='KRAKEN-REMOTE-ID4'"
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 5

    ens_names_test_data = ('0xASDF123', 'TEST_ENS_NAME', 1)
    cursor.execute('INSERT INTO ens_mappings(address, ens_name, last_update) VALUES(?, ?, ?)', ens_names_test_data)  # noqa: E501
    data_in_db = cursor.execute('SELECT address, ens_name, last_update FROM ens_mappings').fetchone()  # noqa: E501
    assert data_in_db == ens_names_test_data
    # Check that selected binance markets settings_name changed to the updated one.
    selected_binance_markets_after = cursor.execute("SELECT * from user_credentials_mappings WHERE setting_name='binance_selected_trade_pairs'").fetchall()  # noqa: E501
    assert selected_binance_markets_after == [
        ('binance', 'E', 'binance_selected_trade_pairs', 'pro'),
        ('binanceus', 'S', 'binance_selected_trade_pairs', 'abc'),
    ]
    tag_mappings_after = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings').fetchall()  # noqa: E501
    assert tag_mappings_after == [
        ('1', 'TAG1'),
        ('2', 'TAG2'),
    ]

    # Check that staking events have been updated
    cursor.execute("SELECT COUNT(*) FROM history_events WHERE subtype='staking remove asset' AND type='unstaking'")  # noqa: E501
    assert cursor.fetchone() == (0,)
    cursor.execute("SELECT COUNT(*) FROM history_events WHERE subtype='staking receive asset' AND type='unstaking'")  # noqa: E501
    assert cursor.fetchone() == (0,)
    cursor.execute("SELECT COUNT(*), timestamp FROM history_events WHERE subtype='remove asset' AND type='staking'")  # noqa: E501
    assert cursor.fetchone() == (1, expected_timestamp // 10)
    cursor.execute("SELECT COUNT(*), timestamp FROM history_events WHERE subtype='remove asset' AND type='staking'")  # noqa: E501
    assert cursor.fetchone() == (1, expected_timestamp // 10)
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_32_to_33(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 32 to version 33.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v32_rotkehlchen.db')
    db_v32 = _init_db_with_target_version(
        target_version=32,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v32.conn.cursor()
    # check that you cannot add blockchain column in xpub_mappings
    with pytest.raises(sqlcipher.OperationalError) as exc_info:  # pylint: disable=no-member
        cursor.execute(
            "INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index, blockchain) "  # noqa: E501
            "VALUES ('1234', 'abcd', 'd', 3, 6, 'BCH');",
        )
    assert 'cannot INSERT into generated column "blockchain"' in str(exc_info)
    xpub_mapping_data = (
        '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r',
        'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk',
        'm',
        0,
        0,
        'BTC',
    )
    old_xpub_mappings = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
    assert len(old_xpub_mappings) == 2
    assert old_xpub_mappings[0] == xpub_mapping_data

    # test that previous xpubs as what are expected
    old_xpubs = cursor.execute('SELECT * FROM xpubs').fetchall()
    assert len(old_xpubs) == 2
    blockchain_account_label_initial = cursor.execute("SELECT * FROM blockchain_accounts WHERE account='0x45E6CA515E840A4e9E02A3062F99216951825eB2'").fetchone()[2]  # noqa: E501
    assert blockchain_account_label_initial == ''

    # get tables with tx_hash as string.
    old_aave_events = cursor.execute('SELECT * FROM aave_events').fetchall()
    assert len(old_aave_events) == 4
    old_adex_events = cursor.execute('SELECT * FROM adex_events').fetchall()
    assert len(old_adex_events) == 2
    old_balancer_events = cursor.execute('SELECT * FROM balancer_events').fetchall()
    assert len(old_balancer_events) == 2
    old_yearn_vaults_events = cursor.execute('SELECT * FROM yearn_vaults_events').fetchall()
    assert len(old_yearn_vaults_events) == 2
    old_amm_events = cursor.execute('SELECT * FROM amm_events').fetchall()
    assert len(old_amm_events) == 2
    old_amm_swaps = cursor.execute('SELECT * FROM amm_swaps').fetchall()
    assert len(old_amm_swaps) == 2
    old_combined_trades_views = cursor.execute('SELECT * FROM combined_trades_view;').fetchall()
    assert len(old_combined_trades_views) == 7
    # get history events
    old_history_events = cursor.execute('SELECT * FROM history_events').fetchall()
    assert len(old_history_events) == 5
    db_v32.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=33,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    # check that xpubs mappings were not altered.
    new_xpub_mappings = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
    assert new_xpub_mappings == old_xpub_mappings
    # check that you can now add blockchain column in xpub_mappings
    address = '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe'
    cursor.execute(
        'INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index, blockchain) '  # noqa: E501
        'VALUES (?, ?, ?, ?, ?, ?);',
        (address, xpub_mapping_data[1], 'm', 0, 1, 'BTC'),
    )
    all_xpubs_mappings = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
    assert len(all_xpubs_mappings) == 3

    # check that previous xpubs blockchain columns are set to BTC
    new_xpubs = cursor.execute('SELECT * FROM xpubs').fetchall()
    assert len(new_xpubs) == len(old_xpubs)
    for xpub in new_xpubs:
        assert xpub[3] == 'BTC'
    blockchain_account_label_upgraded = cursor.execute("SELECT * FROM blockchain_accounts WHERE account='0x45E6CA515E840A4e9E02A3062F99216951825eB2'").fetchone()[2]  # noqa: E501
    assert blockchain_account_label_upgraded is None

    # check that forcing bytes for tx hashes did not break anything.
    new_aave_events = cursor.execute('SELECT * FROM aave_events').fetchall()
    assert len(new_aave_events) == 4
    new_adex_events = cursor.execute('SELECT * FROM adex_events').fetchall()
    assert len(new_adex_events) == 2
    new_balancer_events = cursor.execute('SELECT * FROM balancer_events').fetchall()
    assert len(new_balancer_events) == 2
    new_yearn_vaults_events = cursor.execute('SELECT * FROM yearn_vaults_events').fetchall()
    assert len(new_yearn_vaults_events) == 2
    new_amm_events = cursor.execute('SELECT * FROM amm_events').fetchall()
    assert len(new_amm_events) == 2
    new_amm_swaps = cursor.execute('SELECT * FROM amm_swaps').fetchall()
    assert len(new_amm_swaps) == 2
    new_combined_trades_views = cursor.execute('SELECT * FROM combined_trades_view;').fetchall()
    assert len(new_combined_trades_views) == 7
    new_history_events = cursor.execute('SELECT * FROM history_events').fetchall()
    assert len(new_history_events) == 5
    assert_tx_hash_is_bytes(old=old_aave_events, new=new_aave_events, tx_hash_index=4)
    assert_tx_hash_is_bytes(old=old_adex_events, new=new_adex_events, tx_hash_index=0)
    assert_tx_hash_is_bytes(old=old_balancer_events, new=new_balancer_events, tx_hash_index=0)
    assert_tx_hash_is_bytes(old=old_yearn_vaults_events, new=new_yearn_vaults_events, tx_hash_index=12)  # noqa: E501
    assert_tx_hash_is_bytes(old=old_amm_events, new=new_amm_events, tx_hash_index=0)
    assert_tx_hash_is_bytes(old=old_amm_swaps, new=new_amm_swaps, tx_hash_index=0)
    # not all combined_trades_views have tx hash.
    assert_tx_hash_is_bytes(old=old_combined_trades_views[:1], new=new_combined_trades_views[:1], tx_hash_index=10)  # noqa: E501
    assert_tx_hash_is_bytes(old=old_history_events, new=new_history_events, tx_hash_index=1, is_history_event=True)  # noqa: E501
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_33_to_34(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 33 to version 34.

    - Change the combined_trades_view so a valid string is returned in the link field instead
    of a blob.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v33_rotkehlchen.db')
    db_v33 = _init_db_with_target_version(
        target_version=33,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    with db_v33.conn.read_ctx() as cursor:
        cursor.execute('SELECT * FROM combined_trades_view ORDER BY time ASC')
        result = cursor.fetchall()
        assert isinstance(result[-1][10], bytes)
        assert str(HexBytes(result[-1][10])) == '0xb1fcf4aef6af87a061ca03e92c4eb8039efe600d501ba288a8bae90f78c91db5'  # noqa: E501

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=34,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    with db.conn.read_ctx() as cursor:
        cursor.execute('SELECT * FROM combined_trades_view ORDER BY time ASC')
        result = cursor.fetchall()
        assert isinstance(result[-1][10], str)
        assert result[-1][10] == '0xb1fcf4aef6af87a061ca03e92c4eb8039efe600d501ba288a8bae90f78c91db5'  # noqa: E501
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_34_to_35(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 34 to version 35.

    - Check that expected information for the changes in timestamps exists and is correct
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v34_rotkehlchen.db')

    # Make sure that assets from the globaldb at version 3 are not copied in the test database
    with patch('rotkehlchen.db.dbhandler.DBHandler.sync_globaldb_assets', return_value=lambda *args: None):  # noqa: E501
        db_v34 = _init_db_with_target_version(
            target_version=34,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
            resume_from_backup=False,
        )

    upgraded_tables = (
        'timed_balances',
        'timed_location_data',
        'trades',
        'asset_movements',
    )
    expected_timestamps = (
        [(1658564495,)],
        [(1637574520,)],
        [(1595640208,), (1595640208,), (1595640208,)],
        [(1,)],
    )
    expected_old_ignored_assets_ids = [
        ('_ceth_0x4Fabb145d64652a948d72533023f6E7A623C7C53',),
        ('_ceth_0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',),
        ('_ceth_0xB8c77482e45F1F44dE1745F52C74426C631bDD52',),
        ('_ceth_0xdAC17F958D2ee523a2206206994597C13D831ec7',),
    ]
    with db_v34.conn.read_ctx() as cursor:
        for table_name, expected_result in zip(upgraded_tables, expected_timestamps, strict=True):
            cursor.execute(f'SELECT time from {table_name}')
            assert cursor.fetchall() == expected_result

        used_ranges = cursor.execute('SELECT * from used_query_ranges').fetchall()
        assert used_ranges == [
            ('ethtxs_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
            ('eth2_deposits_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 1602667372, 1637575118),
            ('kraken_asset_movements_kraken1', 0, 1634850532),
            ('uniswap_trades_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
            ('sushiswap_trades_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
            ('balancer_trades_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118)]

        # check that amm_swaps and combined trades view exist
        assert table_exists(cursor, 'amm_swaps') is True
        assert cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name=?", ('combined_trades_view',),  # noqa: E501
        ).fetchone()[0] == 1

        with pytest.raises(sqlcipher.OperationalError) as exc_info:  # pylint: disable=no-member
            cursor.execute('SELECT blockchain FROM web3_nodes;')
        assert "no such column: blockchain'" in str(exc_info)

        # check that ignored assets are present in the previous format.
        old_ignored_assets_ids = cursor.execute("SELECT value FROM multisettings WHERE name='ignored_asset';").fetchall()  # noqa: E501
        assert old_ignored_assets_ids == expected_old_ignored_assets_ids
        cursor.execute("SELECT tokens_list from ethereum_accounts_details WHERE account='0x45E6CA515E840A4e9E02A3062F99216951825eB2'")  # noqa: E501

        tokens = json.loads(cursor.fetchone()[0])
        assert tokens['tokens'] == ['_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e']
        # check that history events contain a transaction with an old style token identifier
        old_tx_assets_ids = cursor.execute('SELECT DISTINCT asset FROM history_events;').fetchall()
        asset_missing_from_assets_table = '_ceth_0xb3d608c31ACa7a1c7D6DAcec5978E5493181b67A'
        assert old_tx_assets_ids == [
            ('ETH',),
            ('AVAX',),
            ('BTC',),
            ('_ceth_0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5',),
            (asset_missing_from_assets_table,),
        ]

        # check that _ceth_0xb3d608c31ACa7a1c7D6DAcec5978E5493181b67A is not in assets table
        # essentially reproduce: https://github.com/rotki/rotki/issues/5052
        asset_in_table = cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (asset_missing_from_assets_table,),
        ).fetchone()[0]
        assert asset_in_table == 0, 'asset should be in history event but not in assets table'

        # Check that oracles exist in the test db
        oracles_before_upgrade = cursor.execute(
            "SELECT value FROM settings WHERE name='current_price_oracles'",
        ).fetchone()[0]
        assert oracles_before_upgrade == '["cryptocompare", "coingecko", "uniswapv2", "uniswapv3", "saddle"]'  # noqa: E501

        oracles_after_upgrade = cursor.execute(
            "SELECT value FROM settings WHERE name='historical_price_oracles'",
        ).fetchone()
        assert oracles_after_upgrade is None

        # check that asset movement exist with previous format
        result = [(
            '_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e',
            '_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96',
        )]
        assert cursor.execute('SELECT asset, fee_asset from asset_movements').fetchall() == result

        # test that there is 3 evm tx mappings before the upgrade
        expected_evm_tx_mappings = [
            (b'\nP\xd7\x05}\xaf>y|\x03\x83\x89V\xd9\x90\xb4#\x8e\xfc\x02\xc1\x96STD\xe0\xccP6\x08\x1fF', 'ETH', 'decoded'),  # noqa: E501
            (b'\x0b\xbd\xa0\x0fMA\xe9\xcbs\x0e\x8cT*\x04B\xcb\x08R\x84\x16\xee;\xd5,\x1c\xca\xf7\xadd\x94\x03n', 'ETH', 'decoded'),  # noqa: E501
            (b"\x0c\x04\x82\x92Z\xf0\x97\xedM\x85\xec\x06\x8f\xed\xc3\xdaMev<\xc82WO'6\x92\xc5\xe88wV", 'ETH', 'customized'),  # noqa: E501
        ]
        assert cursor.execute('SELECT * from evm_tx_mappings').fetchall() == expected_evm_tx_mappings  # noqa: E501

        cursor.execute('SELECT COUNT(*) from assets WHERE identifier=?', ('BIFI',))
        assert cursor.fetchone() == (1,)
        # check that assets are updated correctly in the user db
        cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?',
            ('BIFI',),
        )
        assert cursor.fetchone() == (1,)

    xpub1 = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    xpub2 = 'zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q'  # noqa: E501

    def try_insert_mapping(cur):
        # try to insert a new entry with values (except blockchain) duplicating another entry
        cur.execute(
            'INSERT INTO xpub_mappings VALUES (?, ?, ?, ?, ?, ?)',
            (
                '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r',
                xpub1,
                'm', 0, 0, 'BCH',
            ),
        )
    # it should fail before the upgrade
    with db_v34.conn.write_ctx() as write_cursor, pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member
        try_insert_mapping(write_cursor)
    db_v34.logout()

    # Migrate the database
    db_v35 = _init_db_with_target_version(
        target_version=35,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    # it should not fail after upgrade since we added `blockchain` to primary key
    with db_v35.conn.write_ctx() as write_cursor:
        try_insert_mapping(write_cursor)

    expected_xpubs_mappings = [
        ('1LZypJUwJJRdfdndwvDmtAjrVYaHko136r', xpub1, 'm', 0, 0, 'BTC'),
        ('bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5', xpub2, 'm/0', 0, 0, 'BTC'),
        ('1LZypJUwJJRdfdndwvDmtAjrVYaHko136r', xpub1, 'm', 0, 0, 'BCH'),
    ]
    expected_new_ignored_assets_ids = [
        ('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53',),
        ('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',),
        ('eip155:1/erc20:0xB8c77482e45F1F44dE1745F52C74426C631bDD52',),
        ('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',),
    ]

    with db_v35.conn.read_ctx() as cursor:
        for table_name, expected_result in zip(upgraded_tables, expected_timestamps, strict=True):
            cursor.execute(f'SELECT timestamp from {table_name}')
            assert cursor.fetchall() == expected_result
        cursor.execute('SELECT blockchain from web3_nodes LIMIT 1')
        assert cursor.fetchall() == [('ETH',)]

        # Check that data is correct
        xpub_mappings_in_db = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
        assert xpub_mappings_in_db == expected_xpubs_mappings

        # amm swap ranges should be cleared
        used_ranges = cursor.execute('SELECT * from used_query_ranges').fetchall()
        assert used_ranges == [
            ('ethtxs_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 0, 1637575118),
            ('eth2_deposits_0x45E6CA515E840A4e9E02A3062F99216951825eB2', 1602667372, 1637575118),
            ('kraken_asset_movements_kraken1', 0, 1634850532),
        ]

        # check that amm_swaps and combined trades view are deleted
        assert table_exists(cursor, 'amm_swaps') is False
        assert cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name=?", ('combined_trades_view',),  # noqa: E501
        ).fetchone()[0] == 0
        cursor.execute(
            'SELECT COUNT(*) from assets WHERE identifier=?',
            ('eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A',),
        )
        assert cursor.fetchone() == (1,)
        cursor.execute('SELECT COUNT(*) from assets WHERE identifier=?', ('BIFI',))
        assert cursor.fetchone() == (0,)
        cursor.execute(
            'SELECT COUNT(*) from manually_tracked_balances WHERE asset=?',
            ('eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A',),
        )
        assert cursor.fetchone() == (1,)

        # check that ignored assets are now in the current CAIP format.
        new_ignored_assets_ids = cursor.execute("SELECT value FROM multisettings WHERE name='ignored_asset';").fetchall()  # noqa: E501
        for new_ignored_assets_id in expected_new_ignored_assets_ids:
            assert new_ignored_assets_id in new_ignored_assets_ids

        fixed_asset_id = 'eip155:1/erc20:0xb3d608c31ACa7a1c7D6DAcec5978E5493181b67A'
        # check that history events contain a transaction with new style token identifier
        new_tx_assets_ids = cursor.execute('SELECT DISTINCT asset FROM history_events;').fetchall()
        assert new_tx_assets_ids == [
            ('ETH',),
            ('AVAX',),
            ('BTC',),
            ('eip155:1/erc20:0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5',),
            (fixed_asset_id,),
        ]
        asset_in_table = cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?', (fixed_asset_id,),
        ).fetchone()[0]
        assert asset_in_table == 1, 'asset should now be in both history events and asset table'

        # Check that token_list for accounts has been correctly upgraded
        cursor.execute("SELECT value from accounts_details WHERE account='0x45E6CA515E840A4e9E02A3062F99216951825eB2' AND blockchain='eth' AND key='tokens'")  # noqa: E501
        token = cursor.fetchone()[0]
        assert token == 'eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'

        # Check that oracles were upgraded properly
        oracles_after_upgrade = cursor.execute(
            "SELECT value FROM settings WHERE name='current_price_oracles'",
        ).fetchone()[0]
        assert oracles_after_upgrade == '["manualcurrent", "cryptocompare", "coingecko", "defillama", "uniswapv2", "uniswapv3", "saddle"]'  # noqa: E501

        oracles_after_upgrade = cursor.execute(
            "SELECT value FROM settings WHERE name='historical_price_oracles'",
        ).fetchone()[0]
        assert oracles_after_upgrade == '["manual", "cryptocompare", "coingecko", "defillama"]'

        # check that asset movements assets were upgraded
        result = [(
            'eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e',
            'eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96',
        )]
        assert cursor.execute('SELECT asset, fee_asset from asset_movements').fetchall() == result

        # test that only the customized mapping stayed after the upgrade
        expected_evm_tx_mappings = [
            (b"\x0c\x04\x82\x92Z\xf0\x97\xedM\x85\xec\x06\x8f\xed\xc3\xdaMev<\xc82WO'6\x92\xc5\xe88wV", 'ETH', 'customized'),  # noqa: E501
        ]
        assert cursor.execute('SELECT * from evm_tx_mappings').fetchall() == expected_evm_tx_mappings  # noqa: E501
    db_v35.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_35_to_36(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 35 to version 36"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v35_rotkehlchen.db')
    db_v35 = _init_db_with_target_version(
        target_version=35,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v35.conn.cursor()

    # Test state of DB before upgrade is as expected
    result = cursor.execute("SELECT value FROM settings WHERE name='active_modules';")
    assert result.fetchone()[0] == '["liquity","adex","balancer"]'
    result = cursor.execute('SELECT * FROM ignored_actions;')
    assert result.fetchall() == [
        ('C', '0x72b6e402ccf1adc977b4054905337ece6cf0e6f67c6a95b2965d4f845ac86971'),
        ('D', '1'),
    ]
    assert table_exists(cursor, 'adex_events')
    result = cursor.execute('SELECT * FROM used_query_ranges')
    assert result.fetchall() == [
        ('ethtxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
        ('ethinternaltxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
        ('ethtokentxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
        ('adex_events_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
    ]
    accounts_details_result = cursor.execute('SELECT * from accounts_details').fetchall()
    assert len(accounts_details_result) == 50
    for entry in accounts_details_result:
        if entry[2] == 'tokens':
            assert entry[3].startswith('eip155:1/erc')
        elif entry[2] == 'last_queried_timestamp':
            assert entry[3] in {'1669718731', '1669715131', '1669711531', '1669698971'}
        else:
            raise AssertionError(f'Unexpected type {entry[2]} in accounts_details')
    transactions_result = cursor.execute('SELECT * from ethereum_transactions').fetchall()
    assert len(transactions_result) == 306
    internal_transactions_result = cursor.execute('SELECT * from ethereum_internal_transactions').fetchall()  # noqa: E501
    assert len(internal_transactions_result) == 8
    tx_receipts_result = cursor.execute('SELECT * from ethtx_receipts').fetchall()
    assert len(tx_receipts_result) == 305
    tx_receipt_logs_result = cursor.execute('SELECT * from ethtx_receipt_logs').fetchall()
    assert len(tx_receipt_logs_result) == 8291
    tx_receipt_log_topics_result = cursor.execute('SELECT * from ethtx_receipt_log_topics').fetchall()  # noqa: E501
    assert len(tx_receipt_log_topics_result) == 24124
    tx_address_mappings_result = cursor.execute('SELECT * from ethtx_address_mappings').fetchall()
    assert len(tx_address_mappings_result) == 305
    tx_mappings_result = cursor.execute('SELECT * from evm_tx_mappings').fetchall()
    assert len(tx_mappings_result) == 305
    assert cursor.execute('SELECT COUNT(*) from history_events').fetchone()[0] == 562
    assert table_exists(cursor, 'web3_nodes')
    assert table_exists(cursor, 'rpc_nodes') is False
    results = cursor.execute(
        'SELECT name, endpoint, owned, active, weight, blockchain from web3_nodes ORDER by name',
    ).fetchall()
    old_nodes_results = [
        ('1inch', 'https://web3.1inch.exchange', 0, 1, 0.15, 'ETH'),
        ('avado pool', 'https://mainnet.eth.cloud.ava.do/', 0, 1, 0.05, 'ETH'),
        ('blockscout', 'https://mainnet-nethermind.blockscout.com/', 0, 1, 0.1, 'ETH'),
        ('cloudflare', 'https://cloudflare-eth.com/', 0, 1, 0.1, 'ETH'),
        ('etherscan', '', 0, 1, 0.3, 'ETH'),
        ('mycrypto', 'https://api.mycryptoapi.com/eth', 0, 1, 0.15, 'ETH'),
        ('myetherwallet', 'https://names.mewapi.io/rpc/eth', 0, 1, 0.15, 'ETH'),
    ]
    assert results == old_nodes_results
    result = cursor.execute("SELECT sql from sqlite_master WHERE type='table' AND name='nfts'")
    assert result.fetchone()[0] == (
        'CREATE TABLE nfts (\n'
        '    identifier TEXT NOT NULL PRIMARY KEY,\n'
        '    name TEXT,\n'
        '    last_price TEXT,\n'
        '    last_price_asset TEXT,\n'
        '    manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),\n'
        '    owner_address TEXT,\n'
        '    blockchain TEXT GENERATED ALWAYS AS ("ETH") VIRTUAL,\n'
        '    FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,\n'  # noqa: E501
        '    FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n'
        '    FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n'
        ')'
    )
    result = cursor.execute('SELECT * from blockchain_accounts')
    assert result.fetchall() == [
        ('ETH', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', None),
        ('BTC', '1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'my bitcoin account'),
        ('BCH', '1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'my bitcoin cash account'),
    ]
    result = cursor.execute('SELECT * from tags')
    assert result.fetchall() == [
        ('hardware', 'hardware wallet', '0xfffff', '0x00000'),
        ('hot', 'hot wallet', '0x0f0f0f', '0xffffff'),
        ('blue', 'A tag to not touch in this upgrade', '0x0f0f0f', '0xffffff'),
    ]
    result = cursor.execute('SELECT * from tag_mappings')
    assert result.fetchall() == [
        ('1', 'blue'),
        ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'hardware'),
        ('1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'hot'),
    ]
    cursor.execute('SELECT * FROM address_book')
    assert cursor.fetchall() == [
        ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'ETH', 'yabir secret account'),
        ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'ETH', 'lefteris GTC'),
    ]
    cursor.execute("SELECT extra_data FROM history_events WHERE counterparty='liquity'")
    assert cursor.fetchall() == [
        (None,),
        ('{"staked_amount": "0", "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"}',),  # noqa: E501
        (None,),
    ]
    cursor.execute('SELECT validator_index, pnl FROM eth2_daily_staking_details')
    assert cursor.fetchall() == [
        (999, '32.01201'),
        (120000, '0'),
        (1000, '32.01455'),
    ]

    db_v35.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=36,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()

    # Test all is properly upgraded
    result = cursor.execute("SELECT value FROM settings WHERE name='active_modules' ;")
    assert result.fetchone()[0] == '["liquity", "balancer"]'
    result = cursor.execute('SELECT * FROM ignored_actions;')
    assert result.fetchall() == [
        ('C', '10x72b6e402ccf1adc977b4054905337ece6cf0e6f67c6a95b2965d4f845ac86971'),
        ('D', '1'),
    ]
    assert table_exists(cursor, 'adex_events') is False
    result = cursor.execute('SELECT * FROM used_query_ranges')
    assert result.fetchall() == [
        ('ethtxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
        ('ethinternaltxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
        ('ethtokentxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 0, 1669719423),
    ]
    new_accounts_details_result = cursor.execute('SELECT * from evm_accounts_details').fetchall()
    assert len(new_accounts_details_result) == 47
    for idx, entry in enumerate(new_accounts_details_result):
        assert entry[0] == accounts_details_result[idx][0]
        assert entry[1] == 1
        assert entry[2] == accounts_details_result[idx][2]
        assert entry[3] == accounts_details_result[idx][3]
    new_transactions_result = cursor.execute('SELECT * from evm_transactions').fetchall()
    assert len(new_transactions_result) == 306
    for idx, entry in enumerate(new_transactions_result):
        for i in range(12):
            if i == 0:
                assert entry[i] == transactions_result[idx][i]
            elif i == 1:
                assert entry[i] == 1
            else:
                assert entry[i] == transactions_result[idx][i - 1]
    new_internal_transactions_result = cursor.execute('SELECT * from evm_internal_transactions').fetchall()  # noqa: E501
    assert len(new_internal_transactions_result) == 8
    for idx, entry in enumerate(new_internal_transactions_result):
        for i in range(8):
            if i == 0:
                assert entry[i] == internal_transactions_result[idx][i]
            elif i == 1:
                assert entry[i] == 1
            else:
                assert entry[i] == internal_transactions_result[idx][i - 1]
    new_tx_receipts_result = cursor.execute('SELECT * from evmtx_receipts').fetchall()
    assert len(new_tx_receipts_result) == 305
    for idx, entry in enumerate(new_tx_receipts_result):
        for i in range(5):
            if i == 0:
                assert entry[i] == tx_receipts_result[idx][i]
            elif i == 1:
                assert entry[i] == 1
            else:
                assert entry[i] == tx_receipts_result[idx][i - 1]
    new_tx_receipt_logs_result = cursor.execute('SELECT * from evmtx_receipt_logs').fetchall()
    assert len(new_tx_receipt_logs_result) == 8291
    for idx, entry in enumerate(new_tx_receipt_logs_result):
        for i in range(6):
            if i == 0:
                assert entry[i] == tx_receipt_logs_result[idx][i]
            elif i == 1:
                assert entry[i] == 1
            else:
                assert entry[i] == tx_receipt_logs_result[idx][i - 1]
    new_tx_receipt_log_topics_result = cursor.execute('SELECT * from evmtx_receipt_log_topics').fetchall()  # noqa: E501
    assert len(new_tx_receipt_log_topics_result) == 24124
    for idx, entry in enumerate(new_tx_receipt_log_topics_result):
        for i in range(5):
            if i == 0:
                assert entry[i] == tx_receipt_log_topics_result[idx][i]
            elif i == 1:
                assert entry[i] == 1
            else:
                assert entry[i] == tx_receipt_log_topics_result[idx][i - 1]
    new_tx_address_mappings_result = cursor.execute('SELECT * from evmtx_address_mappings').fetchall()  # noqa: E501
    assert len(new_tx_address_mappings_result) == 305
    for idx, entry in enumerate(new_tx_address_mappings_result):
        for i in range(4):
            if i in {0, 1}:
                assert entry[i] == tx_address_mappings_result[idx][i]
            elif i == 2:
                assert entry[i] == 1
            else:
                assert entry[i] == tx_address_mappings_result[idx][i - 1]
    new_tx_mappings_result = cursor.execute('SELECT * from evm_tx_mappings').fetchall()
    # All 305 mappings that we had before the upgrade are deleted, so that
    # the events get redecoded.
    assert len(new_tx_mappings_result) == 0

    assert table_exists(cursor, 'web3_nodes') is False
    assert table_exists(cursor, 'rpc_nodes') is True
    upgraded_nodes_results = [(x[0], x[1], x[2], x[3], str(x[4]), x[5]) for x in old_nodes_results]
    results = cursor.execute(
        'SELECT name, endpoint, owned, active, weight, blockchain from rpc_nodes ORDER by name',
    ).fetchall()
    assert results == [
        *upgraded_nodes_results,
        ('optimism 1rpc', 'https://1rpc.io/op', False, True, '0.1', 'OPTIMISM'),
        ('optimism ankr', 'https://rpc.ankr.com/optimism', False, True, '0.1', 'OPTIMISM'),
        ('optimism blastapi', 'https://optimism-mainnet.public.blastapi.io', False, True, '0.2', 'OPTIMISM'),  # noqa: E501
        ('optimism etherscan', '', False, True, '0.4', 'OPTIMISM'),
        ('optimism official', 'https://mainnet.optimism.io', False, True, '0.2', 'OPTIMISM'),
    ]
    result = cursor.execute("SELECT sql from sqlite_master WHERE type='table' AND name='nfts'")
    assert result.fetchone()[0] == (
        "CREATE TABLE nfts (\n"
        "                identifier TEXT NOT NULL PRIMARY KEY,\n"
        "                name TEXT,\n"
        "                last_price TEXT,\n"
        "                last_price_asset TEXT,\n"
        "                manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),\n"
        "                owner_address TEXT,\n"
        "                blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,\n"
        "                is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),\n"
        "                image_url TEXT,\n"
        "                collection_name TEXT,\n"
        "                FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,\n"  # noqa: E501
        "                FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n"  # noqa: E501
        "                FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n"  # noqa: E501
        "            )"
    )

    # Test that tags and related tables got upgraded correctly
    result = cursor.execute('SELECT * from blockchain_accounts')
    assert result.fetchall() == [
        ('ETH', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', None),
        ('BTC', '1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'my bitcoin account'),
        ('BCH', '1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'my bitcoin cash account'),
    ]
    result = cursor.execute('SELECT * from tags')
    assert result.fetchall() == [
        ('hardware', 'hardware wallet', '0xfffff', '0x00000'),
        ('hot', 'hot wallet', '0x0f0f0f', '0xffffff'),
        ('blue', 'A tag to not touch in this upgrade', '0x0f0f0f', '0xffffff'),
    ]
    result = cursor.execute('SELECT * from tag_mappings')
    assert result.fetchall() == [
        ('1', 'blue'),
        ('BCH1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'hot'),
        ('BTC1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ', 'hot'),
        ('ETH0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'hardware'),
    ]

    # test that the blockchain column is nullable
    cursor.execute("INSERT INTO address_book(address, blockchain, name) VALUES ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', NULL, 'yabir everywhere')")  # noqa: E501

    # test that address book entries were kept
    cursor.execute('SELECT * FROM address_book')
    assert cursor.fetchall() == [
        ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'ETH', 'yabir secret account'),
        ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'ETH', 'lefteris GTC'),
        ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', None, 'yabir everywhere'),
    ]
    cursor.execute("SELECT extra_data FROM history_events WHERE counterparty='liquity'")
    assert cursor.fetchall() == []  # Check that it was reset

    # check that pnl for validators has been corrected on genesis
    cursor.execute('SELECT validator_index, pnl FROM eth2_daily_staking_details')
    assert cursor.fetchall() == [
        (999, '0.01201'),
        (120000, '0'),
        (1000, '0.01455'),
    ]

    # Check that customized events were not deleted
    res = cursor.execute('SELECT * FROM history_events_mappings').fetchall()
    assert res == [(234, 'state', 1)]  # A customized event that was not deleted
    res = cursor.execute('SELECT * FROM history_events WHERE identifier=?', (234,)).fetchone()
    assert res is not None
    assert res[9] == 'Edited event'  # event's notes
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_36_to_37(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 36 to version 37"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v36_rotkehlchen.db')
    db_v36 = _init_db_with_target_version(
        target_version=36,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v36.conn.cursor()
    # Test state of DB before upgrade is as expected
    result = cursor.execute('SELECT COUNT(*) FROM history_events;')
    assert result.fetchone()[0] == 186
    result = cursor.execute('SELECT COUNT(*) FROM history_events WHERE subtype IS NULL;')
    assert result.fetchone()[0] == 5
    result = cursor.execute('SELECT * from history_events_mappings;')
    assert result.fetchall() == [  # customized events
        (1, 'state', 1),
        (74, 'state', 1),
        (238, 'state', 1),
    ]
    # get events from 1.27.0 that didn't have the ethereum/optimism location
    cursor.execute("SELECT COUNT(*) FROM history_events WHERE location = 'J';")
    assert cursor.fetchone()[0] == 5

    old_history_events = cursor.execute('SELECT * FROM history_events;').fetchall()
    kraken_events = {
        (171, b'SDASD-DSAD-DSAD', 0, 1638706007439, 'B', 'kraken', 'ETH', '-10.996', '-11843.777435000000', None, 'withdrawal', None, None, None),  # noqa: E501
        (172, b'YDASD-YDSAD-YDSAD', 0, 1636553589350, 'B', 'kraken', 'ETH', '-5.1', '-6145.834', None, 'trade', None, None, None),  # noqa: E501
        (173, b'TXZSDG-IUSNH2-OOAIE3U', 0, 1679243606179, 'B', 'kraken', 'BTC', '-0.0922995600', '-1391.564299579200', None, 'trade', None, None, None),  # noqa: E501
        (174, b'TXZSDG-IUSNH2-OOAIE3U', 1, 1679243606179, 'B', 'kraken', 'EUR', '1100', '1391.564299579200', None, 'trade', None, None, None),  # noqa: E501
        (175, b'TXZSDG-IUSNH2-OOAIE3U', 2, 1679243606179, 'B', 'kraken', 'EUR', '8.00', '8.53312', None, 'trade', 'fee', None, None),  # noqa: E501
        (176, b'KRAKEN-ETH2-EVENT', 0, 1681826144996, 'B', 'kraken', 'ETH2', '-0.0032936117', '-6.930681228076', None, 'staking', 'reward', None, None),  # noqa: E501
        (177, b'KRAKEN-ETH-EVENT-STAKING', 0, 1681967948701, 'B', 'kraken', 'ETH', '0.0000355988', '0.069824910272', None, 'staking', 'reward', None, None),  # noqa: E501
        (1113, b'TSTLG5', 0, 1621508243539, 'B', 'Kraken 1', 'EUR', '-37.7000', '0', '', 'spend', 'none', None, None),  # noqa: E501
        (1114, b'TSTLG5', 2, 1621508243539, 'B', 'Kraken 1', 'EUR', '0.5500', '0', '', 'spend', 'fee', None, None),  # noqa: E501
        (1115, b'TSTLG5', 1, 1621508243543, 'B', 'Kraken 1', 'ETH', '0.0169800000', '0', '', 'receive', 'none', None, None),  # noqa: E501
    }
    custom_events = {
        (1, b'\xf1\xe0SX\xcbe\xed{3\xa6\xbb\x0f"\x8am>E\x9a\xf8\x18e\xccc6\x99M\xeciw\xc3\x1aM', 0, 1676042975000, 'g', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'ETH', '0.0000004061904', '0.000609801461808', 'Burned 0.0000004061904 ETH for gas for greater justice', 'spend', 'fee', 'gas', None),  # noqa: E501
        (74, b'\xd1\x81W\xff\x16\xd3D\xcf-"\xf1D\xeb\xcf\xc3;\xff\x0b0\xcd\xcd\xddY\x97?\xd2\xf9\xf9%\xb3\xf5\xa3', 474, 1669664867000, 'f', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', '125.835582561728229714', '125.6594127461418101924004', 'Receive 125.835582561728229714 DAI from 0x73043143e0A6418cc45d82D4505B096b802FD365 to 0xc37b40ABdB939635068d3c5f13E7faF686F03B65 because I am cool', 'receive', 'none', '0x73043143e0A6418cc45d82D4505B096b802FD365', None),  # noqa: E501
        (238, b'\xe9T\xa3\x96\xa0.\xbb\xeaE\xa1\xd2\x06\xc9\x91\x8fq|UP\x9c\x818\xfc\xccc\x15]\x02b\xefM\xc4', 76, 1675186487000, 'J', '0x6Bb553FFC5716782051f51b564Bb149D9946f0d2', 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', '10', '9.9970', 'Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD', 'deposit', 'deposit asset', 'curve', ''),  # noqa: E501
    }
    imported_event = (1116, b'rotki_eventsf3d3c9cc11e3442c91662c24ed7b3554', 0, 1638706007440, 'P', 'crypto.com', 'ETH', '12', '12000', None, 'receive', None, None, None)  # noqa: E501
    assert all(x in old_history_events for x in kraken_events)
    assert all(x in old_history_events for x in custom_events)
    assert imported_event in old_history_events

    old_ens_mappings = cursor.execute('SELECT * FROM ens_mappings').fetchall()
    assert len(old_ens_mappings) == 10
    # Check that old tables exist
    assert cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", ('eth2_deposits',),
    ).fetchone()[0] == 1
    # Check used query ranges
    assert cursor.execute('SELECT * FROM used_query_ranges').fetchall() == [
        ('ETHtxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('OPTIMISMtxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('ETHinternaltxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('OPTIMISMinternaltxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('OPTIMISMtokentxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('ETHtokentxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('eth2_deposits_0x9531C059098e3d194fF87FebB587aB07B30B1306', 0, 10),
        ('eth2_deposits_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 100, 200),
        ('kucoin_trades_Kucoin 1', 0, 1682610440),
        ('kucoin_margins_Kucoin 1', 0, 1682610440),
        ('kucoin_asset_movements_Kucoin 1', 0, 1682610440),
        ('kucoin_ledger_actions_Kucoin 1', 0, 1682610440),
        ('ftxus_trades_FTX 1', 0, 1682610440),
        ('ftxus_margins_FTX 1', 0, 1682610440),
        ('ftxus_asset_movements_FTX 1', 0, 1682610440),
        ('ftxus_ledger_actions_FTX 1', 0, 1682610440),
        ('ftx_trades_FTX 1', 0, 1682610440),
        ('ftx_margins_FTX 1', 0, 1682610440),
        ('ftx_asset_movements_FTX 1', 0, 1682610440),
        ('ftx_ledger_actions_FTX 1', 0, 1682610440),
    ]
    # check that there are two kraken events and one of them has incorrect information
    cursor.execute('SELECT amount, asset FROM history_events WHERE event_identifier IN (?, ?)', (b'KRAKEN-ETH2-EVENT', b'KRAKEN-ETH-EVENT-STAKING'))  # noqa: E501
    assert cursor.fetchall() == [('0.0000355988', 'ETH'), ('-0.0032936117', 'ETH2')]
    assert cursor.execute('SELECT * FROM eth2_daily_staking_details').fetchall() == [
        (67890, 1692519934, '0', '0', '0', '0', '0', 0, 0, 0, 0, 0, 0, 0, 0, '0'),
        (12345, 1682519933, '1000.0', '1001.0', '0.00001', '32.0', '32.00001', 0, 0, 0, 0, 0, 0, 0, 0, '0'),  # noqa: E501
        (67890, 1682519934, '1200.5', '1200.6', '0.00003', '32.01', '32.01003', 0, 0, 0, 0, 0, 0, 0, 0, '0.0'),  # noqa: E501
    ]
    assert cursor.execute('select * from user_credentials').fetchall() == [
        ('ftx1', 'Z', 'api-key-1', 'api-secret-1', None),
        ('ftx2', 'd', 'api-key-2', 'api-secret-2', None),
        ('binance1', 'E', 'api-key-3', 'api-secret-3', None),
        ('kraken1', 'B', 'api-key-4', 'api-secret-4', None),
    ]
    assert cursor.execute('select * from user_credentials_mappings').fetchall() == [
        ('ftx1', 'Z', 'ftx_subaccount', 'some-ftx-subaccount'),
        ('kraken1', 'B', 'kraken_account_type', 'starter'),
    ]
    assert cursor.execute(
        "SELECT value FROM settings WHERE name='non_syncing_exchanges'",
    ).fetchone()[0] == '[{"name": "Kucoin 1", "location": "kucoin"}]'
    assert cursor.execute(
        "SELECT value FROM settings WHERE name='ssf_0graph_multiplier'",
    ).fetchone()[0] == '42'
    assert cursor.execute(
        "SELECT value FROM settings WHERE name='ssf_graph_multiplier'",
    ).fetchone() is None

    db_v36.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=37,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()

    result = cursor.execute('SELECT COUNT(*) FROM history_events;')
    # the extra event is the imported rotki_event
    assert result.fetchone()[0] == len(kraken_events) + len(custom_events) + 1
    result = cursor.execute('SELECT COUNT(*) FROM history_events WHERE subtype IS NULL;')
    assert result.fetchone()[0] == 0

    result = cursor.execute('SELECT * from history_events_mappings;')
    assert result.fetchall() == [  # customized events mapping should persist
        (1, 'state', 1),
        (74, 'state', 1),
        (238, 'state', 1),
    ]

    new_kraken_events = set(cursor.execute("SELECT * FROM history_events WHERE location='B';"))
    updated_kraken_events = {
        (171, 1, 'SDASD-DSAD-DSAD', 0, 1638706007439, 'B', 'kraken', 'ETH', '10.996', '11843.777435000000', None, 'withdrawal', 'none'),  # noqa: E501
        (172, 1, 'YDASD-YDSAD-YDSAD', 0, 1636553589350, 'B', 'kraken', 'ETH', '5.1', '6145.834', None, 'trade', 'spend'),  # noqa: E501
        (173, 1, 'TXZSDG-IUSNH2-OOAIE3U', 0, 1679243606179, 'B', 'kraken', 'BTC', '0.0922995600', '1391.564299579200', None, 'trade', 'spend'),  # noqa: E501
        (174, 1, 'TXZSDG-IUSNH2-OOAIE3U', 1, 1679243606179, 'B', 'kraken', 'EUR', '1100', '1391.564299579200', None, 'trade', 'receive'),  # noqa: E501
        (175, 1, 'TXZSDG-IUSNH2-OOAIE3U', 2, 1679243606179, 'B', 'kraken', 'EUR', '8.00', '8.53312', None, 'trade', 'fee'),  # noqa: E501
        (176, 1, 'KRAKEN-ETH2-EVENT', 0, 1681826144996, 'B', 'kraken', 'ETH2', '0.0032936117', '6.930681228076', 'Automatic virtual conversion of staked ETH rewards to ETH', 'informational', 'none'),  # noqa: E501
        (177, 1, 'KRAKEN-ETH-EVENT-STAKING', 0, 1681967948701, 'B', 'kraken', 'ETH', '0.0000355988', '0.069824910272', None, 'staking', 'reward'),  # noqa: E501
        (1113, 1, 'TSTLG5', 0, 1621508243539, 'B', 'Kraken 1', 'EUR', '37.7000', '0', '', 'trade', 'spend'),  # noqa: E501
        (1114, 1, 'TSTLG5', 2, 1621508243539, 'B', 'Kraken 1', 'EUR', '0.5500', '0', '', 'spend', 'fee'),  # noqa: E501
        (1115, 1, 'TSTLG5', 1, 1621508243543, 'B', 'Kraken 1', 'ETH', '0.0169800000', '0', '', 'trade', 'receive'),  # noqa: E501
    }
    assert new_kraken_events == updated_kraken_events

    new_evm_info = cursor.execute('SELECT * FROM evm_events_info;').fetchall()
    assert len(new_evm_info) == len(custom_events)
    new_history_events = set(cursor.execute('SELECT * FROM history_events;'))
    for original_entry in custom_events:
        entry = original_entry
        if entry[0] == 238:
            # the event with location blockchain needs to update the location to ethereum.
            # This is the same row modifying the location to 'f' in order to build the new
            # expected event
            entry = (238, b'\xe9T\xa3\x96\xa0.\xbb\xeaE\xa1\xd2\x06\xc9\x91\x8fq|UP\x9c\x818\xfc\xccc\x15]\x02b\xefM\xc4', 76, 1675186487000, 'f', '0x6Bb553FFC5716782051f51b564Bb149D9946f0d2', 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', '10', '9.9970', 'Deposit 10 DAI in curve pool 0xA5407eAE9Ba41422680e2e00537571bcC53efBfD', 'deposit', 'deposit asset', 'curve', '')  # noqa: E501
        prefix = '10x' if entry[4] == 'f' else '100x'  # chain id prefix depending on location
        assert (entry[0], 2, prefix + entry[1].hex(), *entry[2:12]) in new_history_events
        assert (entry[0], entry[1], entry[12], None, None, entry[13]) in new_evm_info

    expected_imported_event = (1116, 1, 'rotki_eventsf3d3c9cc11e3442c91662c24ed7b3554', 0, 1638706007440, 'P', 'crypto.com', 'ETH', '12', '12000', None, 'receive', 'none')  # noqa: E501
    assert expected_imported_event in new_history_events

    new_ens_mappings = cursor.execute('SELECT * FROM ens_mappings').fetchall()
    expected_ens_mappings = [(*mapping, 0) for mapping in old_ens_mappings]
    assert new_ens_mappings == expected_ens_mappings
    # Check that old tables got deleted and used query ranges updated
    assert cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", ('eth2_deposits',),
    ).fetchone()[0] == 0
    assert cursor.execute('SELECT * FROM used_query_ranges').fetchall() == [
        ('ETHtxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('OPTIMISMtxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('ETHinternaltxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('OPTIMISMinternaltxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('OPTIMISMtokentxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('ETHtokentxs_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 0, 1679312760),
        ('kucoin_trades_Kucoin 1', 0, 1682610440),
        ('kucoin_margins_Kucoin 1', 0, 1682610440),
        ('kucoin_asset_movements_Kucoin 1', 0, 1682610440),
        ('kucoin_ledger_actions_Kucoin 1', 0, 1682610440),
    ]
    assert cursor.execute(
        'SELECT * FROM eth2_daily_staking_details',
    ).fetchall() == [(12345, 1682519933, '0.00001'), (67890, 1682519934, '0.00003')]
    assert cursor.execute('select * from user_credentials').fetchall() == [
        ('binance1', 'E', 'api-key-3', 'api-secret-3', None),
        ('kraken1', 'B', 'api-key-4', 'api-secret-4', None),
    ]
    assert cursor.execute('select * from user_credentials_mappings').fetchall() == [
        ('kraken1', 'B', 'kraken_account_type', 'starter'),
    ]
    assert cursor.execute(  # Check that FTX was deleted from non syncing exchanges
        "SELECT value FROM settings WHERE name='non_syncing_exchanges'",
    ).fetchone()[0] == '[{"name": "Kucoin 1", "location": "kucoin"}]'
    assert cursor.execute(  # Check the 0graph multiplier setting got updated properly
        "SELECT value FROM settings WHERE name='ssf_0graph_multiplier'",
    ).fetchone() is None
    assert cursor.execute(
        "SELECT value FROM settings WHERE name='ssf_graph_multiplier'",
    ).fetchone()[0] == '42'
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_37_to_38(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 37 to version 38"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v37_rotkehlchen.db')
    db_v37 = _init_db_with_target_version(
        target_version=37,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v37.conn.cursor()
    assert cursor.execute('SELECT MAX(seq) FROM location').fetchone()[0] == 39
    assert cursor.execute('SELECT COUNT(*) FROM aave_events').fetchone()[0] == 2
    aave_range_key = 'aave_events_0x026045B110b49183E78520460eBEcdC6B4538C85'
    assert cursor.execute('SELECT COUNT(*) FROM used_query_ranges WHERE name=?', (aave_range_key, )).fetchone()[0] == 1  # noqa: E501
    assert cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='amm_events';").fetchone()[0] == 1  # noqa: E501
    nodes_before = cursor.execute('SELECT * FROM rpc_nodes').fetchall()
    max_initial_node_id = cursor.execute('SELECT MAX(identifier) FROM rpc_nodes').fetchone()[0]
    expected_internal_txs = [
        (b'\x9be\x99&\xc5\xdbx\xfa\xb8\xe1\xe5\xe6\xc1\x95Z\xe5H\xee/f{G\xfc\xe5\x14p\xdf\xcfN\xe8\xaf\x12', 10, 11, 1664740777, 27005911, '0xC36442b4a4522E871399CD717aBDD847Ab11FE88', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '95427211708089243'),  # noqa: E501
        (b'>\xad\xa4\x1cyJ\xa8>\x7f5\x8c\x16\xf9R`n\xf5H\xcd\xdf;$\x89\x8a\xfd\x11\xef\xc8\x81\xa8B\x1d', 10, 1, 1664740853, 27006108, '0xBBF8233867c1982D66EA920d726d24391B713550', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '272573405755025'),  # noqa: E501
        (b'\xd2\x0f\xd4\xc6Nx\xa6\xfb\xcbq\xae\xc9-\xc7p\xd0\x9cP\x12\xeeXqB5\x08\x96}&\xa6<\x90?', 10, 1, 1651314511, 6793555, '0x1111111254760F7ab3F16433eea9304126DCd199', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '24788679616549824'),  # noqa: E501
        (b'N\xa7*\xe55\xe3-^\xdcT:\x9a\xce_slp7\xccc\xe4\x08\x8d\xe3\x85\x11)|v@I\xb5', 1, 10, 1639315070, 13790549, '0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '247563100724292'),  # noqa: E501
        (b'!wp\x1a\xb9\xc6Zw\xc7\xe9\xe6OV\x85\x12h\xcd\x015\x8e\x1c\x1d\x7f\xeb\xd8]!\x89\xbf\xf9P\x9f', 10, 1, 1667995269, 36284335, '0x1111111254760F7ab3F16433eea9304126DCd199', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '127700838932040865'),  # noqa: E501
        (b'O\x1e\x95Pl\x10\xf0a\xdd\xfe(\xa7C\x7f;e\x19Y\xff\x17\xf1\xe2\xa7\xa1H\xc8\x89aG\xee5~', 10, 11, 1643122781, 2806776, '0x86cA30bEF97fB651b8d866D45503684b90cb3312', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '103926722004783110'),  # noqa: E501
    ]
    assert cursor.execute('SELECT * FROM evm_internal_transactions ORDER BY value DESC').fetchall() == expected_internal_txs  # noqa: E501
    expected_history_events = [
        (1336, 4, 'evm_1_block_17322931', 0, 1687333184000, 'f', '0x1CCA4D950E1b548c0d0c6F2Bdb3e1d34B03505D7', 'ETH', '0.020341336836263802', '42.199456426776549992', 'Validator 1337 produced block 17322931 with 0.020341336836263802 ETH going to 0x1CCA4D950E1b548c0d0c6F2Bdb3e1d34B03505D7 as the block reward', 'staking', 'block production'),  # noqa: E501
        (1337, 4, 'evm_1_block_17322931', 1, 1687333184000, 'f', '0x1CCA4D950E1b548c0d0c6F2Bdb3e1d34B03505D7', 'ETH', '0.020341336836263802', '42.199456426776549992', 'Validator 1337 produced block 17322931 with 0.020341336836263802 ETH going to 0x1CCA4D950E1b548c0d0c6F2Bdb3e1d34B03505D7 as the mev reward', 'staking', 'mev reward'),  # noqa: E501
        (1338, 4, 'evm_1_block_17322932', 0, 1687333185000, 'f', '0x5124fcC2B3F99F571AD67D075643C743F38f1C34', 'ETH', '0.1', '50.199456426776549992', 'Validator 42 produced block 17322932 with 0.1 ETH going to 0x5124fcC2B3F99F571AD67D075643C743F38f1C34 as the block reward', 'staking', 'block production'),  # noqa: E501
        (1339, 4, 'evm_1_block_17322935', 0, 1687333191000, 'f', '0xeE1F6F65eA24D78A23A823647a14B6C4AA7436E6', 'ETH', '0.01', '35.199456426776549992', 'Validator 69 produced block 17322935 with 0.01 ETH going to 0xeE1F6F65eA24D78A23A823647a14B6C4AA7436E6 as the block reward', 'staking', 'block production'),  # noqa: E501
        (1340, 4, 'evm_1_block_17322935', 1, 1687333191000, 'f', '0x8D846930404CB46cFa021EaB1c1Dc7dd077FEc3b', 'ETH', '0.2', '78.199456426776549992', 'Validator 69 produced block 17322935 with 0.2 ETH going to 0x8D846930404CB46cFa021EaB1c1Dc7dd077FEc3b as the mev reward', 'staking', 'mev reward'),  # noqa: E501
        (1341, 4, 'evm_1_block_17322936', 0, 1687333991000, 'f', '0xeE1F6F65eA24D78A23A823647a14B6C4AA7436E6', 'ETH', '0.01', '35.199456426776549992', 'Validator 69 produced block 17322936 with 0.01 ETH going to 0xeE1F6F65eA24D78A23A823647a14B6C4AA7436E6 as the block reward', 'staking', 'block production'),  # noqa: E501
        (1342, 4, 'evm_1_block_17322936', 1, 1687333991000, 'f', '0xeE1F6F65eA24D78A23A823647a14B6C4AA7436E6', 'ETH', '0.01', '35.199456426776549992', 'Validator 69 produced block 17322936 with 0.01 ETH going to 0xeE1F6F65eA24D78A23A823647a14B6C4AA7436E6 as the mev reward', 'staking', 'mev reward'),  # noqa: E501
    ]
    assert cursor.execute('SELECT * from history_events WHERE entry_type=4;').fetchall() == expected_history_events  # noqa: E501
    expected_eth_staking_events_info = [
        (1336, 1337, 17322931),
        (1337, 1337, 17322931),
        (1338, 42, 17322932),
        (1339, 69, 17322935),
        (1340, 69, 17322935),
        (1341, 69, 17322936),
        (1342, 69, 17322936),
    ]
    assert cursor.execute('SELECT * from eth_staking_events_info').fetchall() == expected_eth_staking_events_info  # noqa: E501
    assert cursor.execute('SELECT identifier from history_events WHERE entry_type=2;').fetchall() == [(1,), (74,), (238,)]  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('uniswap\\_events\\_%', '\\')).fetchone() == (1,)  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('sushiswap\\_events\\_%', '\\')).fetchone() == (1,)  # noqa: E501

    db_v37.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=38,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    assert cursor.execute('SELECT identifier from history_events WHERE entry_type=2;').fetchall() == [(1,), (238,)]  # noqa: E501  # 1, 238 are customized so they stay. 74 should be deleted
    assert cursor.execute(  # Check that Polygon POS location was added
        'SELECT location FROM location WHERE seq=?',
        (Location.POLYGON_POS.value,),
    ).fetchone()[0] == Location.POLYGON_POS.serialize_for_db()
    nodes_after = cursor.execute('SELECT * FROM rpc_nodes').fetchall()
    default_polygon_nodes_with_ids = [
        (identifier, *node)
        for identifier, node in enumerate(DEFAULT_POLYGON_NODES_AT_V38, start=max_initial_node_id + 1)  # noqa: E501
    ]
    assert nodes_after == nodes_before + default_polygon_nodes_with_ids
    expected_internal_txs = [tuple(x[:3]) + tuple(x[5:]) for x in expected_internal_txs]
    assert cursor.execute('SELECT * from evm_internal_transactions ORDER BY value DESC').fetchall() == expected_internal_txs  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM used_query_ranges WHERE name=?', (aave_range_key,)).fetchone()[0] == 0  # noqa: E501
    assert cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='aave_events';").fetchone()[0] == 0  # noqa: E501
    assert cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='amm_events';").fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('uniswap\\_events\\_%', '\\')).fetchone() == (0,)  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('sushiswap\\_events\\_%', '\\')).fetchone() == (0,)  # noqa: E501
    # Make sure that duplicate events were removed
    expected_history_events = [expected_history_events[0]] + expected_history_events[2:6]
    assert cursor.execute('SELECT * from history_events WHERE entry_type=4;').fetchall() == expected_history_events  # noqa: E501
    expected_eth_staking_events_info = [expected_eth_staking_events_info[0]] + expected_eth_staking_events_info[2:6]  # noqa: E501
    assert cursor.execute('SELECT * from eth_staking_events_info').fetchall() == expected_eth_staking_events_info  # noqa: E501
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_38_to_39(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 38 to version 39"""
    def get_hashchain(entry):
        return entry[0] + entry[1].to_bytes(4, byteorder='big')

    def get_hashchainlog(entry):
        return get_hashchain(entry) + entry[2].to_bytes(4, byteorder='big')

    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v38_rotkehlchen.db')
    db_v38 = _init_db_with_target_version(
        target_version=38,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v38.conn.cursor()
    assert cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='optimism_transactions';").fetchone()[0] == 0  # noqa: E501
    withdrawal_events_before = {x[0] for x in cursor.execute(
        "SELECT identifier FROM history_events WHERE event_identifier LIKE 'eth2_withdrawal_%'",
    ).fetchall()}
    block_events_before = {x[0] for x in cursor.execute(
        "SELECT identifier FROM history_events WHERE event_identifier LIKE 'evm_1_block_%'",
    ).fetchall()}
    assert cursor.execute("SELECT event_identifier FROM history_events WHERE event_identifier LIKE 'rotki_events_%'").fetchall() == [  # noqa: E501
        ('rotki_events_0x2123',), ('rotki_events_bitcoin_tax_0x4123',),
    ]
    nft_data = cursor.execute('SELECT * FROM nfts').fetchall()
    assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 547
    before_non_evm_events = cursor.execute('SELECT COUNT(*) FROM history_events WHERE entry_type!=2 AND entry_type!=5').fetchone()[0]  # noqa: E501

    # Get previous data count to later compare
    txs_num = cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0]
    internaltxs_num = cursor.execute('SELECT COUNT(*) FROM evm_internal_transactions').fetchone()[0]  # noqa: E501
    receipts_num = cursor.execute('SELECT COUNT(*) FROM evmtx_receipts').fetchone()[0]
    logs_num = cursor.execute('SELECT COUNT(*) FROM evmtx_receipt_logs').fetchone()[0]
    topics_num = cursor.execute('SELECT COUNT(*) FROM evmtx_receipt_log_topics').fetchone()[0]
    assert cursor.execute('SELECT COUNT(*) FROM evm_tx_mappings').fetchone()[0] == 316
    address_mappings_num = cursor.execute('SELECT COUNT(*) FROM evmtx_address_mappings').fetchone()[0]  # noqa: E501

    # Get the previous table data and map old keys to data, for later comparison
    hashchain_to_txs = {}
    cursor.execute('SELECT * FROM evm_transactions')
    for entry in cursor:
        hashchain_to_txs[get_hashchain(entry)] = entry[2:]
    hashchain_to_internaltxs = {}
    cursor.execute('SELECT * FROM evm_internal_transactions')
    for entry in cursor:
        hashchain_to_internaltxs[get_hashchain(entry)] = entry[2:]
    hashchain_to_receipts = {}
    cursor.execute('SELECT * FROM evmtx_receipts')
    for entry in cursor:
        hashchain_to_receipts[get_hashchain(entry)] = entry[2:]
    hashchainlog_to_logs = {}
    cursor.execute('SELECT * FROM evmtx_receipt_logs')
    for entry in cursor:
        hashchainlog_to_logs[get_hashchainlog(entry)] = entry[3:]
    hashchainlogindex_to_topics = {}
    cursor.execute('SELECT * FROM evmtx_receipt_log_topics')
    for entry in cursor:
        hashchainlogindex = get_hashchainlog(entry) + entry[4].to_bytes(4, byteorder='big')
        hashchainlogindex_to_topics[hashchainlogindex] = entry[3:]
    hashchain_to_tx_mappings = {}
    cursor.execute('SELECT * FROM evm_tx_mappings')
    for entry in cursor:
        hashchain_to_tx_mappings[get_hashchain(entry)] = entry[2:]
    hashchain_to_address_mappings = {}
    cursor.execute('SELECT tx_hash, chain_id, address FROM evmtx_address_mappings')
    for entry in cursor:
        hashchain_to_address_mappings[get_hashchain(entry)] = entry[2:]

    assert cursor.execute('SELECT MAX(seq) FROM location').fetchone()[0] == 40

    # get settings and confirm saddle is present before the upgrade
    cursor.execute("SELECT value FROM settings WHERE name='current_price_oracles'")
    oracles = json.loads(cursor.fetchone()[0])
    assert 'saddle' in oracles

    # get the rpc nodes in the user db
    rpc_nodes = cursor.execute('SELECT * FROM rpc_nodes').fetchall()
    # check that there are two nodes with the same endpoint and blockchain
    assert len([x for x in rpc_nodes if 'flashbots' in x[2] == 'https://rpc.flashbots.net/' and x[-1] == 'ETH']) == 2  # noqa: E501

    cursor.close()
    db_v38.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=39,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()

    assert cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='optimism_transactions';").fetchone()[0] == 1  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == before_non_evm_events + 1  # noqa: E501  # all but 1 customized evm events should have been deleted
    withdrawal_events_after = {x[0] for x in cursor.execute(
        "SELECT identifier FROM history_events WHERE event_identifier LIKE 'EW_%'",
    ).fetchall()}
    assert withdrawal_events_after == withdrawal_events_before
    block_events_after = {x[0] for x in cursor.execute(
        "SELECT identifier FROM history_events WHERE event_identifier LIKE 'BP1_%'",
    ).fetchall()}
    assert block_events_after == block_events_before
    assert cursor.execute("SELECT event_identifier FROM history_events WHERE event_identifier LIKE 'rotki_events_%'").fetchall() == []  # noqa: E501
    assert set(cursor.execute("SELECT event_identifier FROM history_events WHERE event_identifier LIKE 'RE%'").fetchall()) == {  # noqa: E501
        ('RE_0x2123',), ('REBTX_0x4123',),
    }
    assert cursor.execute('SELECT * FROM nfts').fetchall() == nft_data

    # Make sure number of evm table entries is the same
    assert cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] == txs_num
    assert cursor.execute('SELECT COUNT(*) FROM evm_internal_transactions').fetchone()[0] == internaltxs_num  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM evmtx_receipts').fetchone()[0] == receipts_num
    assert cursor.execute('SELECT COUNT(*) FROM evmtx_receipt_logs').fetchone()[0] == logs_num
    assert cursor.execute('SELECT COUNT(*) FROM evmtx_receipt_log_topics').fetchone()[0] == topics_num  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM evm_tx_mappings').fetchone()[0] == 0  # events have been reset so no transactions are now decoded  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM evmtx_address_mappings').fetchone()[0] == address_mappings_num  # noqa: E501

    # Now make sure mappings are correct and point to the same data after upgrade
    hashchain_to_id = {}
    id_to_hashchain = {}
    cursor.execute('SELECT * FROM evm_transactions')
    for entry in cursor:
        hashchain = get_hashchain(entry[1:])
        hashchain_to_id[hashchain] = entry[0]
        id_to_hashchain[entry[0]] = hashchain
        assert hashchain_to_txs[hashchain] == entry[3:]

    cursor.execute('SELECT * FROM evm_internal_transactions')
    for entry in cursor:
        hashchain = id_to_hashchain[entry[0]]
        assert hashchain_to_internaltxs[hashchain] == entry[1:]

    cursor.execute('SELECT * FROM evmtx_receipts')
    for entry in cursor:
        hashchain = id_to_hashchain[entry[0]]
        assert hashchain_to_receipts[hashchain] == entry[1:]

    hashchainlog_to_id = {}
    id_to_hashchainlog = {}
    cursor.execute('SELECT * FROM evmtx_receipt_logs')
    for entry in cursor:
        hashchain = id_to_hashchain[entry[1]]
        hashchainlog = hashchain + entry[2].to_bytes(4, byteorder='big')
        hashchainlog_to_id[hashchainlog] = entry[0]
        id_to_hashchainlog[entry[0]] = hashchainlog
        assert hashchainlog_to_logs[hashchainlog] == entry[3:]

    cursor.execute('SELECT * FROM evmtx_receipt_log_topics')
    for entry in cursor:
        hashchainlogindex = id_to_hashchainlog[entry[0]] + entry[2].to_bytes(4, byteorder='big')
        assert hashchainlogindex_to_topics[hashchainlogindex] == entry[1:]

    cursor.execute('SELECT * FROM evm_tx_mappings')
    for entry in cursor:
        hashchain = id_to_hashchain[entry[0]]
        assert hashchain_to_tx_mappings[hashchain] == entry[1:]

    cursor.execute('SELECT * FROM evmtx_address_mappings')
    for entry in cursor:
        hashchain = id_to_hashchain[entry[0]]
        assert hashchain_to_address_mappings[hashchain] == entry[1:]

    assert cursor.execute('SELECT identifier, notes FROM history_events WHERE entry_type==2 OR entry_type==5').fetchall() == [  # noqa: E501
        (539, 'Receive 95 ETH from 0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf'),
    ]  # make sure only 1 event remains, the one that was customized

    # Check Arbitrum One related data
    assert cursor.execute(  # Check that Arbitrum One location was added
        'SELECT location FROM location WHERE location=?',
        (Location.ARBITRUM_ONE.serialize_for_db(),),
    ).fetchone()[0] == Location.ARBITRUM_ONE.serialize_for_db()

    # check that nodes got correctly copied except for the duplicated one
    assert cursor.execute('SELECT * FROM rpc_nodes').fetchall() == [node for node in rpc_nodes if node[0] != 18]  # node 18 is the duplicated flashbot node # noqa: E501
    # check that inserting a node that already exists fails
    with db.conn.write_ctx() as write_cursor, pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member
        write_cursor.execute(
            'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',   # noqa: E501
            ('flashbots2', 'https://rpc.flashbots.net/', 0, 1, '0.2', 'ETH'),
        )

    # get current oracles and check that saddle was removed and all others remain as they were.
    settings = db.get_settings(cursor=cursor)
    expected_oracles = [CurrentPriceOracle.deserialize(oracle) for oracle in oracles if oracle != 'saddle']  # noqa: E501
    assert settings.current_price_oracles == expected_oracles
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_39_to_40(user_data_dir):  # pylint: disable=unused-argument
    """Test upgrading the DB from version 39 to version 40"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v39_rotkehlchen.db')
    db_v39 = _init_db_with_target_version(
        target_version=39,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db_v39.conn.cursor()
    cursor.execute('SELECT type, subtype from history_events WHERE event_identifier LIKE ?', (PREFIX,))  # noqa: E501
    events_types_before = set(cursor.fetchall())
    cursor.execute('SELECT type, subtype from history_events WHERE event_identifier NOT LIKE ?', (PREFIX,))  # noqa: E501
    other_events_types_before = set(cursor.fetchall())

    assert cursor.execute('SELECT * FROM history_events_mappings').fetchall() == [(7352, 'state', 1), (7353, 'state', 0)]  # all event mappings  # noqa: E501
    assert events_types_before == {
        ('deposit', 'spend'), ('deposit', 'fee'),
        ('withdrawal', 'receive'), ('withdrawal', 'fee'),
        ('receive', 'receive'), ('receive', 'fee'),
        ('spend', 'none'), ('spend', 'fee'),
        ('staking', 'reward'), ('staking', 'fee'),
    }
    # also check that the non rotki events are not affected
    assert other_events_types_before == {('deposit', 'spend'), ('deposit', 'none'), ('withdrawal', 'none'), ('withdrawal', 'fee'), ('receive', 'receive'), ('staking', 'fee'), ('receive', 'none'), ('remove_asset', 'staking')}  # noqa: E501
    # check that the evm events info is populated and connected to
    assert cursor.execute('SELECT * from evm_events_info').fetchall() == [
        (15, 'bytehash', 'aprotocol', 'aproduct', '0x4bBa290826C253BD854121346c370a9886d1bC26', None),  # noqa: E501
        (7352, 'hash', None, None, '0', None), (7353, 'hash', None, None, '0', None),
    ]
    assert cursor.execute('SELECT * from eth_staking_events_info').fetchall() == [(16, 19564, 0)]

    # check the tables we create don't exist and ones we remove exist before the upgrade
    assert table_exists(cursor, 'skipped_external_events') is False
    assert table_exists(cursor, 'accounting_rules') is False
    assert table_exists(cursor, 'ledger_action_type') is True
    assert table_exists(cursor, 'ledger_actions') is True

    # Check used query ranges before
    assert cursor.execute('SELECT * from used_query_ranges').fetchall() == [
        ('last_withdrawals_query_ts', 0, 1693141835),
        ('coinbase_ledger_actions_coinbase1', 0, 100),
        ('coinbase_ledger_actions_coinbase2', 500, 1000),
    ]
    # Check that ledger actions settings are there
    assert cursor.execute('SELECT COUNT(*) FROM settings WHERE name=?', ('taxable_ledger_actions',)).fetchone()[0] == 1  # noqa: E501
    # Check that ignored ledger actions are there
    assert cursor.execute('SELECT type, identifier FROM ignored_actions').fetchall() == [
        ('D', '2'), ('D', '7'),
    ]
    assert cursor.execute('SELECT type, seq FROM action_type').fetchall() == [
        ('A', 1), ('B', 2), ('C', 3), ('D', 4),
    ]
    # check settings in db for ledger accounting contains the airdrop type
    cursor.execute('SELECT value FROM settings where name=?', ('taxable_ledger_actions',))
    assert 'airdrop' in json.loads(cursor.fetchone()[0])

    # check the renaming of the VELO asset
    bnb_velo_asset_id = 'eip155:56/erc20:0xf486ad071f3bEE968384D2E39e2D8aF0fCf6fd46'
    assert cursor.execute(
        'SELECT asset FROM history_events WHERE identifier IN (?, ?)',
        ('10000', '10001'),
    ).fetchall() == [('VELO',), (bnb_velo_asset_id,)]
    assert cursor.execute(
        'SELECT base_asset FROM trades WHERE id=?',
        ('1a1ee5',),
    ).fetchall() == [('VELO',)]

    cursor.close()
    db_v39.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=40,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    cursor.execute('SELECT type, subtype from history_events WHERE event_identifier LIKE ?', (PREFIX,))  # noqa: E501
    events_types_after = set(cursor.fetchall())
    cursor.execute('SELECT type, subtype from history_events WHERE event_identifier NOT LIKE ?', (PREFIX,))  # noqa: E501
    other_events_types_after = set(cursor.fetchall())

    assert cursor.execute('SELECT * FROM history_events_mappings').fetchall() == [(7352, 'state', 1)]  # only customized event mapping  # noqa: E501
    assert events_types_after == {
        ('deposit', 'deposit asset'), ('spend', 'fee'),
        ('withdrawal', 'remove asset'), ('spend', 'fee'),
        ('receive', 'none'), ('spend', 'fee'),
        ('spend', 'none'), ('spend', 'fee'),
        ('staking', 'reward'), ('spend', 'fee'),
    }
    # also check that the non rotki events are not affected
    assert other_events_types_after == {('deposit', 'deposit asset'), ('withdrawal', 'remove asset'), ('withdrawal', 'fee'), ('receive', 'receive'), ('staking', 'fee'), ('receive', 'none'), ('spend', 'none'), ('receive', 'donate'), ('receive', 'airdrop'), ('remove_asset', 'staking')}  # noqa: E501
    # check that after upgrade tables depending on base history events are still connected
    assert cursor.execute('SELECT * from evm_events_info').fetchall() == [(7352, 'hash', None, None, '0', None)]  # noqa: E501
    assert cursor.execute('SELECT * from eth_staking_events_info').fetchall() == [(16, 19564, 0)]
    # check new tables are created and old are removed
    assert table_exists(cursor, 'skipped_external_events') is True
    assert table_exists(cursor, 'accounting_rules') is True
    assert table_exists(cursor, 'ledger_action_type') is False
    assert table_exists(cursor, 'ledger_actions') is False

    assert cursor.execute(  # Check that BASE and GNOSIS locations were added
        'SELECT location FROM location WHERE seq IN (?, ?) ORDER BY seq',
        (Location.BASE.value, Location.GNOSIS.value),
    ).fetchall() == [(Location.BASE.serialize_for_db(),), (Location.GNOSIS.serialize_for_db(),)]

    # test that all 8 ledger actions were moved to history events
    assert all(x == (1, 0) for x in cursor.execute("SELECT entry_type, sequence_index from history_events WHERE event_identifier LIKE 'MLA_%'"))  # noqa: E501
    assert cursor.execute("SELECT timestamp, location, location_label, asset, amount, notes, type, subtype from history_events WHERE event_identifier LIKE 'MLA_%'").fetchall() == [  # noqa: E501
        (1674229230000, 'A', None, 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', '100', 'This is my income action. Migrated from a ledger action of income type. https://alink.com', 'receive', 'none'),  # noqa: E501
        (1695307330000, 'B', None, 'ETH', '0.5', 'I lost ETH here. Migrated from a ledger action of loss type. https://etherscan.io/tx/0x4677ffa104b011d591ae0c056ba651a978db982c0dfd131520db74c1b46ff564', 'spend', 'none'),  # noqa: E501
        (1695480219000, 'J', None, 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', '50', 'Migrated from a ledger action of donation received type', 'receive', 'donate'),  # noqa: E501
        (1695566739000, 'J', None, 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7', '50', 'Spent $50 for lunch. Migrated from a ledger action of expense type', 'spend', 'none'),  # noqa: E501
        (1695739914000, 'J', None, 'eip155:1/erc20:0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F', '10', 'Got dividends in GTC for some reason.. Migrated from a ledger action of dividends income type', 'receive', 'none'),  # noqa: E501
        (1695826372000, 'J', None, 'eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302', '69', 'Hue hue 69 1inch tokens airdrop. Hue hue!. Migrated from a ledger action of airdrop type', 'receive', 'airdrop'),  # noqa: E501
        (1696085745000, 'B', None, 'BTC', '1', 'Kraken gave me 1 BTC because I am a good boy. Migrated from a ledger action of gift type', 'receive', 'none'),  # noqa: E501
        (1695913006000, 'h', None, 'eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', '1000', 'Polygon paid us for something (as if). Migrated from a ledger action of grant type. https://polygonscan.com/tx/0xc0b96f46f7d2be3e5b68583b1223cab0d46526a6a37415a125698687c7cbd87d', 'receive', 'none'),  # noqa: E501
    ]
    # Assert used query ranges got updated
    assert cursor.execute('SELECT * from used_query_ranges').fetchall() == [
        ('coinbase_history_events_coinbase1', 0, 100),  # notice withdrawals old range is deleted
        ('coinbase_history_events_coinbase2', 500, 1000),
    ]
    # Check that ledger actions settings are removed
    assert cursor.execute('SELECT COUNT(*) FROM settings WHERE name=?', ('taxable_ledger_actions',)).fetchone()[0] == 0  # noqa: E501
    # Check that ignored ledger actions are removed
    assert cursor.execute('SELECT type, identifier FROM ignored_actions').fetchall() == []
    assert cursor.execute('SELECT type, seq FROM action_type').fetchall() == [
        ('A', 1), ('B', 2), ('C', 3),
    ]
    # check that we have a defined accounting rule for aidrops coming from ledger actions
    accounting_row = cursor.execute(
        "SELECT * FROM accounting_rules WHERE type='receive' AND subtype='airdrop'",
    ).fetchone()
    assert accounting_row[:4] == (1, 'receive', 'airdrop', 'NONE')
    assert BaseEventSettings(
        taxable=True,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        accounting_treatment=None,
    ).serialize() == BaseEventSettings.deserialize_from_db(accounting_row[4:]).serialize()

    # check that the replacement for the VELO asset worked
    assert cursor.execute(
        'SELECT COUNT(*) FROM assets WHERE identifier=?',
        ('VELO',),
    ).fetchone()[0] == 0
    assert cursor.execute(
        'SELECT asset FROM history_events WHERE identifier IN (?, ?)',
        ('10000', '10001'),
    ).fetchall() == [(bnb_velo_asset_id,)] * 2
    assert cursor.execute(
        'SELECT base_asset FROM trades WHERE id=?',
        ('1a1ee5',),
    ).fetchall() == [(bnb_velo_asset_id,)]
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('address_name_priority', [
    (  # customized to prioritized blockchain_account, no values should be replaced
        'blockchain_account',
        'private_addressbook',
        'global_addressbook',
        'ethereum_tokens',
        'hardcoded_mappings',
        'ens_names',
    ), (  # blockchain_account missing, result should have two values replaced
        'private_addressbook',
        'global_addressbook',
        'ethereum_tokens',
        'hardcoded_mappings',
        'ens_names',
    ),
    None,  # no setting, result should have two values replaced
])
def test_upgrade_db_40_to_41(user_data_dir, address_name_priority, messages_aggregator):
    """Test upgrading the DB from version 40 to version 41"""
    _use_prepared_db(user_data_dir, 'v40_rotkehlchen.db')
    db_v40 = _init_db_with_target_version(
        target_version=40,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    # add some settings and used_query_ranges that should/shouldn't move in the upgrade
    should_move_settings = {
        'last_balance_save': '234',
        'last_data_upload_ts': '345',
        'last_data_updates_ts': '456',
        'last_owned_assets_update': '567',
        'last_evm_accounts_detect_ts': '678',
        'last_spam_assets_detect_key': '789',
        'last_augmented_spam_assets_detect_key': '890',
    }
    should_not_move_settings = {
        'version': '40',
        'last_write_ts': '890',
        'spam_assets_version': '901',
        'rpc_nodes_version': '12',
        'contracts_version': '123',
        'global_addressbook_version': '234',
        'accounting_rules_version': '345',
        'non_syncing_exchanges': '[{"name": "Kraken 1", "location": "kraken"}]',
    }
    if address_name_priority is not None:
        should_not_move_settings['address_name_priority'] = json.dumps(address_name_priority)
    should_move_used_query_ranges = {
        'ethwithdrawalsts_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12': '123',
        'ethwithdrawalsts_0xc37b40ABdB939635068d3c5f13E7faF686F03B65': '123',
        'ethwithdrawalsidx_0xc37b40ABdB939635068d3c5f13E7faF686F03B65': '234',
        f'{Location.BITSTAMP}_bitstamp1_last_cryptotx_offset': '345',
        f'{Location.COINBASE}_coinbase1_123_last_query_ts': '456',
        f'{Location.COINBASE}_coinbase1_123_last_query_id': '567',
        'last_produced_blocks_query_ts': '678',
        'last_withdrawals_exit_query_ts': '789',
        'last_events_processing_task_ts': '890',
    }
    should_not_move_used_query_ranges = {
        'coinbase_trades_Coinbase 1': '123',
        'coinbase_margins_Coinbase 1': '234',
        'coinbase_asset_movements_Coinbase 1': '345',
        'balancer_events_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12': '456',
        'balancer_events_0xc37b40ABdB939635068d3c5f13E7faF686F03B65': '456',
        'binance_history_events_binance1': '567',
        'binance_lending_history_binance1': '678',
        'yearn_vaults_events_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12': '789',
        'yearn_vaults_v2_events_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12': '890',
        'gnosisbridge_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12': '901',
    }
    with db_v40.conn.write_ctx() as cursor:
        assert table_exists(cursor, 'key_value_cache') is False
        cursor.execute('SELECT name FROM settings;')
        for names in cursor:
            assert names[0] in should_move_settings | should_not_move_settings
        cursor.execute('SELECT name FROM used_query_ranges;')
        for names in cursor:
            if names[0].startswith('bittrex'):
                continue  # those will be removed
            assert names[0] in should_move_used_query_ranges | should_not_move_used_query_ranges
        cursor.execute('SELECT COUNT(*) FROM location WHERE location=? AND seq=?', ('m', 45))
        assert cursor.fetchone()[0] == 0
        assert cursor.execute('SELECT * FROM blockchain_accounts;').fetchall() == [
            ('eth', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'eth1_blockchain_accounts'),
            ('eth', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'eth2_blockchain_accounts'),
            ('btc', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'btc1_blockchain_accounts'),
            ('btc', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'btc2_blockchain_accounts'),
        ]
        assert cursor.execute('SELECT * FROM address_book').fetchall() == [
            ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'eth', 'eth1_address_book'),
            ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'btc', 'btc1_address_book'),
        ]  # eth1 and btc1 already exists in address_book
        if address_name_priority is not None:
            cursor.execute(
                'INSERT INTO settings(name, value) VALUES(?, ?)',
                ('address_name_priority', json.dumps(address_name_priority)),
            )
        # check that we have bittrex information that needs to be removed
        assert cursor.execute(
            'SELECT COUNT(*) FROM user_credentials WHERE location=?',
            ('D',),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{Location.BITTREX!s}\\_%', '\\'),
        ).fetchone()[0] == 3

    # test external credentials are there
    with db_v40.conn.read_ctx() as cursor:
        assert table_exists(
            cursor=cursor,
            name='external_service_credentials',
            schema="""CREATE TABLE external_service_credentials (
            name VARCHAR[30] NOT NULL PRIMARY KEY,
            api_key TEXT
            )""") is True
        assert table_exists(
            cursor=cursor,
            name='blockchain_accounts',
            schema="""CREATE TABLE IF NOT EXISTS blockchain_accounts (
                blockchain VARCHAR[24] NOT NULL,
                account TEXT NOT NULL,
                label TEXT,
                PRIMARY KEY (blockchain, account)
            );""",
        )
        assert cursor.execute('SELECT * FROM external_service_credentials').fetchall() == [('etherscan', 'LOL'), ('blockscout', 'LOL2'), ('covalent', 'lollol')]  # noqa: E501
        # verify that the history_events exists before upgrade
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 10
        assert cursor.execute("SELECT COUNT(*) FROM history_events WHERE location = 'B'").fetchone()[0] == 2  # kraken events: one valid and one that needs to be removed # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM evm_events_info').fetchone()[0] == 8
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        ).fetchone()[0] == 1  # one event is customized

        # test eth2 validators and daily stats are there
        assert table_exists(
            cursor=cursor,
            name='eth2_validators',
            schema="""CREATE TABLE IF NOT EXISTS eth2_validators (
                validator_index INTEGER NOT NULL PRIMARY KEY,
                public_key TEXT NOT NULL UNIQUE,
                ownership_proportion TEXT NOT NULL
            );""",
        )
        validators_data = [
            (42, '0xb0fee189ffa7ddb3326ef685c911f3416e15664ff1825f3b8e542ba237bd3900f960cd6316ef5f8a5adbaf4903944013', '1.0'),  # noqa: E501
            (1232, '0xa15f29dd50327bc53b02d34d7db28f175ffc21d7ffbb2646c8b1b82bb6bca553333a19fd4b9890174937d434cc115ace', '0.35'),  # noqa: E501
            (5232, '0xb052a2b421770b99c2348b652fbdc770b2a27a87bf56993dff212d839556d70e7b68f5d953133624e11774b8cb81129d', '1.0'),  # noqa: E501
        ]
        assert cursor.execute('SELECT * from eth2_validators').fetchall() == validators_data
        daily_stats = [
            (42, 1707001200, '0.001'), (1232, 1707001200, '0.0005'), (5232, 1707001200, '0.0009'),
            (42, 1706914800, '0.0201'), (1232, 1706914800, '0.0008'), (5232, 1706914800, '0.001'),
            (42, 1706828400, '0.00075'), (1232, 1706828400, '0.00052'), (5232, 1706828400, '0.00083'),  # noqa: E501
        ]
        assert cursor.execute('SELECT * from eth2_daily_staking_details').fetchall() == daily_stats

    db_v40.logout()

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=41,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    assert messages_aggregator.consume_errors() == []
    assert messages_aggregator.consume_warnings() == []
    # check if all the above values have been moved
    with db.conn.read_ctx() as cursor:
        assert table_exists(cursor, 'key_value_cache', """CREATE TABLE key_value_cache (
        name TEXT NOT NULL PRIMARY KEY,
        value TEXT
    )""") is True
        cache_values = cursor.execute('SELECT name, value FROM key_value_cache').fetchall()
        assert len(cache_values) == len(should_move_settings) + len(should_move_used_query_ranges) + 1  # 1 is for the last_db_upgrade_ts  # noqa: E501
        for name, value in cache_values:
            if name == 'last_db_upgrade':
                continue  # this unrelated

            assert name not in should_not_move_settings
            assert name not in should_not_move_used_query_ranges
            if name in should_move_settings:
                assert value == should_move_settings[name]
            elif name in should_move_used_query_ranges:
                assert value == should_move_used_query_ranges[name]
            else:
                pytest.fail(f'{name} should not end up in key_value_cache table')
        db_settings = cursor.execute('SELECT name FROM settings').fetchall()
        assert len(db_settings) == len(should_not_move_settings)
        for name in db_settings:
            assert name[0] not in should_move_settings
            assert name[0] in should_not_move_settings
        db_used_query_ranges = cursor.execute('SELECT name FROM used_query_ranges').fetchall()
        assert len(db_used_query_ranges) == len(should_not_move_used_query_ranges)
        for name in db_used_query_ranges:
            assert name[0] not in should_move_used_query_ranges
            assert name[0] in should_not_move_used_query_ranges
        cursor.execute('SELECT COUNT(*) FROM location WHERE location=? AND seq=?', ('m', 45))
        assert cursor.fetchone()[0] == 1

        # test external credentials have been upgraded
        assert table_exists(
            cursor=cursor,
            name='external_service_credentials',
            schema="""CREATE TABLE external_service_credentials (
            name VARCHAR[30] NOT NULL PRIMARY KEY,
            api_key TEXT NOT NULL,
            api_secret TEXT
            )""") is True
        assert cursor.execute('SELECT * FROM external_service_credentials').fetchall() == [('etherscan', 'LOL', None), ('blockscout', 'LOL2', None)]  # noqa: E501

        # test if blockchain_accounts labels have been moved to address_book
        if address_name_priority is None or address_name_priority[0] == 'private_addressbook':
            assert cursor.execute('SELECT * FROM address_book').fetchall() == [
                ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'eth', 'eth1_address_book'),
                ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'btc', 'btc1_address_book'),
                ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'eth', 'eth2_blockchain_accounts'),
                ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'btc', 'btc2_blockchain_accounts'),
            ]
        else:
            assert cursor.execute('SELECT * FROM address_book').fetchall() == [
                ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'eth', 'eth1_blockchain_accounts'),
                ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'eth', 'eth2_blockchain_accounts'),
                ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'btc', 'btc1_blockchain_accounts'),
                ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'btc', 'btc2_blockchain_accounts'),
            ]
        assert table_exists(
            cursor=cursor,
            name='blockchain_accounts',
            schema="""CREATE TABLE IF NOT EXISTS blockchain_accounts (
                blockchain VARCHAR[24] NOT NULL,
                account TEXT NOT NULL,
                PRIMARY KEY (blockchain, account)
            );""",
        )
        # verify that the history_events are removed, except the one that is customized
        # and the kraken informational event
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 2
        assert cursor.execute('SELECT COUNT(*) FROM evm_events_info').fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM user_credentials WHERE location=?',
            ('D',),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{Location.BITTREX!s}\\_%', '\\'),
        ).fetchone()[0] == 0
        assert json.loads(cursor.execute(
            'SELECT value FROM settings WHERE name=?',
            ('non_syncing_exchanges',),
        ).fetchone()[0]) == [{'name': 'Kraken 1', 'location': 'kraken'}]

        # verify that the new eth2 validators table and data is there
        assert table_exists(
            cursor=cursor,
            name='eth2_validators',
            schema="""CREATE TABLE IF NOT EXISTS eth2_validators (
                identifier INTEGER NOT NULL PRIMARY KEY,
                validator_index INTEGER UNIQUE,
                public_key TEXT NOT NULL UNIQUE,
                ownership_proportion TEXT NOT NULL,
                withdrawal_address TEXT,
                activation_timestamp INTEGER,
                withdrawable_timestamp INTEGER
            );""",
        )
        assert cursor.execute('SELECT validator_index, public_key, ownership_proportion from eth2_validators').fetchall() == validators_data  # noqa: E501
        assert cursor.execute('SELECT * from eth2_daily_staking_details').fetchall() == daily_stats

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_41_to_42(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 41 to version 42"""
    _use_prepared_db(user_data_dir, 'v41_rotkehlchen.db')
    db_v41 = _init_db_with_target_version(
        target_version=41,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db_v41.conn.write_ctx() as cursor:
        assert table_exists(cursor, 'zksynclite_tx_type') is False
        assert table_exists(cursor, 'zksynclite_transactions') is False
        assert table_exists(cursor, 'calendar') is False
        assert table_exists(cursor, 'calendar_reminders') is False

        # history events that need to be deleted because their transaction are not in the database
        expected_events_ids = [(17987,), (17988,), (17989,)]
        assert cursor.execute(
            'SELECT identifier FROM history_events ORDER BY identifier',
        ).fetchall() == expected_events_ids
        assert cursor.execute(
            'SELECT identifier FROM evm_events_info',
        ).fetchall() == expected_events_ids
        assert cursor.execute(
            'SELECT parent_identifier FROM history_events_mappings',
        ).fetchall() == expected_events_ids

        assert cursor.execute('SELECT MAX(seq) FROM location').fetchone()[0] == 45
        assert cursor.execute('SELECT COUNT(tx_hash) FROM balancer_events').fetchone()[0] == 2
        assert cursor.execute('SELECT name from used_query_ranges').fetchall() == [
            ('ETHinternaltxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('ETHtokentxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('ETHtxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('GNOSISinternaltxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('GNOSIStokentxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('GNOSIStxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('balancer_events_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('gnosisbridge_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('kraken_asset_movements_kraken',),
            ('kraken_history_events_kraken',),
            ('kraken_margins_kraken',),
            ('kraken_trades_kraken',),
            ('yearn_vaults_events_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('yearn_vaults_v2_events_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
        ]
        assert cursor.execute(
            'SELECT COUNT(*), version FROM yearn_vaults_events GROUP BY version',
        ).fetchall() == [(2, 1), (3, 2)]
        raw_list = cursor.execute(
            'SELECT value FROM settings WHERE name=?', ('evmchains_to_skip_detection',),
        ).fetchone()[0]
        assert [
            ChainID.deserialize_from_name(x) for x in json.loads(raw_list)
        ] == [ChainID.POLYGON_POS, ChainID.GNOSIS]

        # get settings and confirm manualcurrent is present before the upgrade
        cursor.execute("SELECT value FROM settings WHERE name='current_price_oracles'")
        oracles = json.loads(cursor.fetchone()[0])
        assert 'manualcurrent' in oracles

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=42,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    assert messages_aggregator.consume_errors() == []
    assert messages_aggregator.consume_warnings() == []

    with db.conn.read_ctx() as cursor:
        assert table_exists(cursor, 'zksynclite_tx_type') is True
        assert table_exists(cursor, 'zksynclite_transactions') is True
        assert table_exists(cursor, 'calendar') is True
        assert table_exists(cursor, 'calendar_reminders') is True
        assert table_exists(cursor, 'balancer_events') is False
        assert table_exists(cursor, 'yearn_vaults_events') is False
        assert cursor.execute('SELECT name from used_query_ranges').fetchall() == [
            ('ETHinternaltxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('ETHtokentxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('ETHtxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('GNOSISinternaltxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('GNOSIStokentxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('GNOSIStxs_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('gnosisbridge_0x7716a99194d758c8537F056825b75Dd0C8FDD89f',),
            ('kraken_asset_movements_kraken',),
            ('kraken_history_events_kraken',),
            ('kraken_margins_kraken',),
            ('kraken_trades_kraken',),
        ]
        assert cursor.execute('SELECT * FROM zksynclite_tx_type').fetchall() == [
            ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5), ('F', 6), ('G', 7),
        ]
        for new_loc in (Location.SCROLL, Location.ZKSYNC_LITE):
            assert cursor.execute(  # Check that new locations were added
                'SELECT location FROM location WHERE seq=?',
                (new_loc.value,),
            ).fetchone()[0] == new_loc.serialize_for_db()
        raw_list = cursor.execute(
            'SELECT value FROM settings WHERE name=?', ('evmchains_to_skip_detection',),
        ).fetchone()[0]
        assert [
            SupportedBlockchain.deserialize(x) for x in json.loads(raw_list)
        ] == [SupportedBlockchain.POLYGON_POS, SupportedBlockchain.GNOSIS]

        # get current oracles and check that manualcurrent was removed and all others remain.
        settings = db.get_settings(cursor=cursor)
        assert CurrentPriceOracle.MANUALCURRENT not in settings.current_price_oracles

        # the evm events with the exception of 17987 don't have a transaction
        # in the db, and should have been deleted
        assert cursor.execute('SELECT identifier FROM history_events').fetchall() == [(17987,)]
        assert cursor.execute('SELECT identifier FROM evm_events_info').fetchall() == [(17987,)]
        assert cursor.execute(
            'SELECT parent_identifier FROM history_events_mappings',
        ).fetchall() == [(17987,)]
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_42_to_43(user_data_dir, messages_aggregator, data_dir):
    """Test upgrading the DB from version 42 to version 43"""
    _use_prepared_db(user_data_dir, 'v42_rotkehlchen.db')
    db_v42 = _init_db_with_target_version(
        target_version=42,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    test_address = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
    with db_v42.conn.read_ctx() as cursor:
        nfts = cursor.execute('SELECT name FROM nfts').fetchall()
        assert nfts == [('yabir.eth',)]
        assert cursor.execute(
            'SELECT location from history_events WHERE location_label=?',
            (test_address,),
        ).fetchall() == [(Location.ZKSYNC_LITE.serialize_for_db(),), (Location.POLYGON_POS.serialize_for_db(),)]  # noqa: E501
        # check hop-protocol counterparty is there
        assert cursor.execute('SELECT COUNT(*) from evm_events_info WHERE counterparty=?', ('hop-protocol',)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from evm_events_info WHERE counterparty=?', ('hop',)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute(
            'INSERT INTO user_credentials VALUES (?, ?, ?, ?, ?)',
            ('coinbasepro', Location.COINBASEPRO.serialize_for_db(), 'api_key', 'api_secret', 'passphrase'),  # noqa: E501
        ).rowcount == 1

    # create csv files that will be deleted in the db upgrade and a parquet one to keep
    airdrops_dir = data_dir / APPDIR_NAME / AIRDROPSDIR_NAME
    airdrops_dir.mkdir(parents=True)
    uniswap_path = airdrops_dir / 'uniswap.csv'
    zk_path = airdrops_dir / 'zk.csv'
    zk_parquet_path = airdrops_dir / 'zk.parquet'
    uniswap_path.touch()
    zk_path.touch()
    zk_parquet_path.touch()
    assert uniswap_path.exists() is True
    assert zk_path.exists() is True

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=43,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    assert messages_aggregator.consume_errors() == []
    assert messages_aggregator.consume_warnings() == []

    with db.conn.read_ctx() as cursor:
        nfts = cursor.execute('SELECT name, usd_price FROM nfts').fetchall()
        assert nfts == [('yabir.eth', 0)]
        # assert hop-protocol counterparty got renamed
        assert cursor.execute(
            'SELECT location from history_events WHERE location_label=?',
            (test_address,),
        ).fetchall() == [(Location.ZKSYNC_LITE.serialize_for_db(),)]
        assert cursor.execute('SELECT COUNT(*) from evm_events_info WHERE counterparty=?', ('hop-protocol',)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from evm_events_info WHERE counterparty=?', ('hop',)).fetchone()[0] == 1  # noqa: E501

        cursor.execute('SELECT seq FROM location WHERE location=?', 'p')
        assert cursor.fetchone() == (Location.HTX.value,)
        assert cursor.execute(
            'SELECT COUNT(*) FROM user_credentials WHERE location=?',
            (Location.COINBASEPRO.serialize_for_db(),),
        ).fetchone()[0] == 0

    assert uniswap_path.exists() is False
    assert zk_path.exists() is False
    assert zk_parquet_path.exists() is True
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_43_to_44(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 43 to version 44"""
    _use_prepared_db(user_data_dir, 'v43_rotkehlchen.db')
    db_v43 = _init_db_with_target_version(
        target_version=43,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    bad_address, tether_address = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'  # noqa: E501
    with db_v43.conn.read_ctx() as cursor:
        assert cursor.execute(  # we have one entry with null values and two with the details
            'SELECT identifier, last_price, last_price_asset FROM nfts',
        ).fetchall() == [
            ('_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'ETH'),  # noqa: E501
            ('_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041', '0.00059', 'ETH'),  # noqa: E501
            ('_nft_0x88997988a6a5aaf29ba973d298d276fe75fb69ab_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', None, None),  # noqa: E501
        ]
        assert set(cursor.execute('SELECT object_reference, tag_name FROM tag_mappings').fetchall()) == {  # noqa: E501
            ('ETH0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'safe'),
            ('OPTIMISM0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'safe'),
            ('GNOSIS0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'safe'),
            ('5', 'staked'),
            ('13', 'beefy'),
            ('ARBITRUM_ONE0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'safe'),
            ('GNOSIS0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'beefy'),
        }
        old_receipt_logs = cursor.execute('SELECT * from evmtx_receipt_logs').fetchall()
        assert set(cursor.execute(
            'SELECT * FROM address_book WHERE address IN (?, ?)',
            (bad_address, tether_address),
        ).fetchall()) == {
            (tether_address, None, 'Black Tether'),
            (bad_address, None, 'yabirgb.eth'),
            (bad_address, None, 'yabir.eth'),
        }
        assert cursor.execute(  # check that the new locations we add are not in the DB before
            'SELECT COUNT(*) FROM location WHERE location IN (?, ?, ?, ?)',
            (
                Location.BITCOIN.serialize_for_db(),
                Location.BITCOIN_CASH.serialize_for_db(),
                Location.POLKADOT.serialize_for_db(),
                Location.KUSAMA.serialize_for_db(),
            ),
        ).fetchone()[0] == 0

    with db_v43.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO settings(name, value) VALUES(?, ?)',
            ('historical_price_oracles', '["manual", "cryptocompare", "coingecko", "defillama"]'),
        )
        db_v43.update_used_query_range(
            write_cursor=write_cursor,
            name='zksynclitetxs_0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=44,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    assert messages_aggregator.consume_errors() == []
    assert messages_aggregator.consume_warnings() == []

    with db.conn.read_ctx() as cursor:
        assert cursor.execute(  # we have one entry with null values and two with the details
            'SELECT identifier, last_price, last_price_asset FROM nfts',
        ).fetchall() == [
            ('_nft_0xfd9d8036F899ed5a9fD8cac7968E5F24D3db2A64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'ETH'),  # noqa: E501
            ('_nft_0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85_26612040215479394739615825115912800930061094786769410446114278812336794170041', '0.00059', 'ETH'),  # noqa: E501
            ('_nft_0x88997988a6A5aAF29BA973d298D276FE75fb69ab_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'ETH'),  # noqa: E501
        ]
        new_receipt_logs = cursor.execute('SELECT * from evmtx_receipt_logs').fetchall()
        assert new_receipt_logs == [(x[0], x[1], x[2], x[3], x[4]) for x in old_receipt_logs]
        assert set(cursor.execute('SELECT object_reference, tag_name FROM tag_mappings').fetchall()) == {  # noqa: E501
            ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'safe'),
            ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'beefy'),
            ('5', 'staked'),
            ('13', 'beefy'),
        }
        # check that addressbook addresses got correctly migrated
        assert set(cursor.execute(
            'SELECT * FROM address_book WHERE address IN (?, ?)',
            (bad_address, tether_address),
        ).fetchall()) == {
            (tether_address, 'NONE', 'Black Tether'),
            (bad_address, 'NONE', 'yabirgb.eth'),
        }
        assert cursor.execute(
            "SELECT value FROM settings WHERE name='historical_price_oracles'",
        ).fetchone()[0] == '["manual", "cryptocompare", "coingecko", "defillama", "uniswapv3", "uniswapv2"]'  # noqa: E501
        assert cursor.execute(
            "SELECT * FROM used_query_ranges WHERE name LIKE 'zksynclitetxs\\_%' ESCAPE '\\'",
        ).fetchone() is None
        assert cursor.execute(  # check that the new locations we add are now in the DB
            'SELECT COUNT(*) FROM location WHERE location IN (?, ?, ?, ?)',
            (
                Location.BITCOIN.serialize_for_db(),
                Location.BITCOIN_CASH.serialize_for_db(),
                Location.POLKADOT.serialize_for_db(),
                Location.KUSAMA.serialize_for_db(),
            ),
        ).fetchone()[0] == 4

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_44_to_45(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 43 to version 44"""
    _use_prepared_db(user_data_dir, 'v43_rotkehlchen.db')
    db_v43 = _init_db_with_target_version(
        target_version=43,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db_v43.conn.read_ctx() as cursor:
        cursor.execute("SELECT COUNT(*) FROM location WHERE location='u'")
        assert cursor.fetchone()[0] == 0

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=45,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db.conn.read_ctx() as cursor:
        cursor.execute("SELECT seq FROM location WHERE location='u'")
        assert cursor.fetchone() == (53,)

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_45_to_46(user_data_dir: 'Path', messages_aggregator):
    """Test upgrading the DB from version 45 to version 46"""
    _use_prepared_db(user_data_dir, 'v45_rotkehlchen.db')
    db_v45 = _init_db_with_target_version(
        target_version=45,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db_v45.conn.read_ctx() as cursor:
        cursor.execute("SELECT value FROM settings where name='active_modules'")
        old_active_modules = json.loads(cursor.fetchone()[0])
        assert 'balancer' in old_active_modules

        icons_dir = user_data_dir.parent.parent / IMAGESDIR_NAME / ASSETIMAGESDIR_NAME / ALLASSETIMAGESDIR_NAME  # noqa: E501
        icons_dir.mkdir(parents=True, exist_ok=True)
        icon_path = icons_dir / f'{urllib.parse.quote_plus(A_COW.identifier)}_small.png'
        icon_path.write_bytes(b'0x0x')

        assert cursor.execute(
            "SELECT COUNT(*) FROM pragma_table_info('history_events') WHERE name='extra_data'",
        ).fetchone()[0] == 0
        assert cursor.execute(
            "SELECT COUNT(*) FROM pragma_table_info('evm_events_info') WHERE name='extra_data'",
        ).fetchone()[0] == 1
        existing_evm_event = cursor.execute('SELECT * FROM history_events WHERE identifier = "35"').fetchone()  # noqa: E501
        existing_evm_event_extra_data = cursor.execute('SELECT extra_data FROM evm_events_info WHERE identifier = "35"').fetchone()[0]  # noqa: E501
        assert existing_evm_event_extra_data == '{"airdrop_identifier": "elfi"}'
        assert cursor.execute('SELECT COUNT(*) FROM asset_movements').fetchone()[0] == 3
        assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE event_identifier=?', ('KRAKEN-XXX',)).fetchone()[0] == 2  # kraken history event that needs to be removed since it will be replaced  # noqa: E501

    # Add a plain history event to the db to be checked after upgrade that it wasn't modified
    # Note that it has to be manually inserted here since the functions for creating
    # history events now expect there to be an extra_data column in history_events
    history_event_bindings = [HistoryBaseEntryType.HISTORY_EVENT.value, 'TEST1', 0, 1, Location.KRAKEN.serialize_for_db(), 'Somewhere', A_ETH.identifier, 1, 3000, 'Just a test event', HistoryEventType.INFORMATIONAL.value, HistoryEventSubType.NONE.value]  # noqa: E501
    with db_v45.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO history_events(entry_type, event_identifier, sequence_index, '
            'timestamp, location, location_label, asset, amount, usd_value, notes, '
            'type, subtype) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            history_event_bindings,
        )
        # Ensure account_for_assets_movements is set before upgrade
        write_cursor.execute("INSERT OR IGNORE INTO settings(name, value) VALUES ('account_for_assets_movements', 'True')")  # noqa: E501
        # Make the existing evm event customized so it isn't removed during the upgrade
        write_cursor.execute(
            "INSERT INTO history_events_mappings(parent_identifier, name, value) VALUES ('35', ?, ?)",  # noqa: E501
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=46,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    assert not icon_path.exists()
    with db.conn.read_ctx() as cursor:
        cursor.execute("SELECT value FROM settings where name='active_modules'")
        new_active_modules = json.loads(cursor.fetchone()[0])
        assert old_active_modules != new_active_modules
        assert [i for i in old_active_modules if i != 'balancer'] == new_active_modules

        assert cursor.execute(
            "SELECT COUNT(*) FROM pragma_table_info('history_events') WHERE name='extra_data'",
        ).fetchone()[0] == 1
        assert cursor.execute(
            "SELECT COUNT(*) FROM pragma_table_info('evm_events_info') WHERE name='extra_data'",
        ).fetchone()[0] == 0

        # Confirm an evm event with extra data has been migrated correctly
        assert (*existing_evm_event, existing_evm_event_extra_data) == cursor.execute(
            'SELECT * FROM history_events WHERE identifier = "35"',
        ).fetchone()

        # Confirm a plain history event has not been modified and has null extra_data
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE entry_type=? AND event_identifier=? AND '
            'sequence_index=? AND timestamp=? AND location=? AND location_label=? AND asset=? AND '
            'amount=? AND usd_value=? AND notes=? AND type=? AND subtype=? AND extra_data IS NULL',
            history_event_bindings,
        ).fetchone()[0] == 1

        # Don't check notes here since the way the AssetMovement class handles notes changed after
        # this upgrade, preventing the upgrade code from handling the notes as it did originally.
        assert cursor.execute(
            'SELECT entry_type, event_identifier, sequence_index, '
            'timestamp, location, location_label, asset, amount, usd_value, '
            'type, subtype, extra_data FROM history_events WHERE entry_type=6',
        ).fetchall() == [
            (6, '20522c693bcda4ef646682c6a58bb0349b01f4d7b9168a62ce94b2c8dd1fe639', 0, 1644244023000, 'B', 'kraken', 'ATOM', '3.40000000', '0', 'withdrawal', 'remove asset', '{"reference": "KRAKEN-XXX"}'),  # noqa: E501
            (6, '20522c693bcda4ef646682c6a58bb0349b01f4d7b9168a62ce94b2c8dd1fe639', 1, 1644244023000, 'B', 'kraken', 'ATOM', '0.10000000', '0', 'withdrawal', 'fee', None),  # noqa: E501
            (6, '1cf3fc675d4835efe532d18730db35163b07fb5f44956b888d7aaf852b04fd1c', 0, 1727542684000, 'G', None, 'ETH', '0.07126231', '0', 'deposit', 'deposit asset', '{"address": "0xc37b40ABdB939635068d3c5f13E7faF686F03B65", "transaction_id": "0xc8aa60c9f8a93692b66fbc3f57c64f2b1c4afd92f370e12dc7bb23acfa303dbb"}'),  # noqa: E501
            (6, 'dd253e55b9e3bd672d98f49062a27d6d9946427061b7d36083d78146e6dcce73', 0, 1676524754000, 'B', 'kraken', 'eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', '10', '0', 'withdrawal', 'remove asset', '{"reference": "KRAKEN-XXX"}'),  # noqa: E501
            (6, 'dd253e55b9e3bd672d98f49062a27d6d9946427061b7d36083d78146e6dcce73', 1, 1676524754000, 'B', 'kraken', 'eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', '0.0100000000', '0', 'withdrawal', 'fee', None),  # noqa: E501
        ]
        assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE event_identifier=?', ('KRAKEN-XXX',)).fetchone()[0] == 0  # noqa: E501

        assert table_exists(cursor, 'asset_movements') is False
        assert table_exists(cursor, 'asset_movement_category') is False

        assert cursor.execute(
            "SELECT COUNT(*) FROM settings WHERE name='account_for_assets_movements'",
        ).fetchone()[0] == 0

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_46_to_47(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 46 to version 47. This happened in 1.38"""

    def _check_tokens_existence(user_db_cursor: 'DBCursor', expect_removed: bool = False):
        """Assert whether the tokens are in the db or not depending on `expect_removed`"""
        for table, column, count in [
            ('assets', 'identifier', 2),
            ('history_events', 'asset', 1),
            ('timed_balances', 'currency', 1),
            ('evm_accounts_details', 'value', 2),
            ('manually_tracked_balances', 'asset', 1),
        ]:
            assert user_db_cursor.execute(
                f'SELECT COUNT(*) FROM {table} WHERE {column} IN (?, ?)',
                (uniswap_erc20_token.identifier, uniswap_erc721_token.identifier),
            ).fetchone()[0] == 0 if expect_removed else count

        with GlobalDBHandler().conn.read_ctx() as global_db_cursor:
            assert global_db_cursor.execute(
                'SELECT COUNT(*) FROM assets WHERE identifier IN (?, ?, ?)',
                (uniswap_erc20_token.identifier, uniswap_erc721_token.identifier, basename_token.identifier),  # noqa: E501
            ).fetchone()[0] == 0 if expect_removed else 3
            assert global_db_cursor.execute(
                'SELECT COUNT(*) FROM assets WHERE identifier IN (?, ?)',
                (erc721_token_with_id.identifier, basename_token_with_id.identifier),
            ).fetchone()[0] == 2  # tokens with collectible ids shouldn't be modified

        if expect_removed:
            temp_erc721_data = user_db_cursor.execute('SELECT * FROM temp_erc721_data').fetchall()
            assert temp_erc721_data == [
                ('history_events', '[[7, 2, "TEST1", 0, 1, "f", "0x706A70067BE19BdadBea3600Db0626859Ff25D74", "eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88", "1", "0", "", "11", "16", ""]]'),  # noqa: E501
                ('manually_tracked_balances', '[[3, "eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88", "Test Balance", "5", "A", "A"]]'),  # noqa: E501
            ]

    _use_prepared_db(user_data_dir, 'v46_rotkehlchen.db')
    db_v46 = _init_db_with_target_version(
        target_version=46,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    uniswap_erc721_token = get_or_create_evm_token(
        userdb=db_v46,
        evm_address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        name='Uniswap V3 Positions NFT-V1',
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
    )
    uniswap_erc20_token = get_or_create_evm_token(
        userdb=db_v46,
        evm_address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        name='Uniswap V3 Positions NFT-V1',
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
    )
    erc721_token_with_id = get_or_create_evm_token(
        userdb=db_v46,
        evm_address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        name='Uniswap V3 Positions NFT-V1',
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id='12345',
    )
    basename_token = get_or_create_evm_token(
        userdb=db_v46,
        evm_address=string_to_evm_address('0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a'),
        name='Base name',
        chain_id=ChainID.BASE,
        token_kind=TokenKind.ERC721,
    )
    basename_token_with_id = get_or_create_evm_token(
        userdb=db_v46,
        evm_address=string_to_evm_address('0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a'),
        name='Base name',
        chain_id=ChainID.BASE,
        token_kind=TokenKind.ERC721,
        collectible_id='4242',
    )

    address, tx_hash = make_evm_address(), make_evm_tx_hash()
    with db_v46.user_write() as write_cursor:
        db_v46.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.EXTRA_INTERNAL_TX,
            value=address,
            chain_id=10,
            receiver=address,
            tx_hash=str(tx_hash),
        )
        # Add entries with an old erc721 asset to ensure they are handled correctly during upgrade.
        write_cursor.execute(
            'INSERT INTO history_events(entry_type, event_identifier, sequence_index, '
            'timestamp, location, location_label, asset, amount, usd_value, notes, '
            'type, subtype, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (HistoryBaseEntryType.EVM_EVENT.value, 'TEST1', 0, 1, Location.ETHEREUM.serialize_for_db(), (user_address := '0x706A70067BE19BdadBea3600Db0626859Ff25D74'), uniswap_erc721_token.identifier, 1, 0, '', HistoryEventType.DEPLOY.value, HistoryEventSubType.NFT.value, ''),  # noqa: E501
        )
        write_cursor.execute(  # mark it a custom event to so event reset doesn't affect it.
            "INSERT INTO history_events_mappings(parent_identifier, name, value) VALUES ((SELECT identifier FROM history_events WHERE event_identifier='TEST1'), ?, ?)",  # noqa: E501
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )
        write_cursor.executemany(
            'INSERT INTO evm_accounts_details(account, chain_id, key, value) VALUES(?, ?, ?, ?)',
            [
                (user_address, 1, 'tokens', uniswap_erc721_token.identifier),
                (user_address, 1, 'testkey', 'testdata'),
            ],
        )
        write_cursor.execute(
            'INSERT INTO timed_balances(category, timestamp, currency, amount, usd_value) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
            ('A', 1, uniswap_erc20_token.identifier, 1, 1),
        )
        write_cursor.execute(
            'INSERT INTO manually_tracked_balances(asset, label, amount) VALUES(?, ?, ?)',
            (uniswap_erc721_token.identifier, 'Test Balance', 5),
        )
        write_cursor.executemany(  # add test history events
            'INSERT INTO history_events(entry_type, event_identifier, sequence_index, '
            'timestamp, location, location_label, asset, amount, usd_value, notes, '
            'type, subtype, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                (1, f'{CB_EVENTS_PREFIX}_EVENT', 0, 1, (coinbase_location := Location.COINBASE.serialize_for_db()), '', 'ETH', 1, 0, '', 'receive', 'receive', ''),  # noqa: E501
                (1, f'{ROTKI_EVENT_PREFIX}_EVENT', 0, 1, coinbase_location, '', 'ETH', 1, 0, '', 'receive', 'receive', ''),  # noqa: E501
                (1, 'kraken-id', 0, 1, (kraken_location := Location.KRAKEN.serialize_for_db()), '', 'BTC', 1, 0, '', 'spend', 'spend', ''),  # noqa: E501
                (1, 'gemini-id', 0, 1, (gemini_location := Location.GEMINI.serialize_for_db()), '', 'BTC', 1, 0, '', 'spend', 'spend', ''),  # noqa: E501
                (1, f'{ROTKI_EVENT_PREFIX}_GEM_EVENT', 0, 1, gemini_location, '', 'ETH', 1, 0, '', 'receive', 'receive', ''),  # noqa: E501
                (1, 'bybit-id', 0, 1, (bybit_location := Location.BYBIT.serialize_for_db()), '', 'BTC', 1, 0, '', 'spend', 'spend', ''),  # noqa: E501
                (1, f'{ROTKI_EVENT_PREFIX}_BYBIT_EVENT', 0, 1, bybit_location, '', 'ETH', 1, 0, '', 'receive', 'receive', ''),  # noqa: E501
            ],
        )
        write_cursor.executemany(  # add location cache entries
            'INSERT INTO key_value_cache(name, value) VALUES(?, ?)',
            [
                ('coinbase_main_123_last_query_ts', '1641386280'),
                ('coinbase_test_456_last_query_ts', '1641386281'),
                ('coinbase_main_123_last_query_id', 'abc123'),
                ('coinbase_test_456_last_query_id', 'def456'),
                ('kraken_main_789_last_query_ts', '1641386282'),  # kraken entry - shouldn't be deleted  #noqa: E501
            ],
        )
        write_cursor.executemany(  # add test trades
            'INSERT INTO trades(id, timestamp, location, base_asset, quote_asset, type, amount, rate, link, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',  # noqa: E501
            [
                ('trade_1', 1641386280, kraken_location, 'BTC', 'EUR', 'A', '0.5', '50000', '', 'Kraken trade'),  # noqa: E501
                ('trade_2', 1641386281, coinbase_location, 'ETH', 'USD', 'B', '1.0', '3000', 'cbid77', 'Coinbase trade with link'),  # noqa: E501
                ('trade_3', 1641386282, coinbase_location, 'ETH', 'USD', 'C', '1.5', '3500', '', 'Coinbase trade without link'),  # noqa: E501
                ('trade_4', 1641386282, gemini_location, 'ETH', 'USD', 'C', '1.5', '3500', 'geminitxid333', 'gemini trade with link'),  # noqa: E501
                ('trade_5', 1641386282, gemini_location, 'ETH', 'USD', 'C', '1.5', '3500', '', 'gemini trade without link'),  # noqa: E501
                ('trade_6', 1641386282, bybit_location, 'ETH', 'USD', 'C', '1.5', '3500', 'bybittxid333', 'bybit trade with link'),  # noqa: E501
                ('trade_7', 1641386282, bybit_location, 'ETH', 'USD', 'C', '1.5', '3500', '', 'bybit trade without link'),  # noqa: E501
            ],
        )
        write_cursor.executemany(  # add entries to queried ranges
            'INSERT INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
            [
                ('coinbase_trades_cb1', 1641386200, 1641386300),
                ('coinbase_history_events_cb1', 1641386301, 1641386400),
                ('kraken_history_events_kk', 1641386301, 1641386400),
                ('gemini_trades_cb1', 1641386200, 1641386300),
                ('gemini_history_events_cb1', 1641386301, 1641386400),
                ('bybit_trades_cb1', 1641386200, 1641386300),
                ('bybit_history_events_cb1', 1641386301, 1641386400),
            ],
        )
        # ensure that manual historical price oracle is present.
        assert 'manual' in json.loads(write_cursor.execute("SELECT value FROM settings WHERE name='historical_price_oracles'").fetchone()[0])  # noqa: E501

    with db_v46.conn.read_ctx() as cursor:  # assert block events state before upgrade
        result = cursor.execute("SELECT identifier, entry_type, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, usd_value, notes, type, subtype FROM history_events WHERE event_identifier IN ('BP1_17153311', 'BP1_17153312')").fetchall()  # noqa: E501
        assert result == [
            (1, 4, 'BP1_17153311', 0, 1682911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.1', '100', 'Validator 4242 produced block 17153311 with 0.1 ETH going to 0x8ff1E3bD9b935208521D33F74430Bd5fA4387120 as the block reward', 'staking', 'block production'),  # noqa: E501
            (2, 4, 'BP1_17153311', 1, 1682911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.05', '50', 'Validator 4242 produced block 17153311 with 0.05 ETH going to 0x8ff1E3bD9b935208521D33F74430Bd5fA4387120 as the mev reward', 'staking', 'mev reward'),  # noqa: E501
            (3, 2, 'BP1_17153311', 2, 1682911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.05', '50', 'Receive 0.05 ETH going from 0x2Aeb220005C35D30F3980b33FFE2a91Ce7a4E131 as mev reward for block 17153311', 'staking', 'mev reward'),  # noqa: E501
            (4, 4, 'BP1_17153312', 0, 1683911787000, 'f', '0x6EF6f6436605793b1c551727B26295Cd4E74bC43', 'ETH', '0.2', '200', 'Validator 4242 produced block 17153312 with 0.2 ETH going to 0x6EF6f6436605793b1c551727B26295Cd4E74bC43 as the block reward', 'staking', 'block production'),  # noqa: E501
            (5, 4, 'BP1_17153312', 1, 1683911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.06', '60', 'Validator 4242 produced block 17153312 with 0.06 ETH going to 0x8ff1E3bD9b935208521D33F74430Bd5fA4387120 as the mev reward', 'staking', 'mev reward'),  # noqa: E501
            (6, 2, 'BP1_17153312', 2, 1682311787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.06', '60', 'Receive 0.06 ETH going from 0x2Aeb220005C35D30F3980b33FFE2a91Ce7a4E131 as mev reward for block 17153312', 'staking', 'mev reward'),  # noqa: E501
        ]
        result = cursor.execute('SELECT identifier, validator_index, is_exit_or_blocknumber FROM eth_staking_events_info').fetchall()  # noqa: E501
        assert result == [(1, 4242, 17153311), (2, 4242, 17153311), (4, 4242, 17153312), (5, 4242, 17153312)]  # noqa: E501
        result = cursor.execute('SELECT identifier, tx_hash, counterparty, product, address FROM evm_events_info').fetchall()  # noqa: E501
        assert result == [
            (3, deserialize_evm_tx_hash('0x3891138d3930f46d853183c651de85e57cfc9f776f211916d5b6337556527682'), None, None, '0x2Aeb220005C35D30F3980b33FFE2a91Ce7a4E131'),  # noqa: E501
            (6, deserialize_evm_tx_hash('0xcdf96f6a8082939652fcb23278f42954fa41c2e11ae30c77f5ee3ef8fc3f0da8'), None, None, '0x2Aeb220005C35D30F3980b33FFE2a91Ce7a4E131'),  # noqa: E501
        ]
        assert cursor.execute(
            "SELECT COUNT(*) FROM settings WHERE name='last_data_upload_ts'",
        ).fetchone()[0] == 1
        assert json.loads(cursor.execute(
            "SELECT value FROM settings WHERE name='active_modules'",
        ).fetchone()[0]) == ['aave', 'sushiswap', 'uniswap', 'nfts', 'loopring', 'eth2', 'compound', 'makerdao_vaults', 'liquity', 'yearn_vaults_v2', 'yearn_vaults', 'pickle_finance']  # noqa: E501
        assert set(cursor.execute(
            "SELECT * FROM multisettings WHERE name LIKE 'queried\\_address\\_%' ESCAPE '\\'",
        ).fetchall()) == {
            ('queried_address_aave', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
            ('queried_address_aave', '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'),
            ('queried_address_yearn_vaults', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
            ('queried_address_yearn_vaults', '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'),
            ('queried_address_yearn_vaults_v2', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
            ('queried_address_yearn_vaults_v2', '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'),
            ('queried_address_compound', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
            ('queried_address_compound', '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'),
        }
        # Before tests for the avalanche/binance tokens deletion
        assert cursor.execute('SELECT * FROM manually_tracked_balances').fetchall() == [
            (1, 'TEDDY', 'My Teddy balance', '10', 'A', 'A'),
            (2, 'BUX', 'My BUX balance', '20', 'A', 'A'),
            (3, 'eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88', 'Test Balance', '5', 'A', 'A'),  # noqa: E501
        ]
        assert cursor.execute('SELECT * FROM timed_balances').fetchall() == [
            ('A', 1740603997, 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', '10', '10'),  # noqa: E501
            ('A', 1740603998, 'BUX', '5', '5'),
            ('A', 1740603897, 'eip155:1/erc721:0xFaC7BEA255a6990f749363002136aF6556b31e04', '1', '100'),  # noqa: E501
            ('A', 1740603897, 'eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a', '1', '100'),  # noqa: E501
            ('A', 1740603897, 'eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a/26612040215479394739615825115912800930061094786769410446114278812336794170041', '1', '100'),  # noqa: E501
            ('A', 1, uniswap_erc20_token.identifier, '1', '1'),
        ]
        assert cursor.execute("SELECT * FROM trades WHERE location='A'").fetchall() == [
            ('1', 1740603997, 'A', 'BUX', 'ETH', 'A', '10', '0.1', '0.01', 'BUX', 'A link', 'trade notes'),  # noqa: E501
        ]
        assert cursor.execute(
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value IN ('BUX', 'TEDDY', 'BIDR')",  # noqa: E501
        ).fetchone()[0] == 3
        assert cursor.execute(
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value IN ('eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', 'eip155:43114/erc20:0x094bd7B2D99711A1486FB94d4395801C6d0fdDcC')",  # noqa: E501
        ).fetchone()[0] == 0
        assert cursor.execute(  # this is BIDR's actual evm token. Testing the already exists case for ignore asset  # noqa: E501
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value ='eip155:56/erc20:0x9A2f5556e9A637e8fBcE886d8e3cf8b316a1D8a2'",  # noqa: E501
        ).fetchone()[0] == 1

    with db_v46.conn.read_ctx() as cursor:
        assert db_v46.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.EXTRA_INTERNAL_TX,
            chain_id=10,
            receiver=address,
            tx_hash=str(tx_hash),
        ) == address
        cursor.execute("SELECT COUNT(*) FROM location WHERE location='v'")
        assert cursor.fetchone()[0] == 0

        _check_tokens_existence(user_db_cursor=cursor)

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=47,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db.conn.read_ctx() as cursor:
        assert db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.EXTRA_INTERNAL_TX,
            chain_id=10,
            receiver=address,
            tx_hash=str(tx_hash),
        ) is None
        cursor.execute("SELECT seq FROM location WHERE location='v'")
        assert cursor.fetchone() == (54,)

        _check_tokens_existence(user_db_cursor=cursor, expect_removed=True)

        assert cursor.execute(  # events with the correct prefix for bybit, coinbase & gemini removed  # noqa: E501
            'SELECT COUNT(*) FROM history_events WHERE location IN (?, ?, ?) AND event_identifier LIKE ?',  # noqa: E501
            (bybit_location, coinbase_location, gemini_location, f'{CB_EVENTS_PREFIX}%'),
        ).fetchone()[0] == 0

        assert cursor.execute(  # events imported or different locations preserved
            'SELECT COUNT(*) FROM history_events WHERE event_identifier IN (?, ?, ?, ?)',
            ('kraken-id', f'{ROTKI_EVENT_PREFIX}_EVENT', f'{ROTKI_EVENT_PREFIX}_GEM_EVENT', f'{ROTKI_EVENT_PREFIX}_BYBIT_EVENT'),  # noqa: E501
        ).fetchone()[0] == 4

        assert cursor.execute(  # all coinbase caches are deleted
            'SELECT COUNT(*) FROM key_value_cache WHERE name LIKE ? OR name LIKE ?',
            (f'{(coinbase_loc := Location.COINBASE.serialize())}_%_last_query_ts', f'{coinbase_loc}_%_last_query_id'),  # noqa: E501
        ).fetchone()[0] == 0
        assert cursor.execute(  # check that the kraken cache was not affected
            'SELECT COUNT(*) FROM key_value_cache WHERE name LIKE ? OR name LIKE ?',
            (f'{(kraken_loc := Location.KRAKEN.serialize())}_%_last_query_ts', f'{kraken_loc}_%_last_query_id'),  # noqa: E501
        ).fetchone()[0] == 1
        assert cursor.execute(  # ensure trades with bybit or Coinbase or Gemini location and a link are deleted  # noqa: E501
            'SELECT COUNT(*) FROM trades WHERE location IN (?, ?, ?) AND link != ?',
            (bybit_location, coinbase_location, gemini_location, ''),
        ).fetchone()[0] == 0
        assert cursor.execute('SELECT id FROM trades').fetchall() == [  # ensure trades with empty link is preserved  # noqa: E501
            ('1',), ('trade_1',), ('trade_3',), ('trade_5',), ('trade_7',),
        ]
        assert cursor.execute(  # verify query ranges for bybit, coinbase and gemini are deleted
            'SELECT COUNT(*) FROM used_query_ranges WHERE name IN (?, ?, ?)',
            (f'{coinbase_loc}_%', f'{Location.GEMINI.serialize()}_%', f'{Location.BYBIT.serialize()}_%'),  # noqa: E501
        ).fetchone()[0] == 0

        # assert block events state after upgrade
        result = cursor.execute("SELECT identifier, entry_type, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype FROM history_events WHERE event_identifier IN ('BP1_17153311', 'BP1_17153312')").fetchall()  # noqa: E501
        assert result == [
            (1, 4, 'BP1_17153311', 0, 1682911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.1', 'Validator 4242 produced block 17153311 with 0.1 ETH going to 0x8ff1E3bD9b935208521D33F74430Bd5fA4387120 as the block reward', 'staking', 'block production'),  # noqa: E501
            (2, 4, 'BP1_17153311', 1, 1682911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.05', 'Validator 4242 produced block 17153311. Relayer reported 0.05 ETH as the MEV reward going to 0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'informational', 'mev reward'),  # noqa: E501
            (4, 4, 'BP1_17153312', 0, 1683911787000, 'f', '0x6EF6f6436605793b1c551727B26295Cd4E74bC43', 'ETH', '0.2', 'Validator 4242 produced block 17153312 with 0.2 ETH going to 0x6EF6f6436605793b1c551727B26295Cd4E74bC43 as the block reward', 'informational', 'block production'),  # noqa: E501
            (5, 4, 'BP1_17153312', 1, 1683911787000, 'f', '0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'ETH', '0.06', 'Validator 4242 produced block 17153312. Relayer reported 0.06 ETH as the MEV reward going to 0x8ff1E3bD9b935208521D33F74430Bd5fA4387120', 'informational', 'mev reward'),  # noqa: E501
        ]
        result = cursor.execute('SELECT identifier, validator_index, is_exit_or_blocknumber FROM eth_staking_events_info').fetchall()  # noqa: E501
        assert result == [(1, 4242, 17153311), (2, 4242, 17153311), (4, 4242, 17153312), (5, 4242, 17153312)]  # noqa: E501
        result = cursor.execute('SELECT identifier, tx_hash, counterparty, product, address FROM evm_events_info').fetchall()  # noqa: E501
        assert result == []

        assert cursor.execute(  # verify that all old counterparty specific rules for these types are removed  # noqa: E501
            'SELECT counterparty FROM accounting_rules WHERE (type=? AND subtype=?) OR (type=? AND subtype=?)',  # noqa: E501
            ('deposit', 'deposit asset', 'withdrawal', 'remove asset'),
        ).fetchall() == [('NONE',), ('NONE',)]  # Keep the rules with null counterparty

        # ensure that manual historical price oracle is removed from settings.
        assert 'manual' not in json.loads(cursor.execute("SELECT value FROM settings WHERE name='historical_price_oracles'").fetchone()[0])  # noqa: E501
        assert cursor.execute(
            "SELECT COUNT(*) FROM settings WHERE name='last_data_upload_ts'",
        ).fetchone()[0] == 0
        assert json.loads(cursor.execute(
            "SELECT value FROM settings WHERE name='active_modules'",
        ).fetchone()[0]) == ['sushiswap', 'uniswap', 'nfts', 'loopring', 'eth2', 'makerdao_vaults', 'liquity', 'pickle_finance']  # noqa: E501
        assert cursor.execute(
            "SELECT * FROM multisettings WHERE name LIKE 'queried\\_address\\_%' ESCAPE '\\'",
        ).fetchall() == []
        # After tests for the avalanche/binance tokens deletion
        assert cursor.execute('SELECT * FROM manually_tracked_balances').fetchall() == [
            (1, 'eip155:43114/erc20:0x094bd7B2D99711A1486FB94d4395801C6d0fdDcC', 'My Teddy balance', '10', 'A', 'A'),  # noqa: E501
            (2, 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', 'My BUX balance', '20', 'A', 'A'),  # noqa: E501
        ]
        assert cursor.execute('SELECT * FROM timed_balances').fetchall() == [
            ('A', 1740603997, 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', '10', '10'),  # noqa: E501
            ('A', 1740603998, 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', '5', '5'),  # noqa: E501
            ('A', 1740603897, 'eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a/26612040215479394739615825115912800930061094786769410446114278812336794170041', '1', '100'),  # noqa: E501
        ]
        assert cursor.execute("SELECT * FROM trades WHERE location='A'").fetchall() == [
            ('1', 1740603997, 'A', 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', 'ETH', 'A', '10', '0.1', '0.01', 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', 'A link', 'trade notes'),  # noqa: E501
        ]
        assert cursor.execute(
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value IN ('BUX', 'TEDDY', 'BIDR')",  # noqa: E501
        ).fetchone()[0] == 0
        assert cursor.execute(
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value IN ('eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45', 'eip155:43114/erc20:0x094bd7B2D99711A1486FB94d4395801C6d0fdDcC', 'eip155:56/erc20:0x9A2f5556e9A637e8fBcE886d8e3cf8b316a1D8a2')",  # noqa: E501
        ).fetchone()[0] == 3

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_47_to_48(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 47 to version 48"""
    _use_prepared_db(user_data_dir, 'v47_rotkehlchen.db')
    db_v47 = _init_db_with_target_version(
        target_version=47,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db_v47.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT entry_type, event_identifier, sequence_index, '
            'timestamp, location, location_label, asset, amount, notes, '
            'type, subtype, extra_data FROM history_events WHERE type IN (?, ?)',
            (HistoryEventType.TRADE.serialize(), HistoryEventType.ADJUSTMENT.serialize()),
        ).fetchall() == [
            # An adjustment event that is not associated with a trade - should remain unmodified.
            (unmodified_adjustment := (1, 'XTJ7Rry-mZ9Lxc5xuhAbnhbBtu5Gpy', 0, 1731508592028, 'B', 'Kraken 1', 'eip155:1/erc20:0x643C4E15d7d62Ad0aBeC4a9BD4b001aA3Ef52d66', '283.79600', None, 'adjustment', 'receive', None)),  # noqa: E501
            # History events associated with a trade. The label should be preserved.
            (1, 'C5DAUH-13NE4-TWYVBD', 0, 1731435124057, 'B', (kraken_normal_trade_label := 'Kraken 2'), 'USD', '25.0000', None, 'trade', 'spend', None),  # noqa: E501
            (1, 'C5DAUH-13NE4-TWYVBD', 1, 1731435124057, 'B', kraken_normal_trade_label, 'BTC', '0.0002857200', None, 'trade', 'receive', None),  # noqa: E501
            (1, 'C5DAUH-13NE4-TWYVBD', 2, 1731435124057, 'B', kraken_normal_trade_label, 'USD', '0.1000', None, 'trade', 'fee', None),  # noqa: E501
            # Adjustment events associated with a trade. The label and amounts should be preserved (adjustment trade rates were incorrect).  # noqa: E501
            (1, 'NZ5OB33-MW63Z-EN3SV1', 0, 1575784819255, 'B', (kraken_adjustment_label := 'Kraken 3'), 'BSV', (adjustment_spend := '0.00000678'), None, 'adjustment', 'spend', None),  # noqa: E501
            (1, 'NZ4HZV6-EN3S2-DFZ1X4', 0, 1575784819256, 'B', kraken_adjustment_label, 'BTC', (adjustment_receive := '0.0000000831'), None, 'adjustment', 'receive', None),  # noqa: E501
        ]
        assert cursor.execute(
            'SELECT timestamp, location, base_asset, quote_asset, type, '
            'amount, rate, fee, fee_currency, link, notes FROM trades',
        ).fetchall() == [
            (1731435124, 'B', 'BTC', 'USD', 'A', '0.0002857200', '87498.2500349993000139997200055998880022399552008959820803583928321433571328573', '0.1000', 'USD', 'C5DAUH-13NE4-TWYVBD1731435124', None),  # noqa: E501
            (1739820693, 'S', 'ETH', 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7', 'B', '0.00800000', '2709.53000000', '0.00004800', 'ETH', '17572768', None),  # noqa: E501
            (1703082904, 'G', 'XRP', 'USD', 'A', '43.764904', '0.685480767877384124960036471232748505514829873727130762128485418361708276567909', None, None, '8ad05838-6b0e-50a8-8665-c784fd4d85fd', None),  # noqa: E501
            (1575784819, 'B', 'BTC', 'BSV', 'A', '0.0000000831', '0.012256637168141592', None, None, 'adjustmentNZ5OB33-MW63Z-EN3SV1NZ4HZV6-EN3S2-DFZ1X4', None),  # noqa: E501
            (1749566127, 'A', 'ETH', 'USD', 'A', '10', '2732.36750009618', '12', 'USD', '', None),
            (1749566127, 'A', 'ETH', 'USD', 'A', '5', '2732.36750009618', None, None, '', ''),
            (1749566154, 'A', 'BTC', 'USD', 'A', '1', '108659.316521703', None, None, '', ''),
            (1749566193, 'A', 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'USD', 'A', '30', '308.847203959014', None, None, 'testig', ''),  # noqa: E501
            (1749566160, 'A', 'BTC', 'USD', 'A', '2', '108659.316521703', None, None, '', ''),
            (1749566220, 'C', 'ETH', 'USD', 'B', '5', '3820.451237', None, None, None, 'Test entry with NULL link'),  # noqa: E501
        ]
        assert table_exists(cursor, 'trades')
        assert table_exists(cursor, 'trade_type')
        assert cursor.execute('SELECT identifier, location FROM user_notes WHERE identifier BETWEEN 1001 AND 1004').fetchall() == [  # noqa: E501
            (1001, 'HISTORY_TRADES'),
            (1002, 'HISTORY_TRANSACTIONS'),
            (1003, 'HISTORY_DEPOSITS_WITHDRAWALS'),
            (1004, 'DASHBOARD'),
        ]
        assert cursor.execute('SELECT identifier, notes FROM history_events WHERE entry_type=6').fetchall() == [  # noqa: E501
            (10, 'Withdraw 100 from A'),
            (11, 'Custom note for asset move'),
        ]
        assert cursor.execute('SELECT * from history_events_mappings').fetchall() == [(11, 'state', 1)]  # noqa: E501
        assert cursor.execute('SELECT * from ignored_actions').fetchall() == [
            ('A', 'C5DAUH-13NE4-TWYVBD'),
            ('A', 'NZ5OB33-MW63Z-EN3SV1'),
            ('C', '17572768'),
            ('A', '8ad05838-6b0e-50a8-8665-c784fd4d85fd'),
            ('B', 'some-deposit-id'),
            ('C', 'some-withdrawal-id'),
        ]
        assert not column_exists(cursor, 'calendar_reminders', 'acknowledged')
        assert cursor.execute('SELECT * from calendar_reminders').fetchall() == [
            (1, 1, 3600),
            (2, 1, 900),
            (3, 2, 86400),
        ]
        assert not column_exists(cursor, 'eth2_validators', 'validator_type')
        assert cursor.execute('SELECT withdrawal_address from eth2_validators').fetchall() == [
            ('0xabcd1234abcd1234abcd1234abcd1234abcd1234',),
            (None,),
            ('0xefef1234abcd1234abcd1234abcd1234abcd5678',),
            (None,),
        ]
        assert cursor.execute('SELECT * from used_query_ranges WHERE name LIKE ? ESCAPE ?', ('%\\_trades\\_%', '\\')).fetchall() == [  # noqa: E501
            ('kraken_trades_kraken', 1577836800, 1609459200),
            ('binance_trades_binance', 1609459200, 1640995200),
            ('coinbase_trades_coinbase', 1640995200, 1672531200),
            ('gemini_trades_gemini', 1672531200, 1704067200),
        ]
        assert table_exists(cursor, 'action_type')
        assert cursor.execute('SELECT COUNT(*) FROM rpc_nodes').fetchone()[0] == 51
        assert {row[0] for row in cursor.execute('SELECT name FROM rpc_nodes WHERE endpoint=""')} == {  # noqa: E501
            'arbitrum one etherscan',
            'base etherscan',
            'bsc etherscan',
            'etherscan',
            'gnosis etherscan',
            'optimism etherscan',
            'polygon pos etherscan',
            'scroll etherscan',
        }
        assert cursor.execute(
            'SELECT value FROM settings where name=?',
            ('use_unified_etherscan_api',),
        ).fetchone()[0] == 'True'
        assert not table_exists(cursor, 'evm_transactions_authorizations')
        assert not table_exists(cursor, 'eth_validators_data_cache')
        assert cursor.execute('SELECT * from evm_internal_transactions').fetchall() == [
            (579, 42, '0x9eE457023bB3De16D51A003a247BaEaD7fce313D', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '15'),  # noqa: E501
        ]
        assert not column_exists(cursor, 'history_events', 'ignored')
        assert A_LTC.identifier in db_v47.get_ignored_asset_ids(cursor)
        ignored_asset_event_count = cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE asset=?',
            (A_LTC.identifier,),
        ).fetchone()[0]

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=48,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT entry_type, event_identifier, sequence_index, '
            'timestamp, location, location_label, asset, amount, notes, '
            'type, subtype, extra_data FROM history_events WHERE type IN (?, ?)',
            (HistoryEventType.TRADE.serialize(), HistoryEventType.ADJUSTMENT.serialize()),
        ).fetchall() == [
            unmodified_adjustment,
            # SwapEvents from the normal trades. The Kraken trade should have its location label set.  # noqa: E501
            (7, '568667233c36a4975559fc4d105d8dedad6de494e46367740e1b1fc7ec41e1d7', 0, 1731435124000, 'B', kraken_normal_trade_label, 'USD', '25.0000000000000000000000000000000000000000000000000000000000000000000000000000', None, 'trade', 'spend', None),  # noqa: E501
            (7, '568667233c36a4975559fc4d105d8dedad6de494e46367740e1b1fc7ec41e1d7', 1, 1731435124000, 'B', kraken_normal_trade_label, 'BTC', '0.0002857200', None, 'trade', 'receive', None),  # noqa: E501
            (7, '568667233c36a4975559fc4d105d8dedad6de494e46367740e1b1fc7ec41e1d7', 2, 1731435124000, 'B', kraken_normal_trade_label, 'USD', '0.1000', None, 'trade', 'fee', None),  # noqa: E501
            (7, '3e13e1b5594292787b80dd12e80fec0035ff18892dc219790aaee697a55c3fc9', 0, 1739820693000, 'S', None, 'ETH', '0.00800000', None, 'trade', 'spend', None),  # noqa: E501
            (7, '3e13e1b5594292787b80dd12e80fec0035ff18892dc219790aaee697a55c3fc9', 1, 1739820693000, 'S', None, 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7', '21.6762400000000000', None, 'trade', 'receive', None),  # noqa: E501
            (7, '3e13e1b5594292787b80dd12e80fec0035ff18892dc219790aaee697a55c3fc9', 2, 1739820693000, 'S', None, 'ETH', '0.00004800', None, 'trade', 'fee', None),  # noqa: E501
            (7, 'd0db33d8ad340e99e717ab103fb4e6009c0797c0ffa94ff30a8d12e54a7b9767', 0, 1703082904000, 'G', None, 'USD', '30.0000000000000000000000000000000000000000000000000000000000000000000000000000', None, 'trade', 'spend', None),  # noqa: E501
            (7, 'd0db33d8ad340e99e717ab103fb4e6009c0797c0ffa94ff30a8d12e54a7b9767', 1, 1703082904000, 'G', None, 'XRP', '43.764904', None, 'trade', 'receive', None),  # noqa: E501
            # Two SwapEvents from the adjustment trade. Amounts should be the same as the original adjustment history events.  # noqa: E501
            (7, '577f4275b57a9c02b166c10f3ffa3e6c616a3d9d1b68cc1d5b5781cbe8cd8992', 0, 1575784819000, 'B', kraken_adjustment_label, 'BSV', adjustment_spend, None, 'trade', 'spend', None),  # noqa: E501
            (7, '577f4275b57a9c02b166c10f3ffa3e6c616a3d9d1b68cc1d5b5781cbe8cd8992', 1, 1575784819000, 'B', kraken_adjustment_label, 'BTC', adjustment_receive, None, 'trade', 'receive', None),  # noqa: E501
            # regression test: trades at same timestamp with different amounts should generate unique event identifiers even without link field  # noqa: E501
            # identical swap #1
            (7, '52ffa18967da0d9a29c0cb4c90999f00b578b4f509b674093e881bfd228ae043', 0, 1749566127000, 'A', None, 'USD', '27323.67500096180', None, 'trade', 'spend', None),  # noqa: E501
            (7, '52ffa18967da0d9a29c0cb4c90999f00b578b4f509b674093e881bfd228ae043', 1, 1749566127000, 'A', None, 'ETH', '10', None, 'trade', 'receive', None),  # noqa: E501
            (7, '52ffa18967da0d9a29c0cb4c90999f00b578b4f509b674093e881bfd228ae043', 2, 1749566127000, 'A', None, 'USD', '12', None, 'trade', 'fee', None),  # noqa: E501
            # identical swap #2
            (7, '58848cc2b8c6f3085a228f4f85777826e81879f43c3e8a6838ed67c5b54a5c45', 0, 1749566127000, 'A', None, 'USD', '13661.83750048090', '', 'trade', 'spend', None),  # noqa: E501
            (7, '58848cc2b8c6f3085a228f4f85777826e81879f43c3e8a6838ed67c5b54a5c45', 1, 1749566127000, 'A', None, 'ETH', '5', None, 'trade', 'receive', None),  # noqa: E501
            # regular swap.
            (7, 'effef56a55330e3f4bf893757ea7c71d06078303ae09bcb93950a33a09f4aaac', 0, 1749566154000, 'A', None, 'USD', '108659.316521703', '', 'trade', 'spend', None),  # noqa: E501
            (7, 'effef56a55330e3f4bf893757ea7c71d06078303ae09bcb93950a33a09f4aaac', 1, 1749566154000, 'A', None, 'BTC', '1', None, 'trade', 'receive', None),  # noqa: E501
            # regular swap.
            (7, 'c43d6b367aa214ac327ccafff42b88717167b78ff8a989af8433f6ac96b2235b', 0, 1749566193000, 'A', None, 'USD', '9265.416118770420', '', 'trade', 'spend', None),  # noqa: E501
            (7, 'c43d6b367aa214ac327ccafff42b88717167b78ff8a989af8433f6ac96b2235b', 1, 1749566193000, 'A', None, 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', '30', None, 'trade', 'receive', None),  # noqa: E501
            # regular swap.
            (7, '858c767c41df3e1a8d4a29bb9e9a8303f0e06efde643bb677f493ea4f1aa4f95', 0, 1749566160000, 'A', None, 'USD', '217318.633043406', '', 'trade', 'spend', None),  # noqa: E501
            (7, '858c767c41df3e1a8d4a29bb9e9a8303f0e06efde643bb677f493ea4f1aa4f95', 1, 1749566160000, 'A', None, 'BTC', '2', None, 'trade', 'receive', None),  # noqa: E501
            # regular swap.
            (7, '864f2ec06d31754c3e6dd9b6203284fe57723fa90dfcf71f8b5150c82bbdf9e2', 0, 1749566220000, 'C', None, 'ETH', '5', 'Test entry with NULL link', 'trade', 'spend', None),  # noqa: E501
            (7, '864f2ec06d31754c3e6dd9b6203284fe57723fa90dfcf71f8b5150c82bbdf9e2', 1, 1749566220000, 'C', None, 'USD', '19102.256185', None, 'trade', 'receive', None),  # noqa: E501
        ]
        assert not table_exists(cursor, 'trades')
        assert not table_exists(cursor, 'trade_type')

        assert cursor.execute('SELECT identifier, location FROM user_notes WHERE identifier BETWEEN 1001 AND 1004').fetchall() == [  # noqa: E501
            (1001, 'HISTORY'),
            (1002, 'HISTORY'),
            (1003, 'HISTORY'),
            (1004, 'DASHBOARD'),
        ]
        assert cursor.execute('SELECT identifier, notes FROM history_events WHERE entry_type=6').fetchall() == [  # noqa: E501
            (10, None),
            (11, 'Custom note for asset move'),
        ]
        assert cursor.execute('SELECT * from history_events_mappings').fetchall() == [(11, 'state', 1)]  # noqa: E501
        assert cursor.execute('SELECT * from ignored_actions').fetchall() == [
            ('C5DAUH-13NE4-TWYVBD',),
            ('NZ5OB33-MW63Z-EN3SV1',),
            ('17572768',),
            ('8ad05838-6b0e-50a8-8665-c784fd4d85fd',),
            ('some-deposit-id',),
            ('some-withdrawal-id',),
        ]
        assert column_exists(cursor, 'calendar_reminders', 'acknowledged')
        assert cursor.execute('SELECT * from calendar_reminders').fetchall() == [
            (1, 1, 3600, 0),
            (2, 1, 900, 0),
            (3, 2, 86400, 0),
        ]
        assert column_exists(cursor, 'eth2_validators', 'validator_type')
        assert cursor.execute('SELECT withdrawal_address, validator_type from eth2_validators').fetchall() == [  # noqa: E501
            ('0xabcd1234abcd1234abcd1234abcd1234abcd1234', 1),
            (None, 0),
            ('0xefef1234abcd1234abcd1234abcd1234abcd5678', 1),
            (None, 0),
        ]
        assert cursor.execute('SELECT COUNT(*) from used_query_ranges WHERE name LIKE ? ESCAPE ?', ('%\\_trades\\_%', '\\')).fetchone()[0] == 0  # noqa: E501
        assert not table_exists(cursor, 'action_type')
        assert cursor.execute('SELECT COUNT(*) FROM rpc_nodes').fetchone()[0] == 43
        assert cursor.execute('SELECT COUNT(*) FROM rpc_nodes WHERE endpoint=""').fetchone()[0] == 0  # noqa: E501
        assert cursor.execute(
            'SELECT value FROM settings where name=?',
            ('use_unified_etherscan_api',),
        ).fetchall() == []
        assert table_exists(cursor, 'evm_transactions_authorizations')
        assert table_exists(cursor, 'eth_validators_data_cache')
        assert cursor.execute('SELECT * from evm_internal_transactions').fetchall() == [
            (579, 42, '0x9eE457023bB3De16D51A003a247BaEaD7fce313D', '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', '15', '0', '0'),  # noqa: E501
        ]
        assert column_exists(cursor, 'history_events', 'ignored')
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE asset=?',
            (A_LTC.identifier,),
        ).fetchone()[0] == ignored_asset_event_count
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE ignored=1',
        ).fetchone()[0] == ignored_asset_event_count

    db.logout()


def test_latest_upgrade_correctness(user_data_dir):
    """
    This is a test that we can only do for the last upgrade.
    It tests that we know and have included addition statements for all
    of the new database tables introduced and also checks for the correctness of the schema.

    Each time a new database upgrade is added this will need to be modified as
    this is just to reminds us not to forget to add create table statements.
    """
    msg_aggregator = MessagesAggregator()
    base_database = f'v{ROTKEHLCHEN_DB_VERSION - 1}_rotkehlchen.db'
    _use_prepared_db(user_data_dir, base_database)
    last_db = _init_db_with_target_version(
        target_version=ROTKEHLCHEN_DB_VERSION - 1,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = last_db.conn.cursor()
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_before = {x[0] for x in result}
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views_before = {x[0] for x in result}

    last_db.logout()

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=ROTKEHLCHEN_DB_VERSION,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    sanity_check_impl(  # do sanity check on the db schema
        cursor=cursor,
        db_name=db.conn.connection_type.name.lower(),
        minimized_schema=db.conn.minimized_schema,
        minimized_indexes=db.conn.minimized_indexes,
    )
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_after_upgrade = {x[0] for x in result}
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views_after_upgrade = {x[0] for x in result}
    # also add latest tables (this will indicate if DB upgrade missed something
    with db.conn.write_ctx() as write_cursor:
        write_cursor.executescript(DB_SCRIPT_CREATE_TABLES)
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_after_creation = {x[0] for x in result}
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views_after_creation = {x[0] for x in result}

    assert cursor.execute(
        "SELECT value FROM settings WHERE name='version'",
    ).fetchone()[0] == str(ROTKEHLCHEN_DB_VERSION)
    removed_tables = set()
    removed_views = set()
    missing_tables = tables_before - tables_after_upgrade
    missing_views = views_before - views_after_upgrade
    assert missing_tables == removed_tables
    assert missing_views == removed_views
    assert tables_after_creation - tables_after_upgrade == set()
    assert views_after_creation - views_after_upgrade == set()
    new_tables = tables_after_upgrade - tables_before
    assert new_tables == {'lido_csm_node_operators', 'lido_csm_node_operator_metrics'}
    new_views = views_after_upgrade - views_before
    assert new_views == set()
    db.logout()


def test_steps_counted_properly_in_upgrades(user_data_dir):
    """
    Tests database upgrade progress counting behaviour. Makes sure that the number of times
    `new_step()` function is called matches the expected number of total steps.
    """
    msessages_aggregator = MessagesAggregator()
    base_database = f'v{MIN_SUPPORTED_USER_DB_VERSION}_rotkehlchen.db'
    _use_prepared_db(user_data_dir, base_database)
    last_db = _init_db_with_target_version(
        target_version=MIN_SUPPORTED_USER_DB_VERSION,
        user_data_dir=user_data_dir,
        msg_aggregator=msessages_aggregator,
        resume_from_backup=False,
    )
    progress_handler = DBUpgradeProgressHandler(
        messages_aggregator=msessages_aggregator,
        target_version=ROTKEHLCHEN_DB_VERSION,
    )
    for upgrade in UPGRADES_LIST:
        progress_handler.new_round(version=upgrade.from_version + 1)
        kwargs = upgrade.kwargs if upgrade.kwargs is not None else {}
        upgrade.function(db=last_db, progress_handler=progress_handler, **kwargs)
        # Make sure that there were some steps taken
        assert progress_handler.current_round_total_steps > 0
        # And that the number of total steps taken matches expected total steps
        assert progress_handler.current_round_current_step == progress_handler.current_round_total_steps  # noqa: E501
        # Check that the db version in progress handler is correct
        assert progress_handler.current_version == upgrade.from_version + 1
        assert progress_handler.start_version == MIN_SUPPORTED_USER_DB_VERSION + 1
    last_db.logout()


def test_db_newer_than_software_raises_error(data_dir, username, sql_vm_instructions_cb):
    """
    If the DB version is greater than the current known version in the
    software warn the user to use the latest version of the software
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    # Manually set a bigger version than the current known one
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('version', str(ROTKEHLCHEN_DB_VERSION + 1)),
    )
    data.db.conn.commit()

    # now relogin and check that an error is thrown
    data.logout()
    del data
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    with pytest.raises(DBUpgradeError):
        data.unlock(username, '123', create_new=False, resume_from_backup=False)
    DBConnection(  # close the db connection
        path=data_dir / USERDB_NAME,
        connection_type=DBConnectionType.USER,
        sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    ).close()


def test_upgrades_list_is_sane():
    for idx, entry in enumerate(UPGRADES_LIST, start=MIN_SUPPORTED_USER_DB_VERSION):
        msg = (
            f'{idx} upgrade record was expected to have {idx} '
            f'from_version but has {entry.from_version}'
        )
        assert entry.from_version == idx, msg
    assert idx + 1 == ROTKEHLCHEN_DB_VERSION, 'the final version + 1 should be current version'


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_old_versions_raise_error(user_data_dir):  # pylint: disable=unused-argument
    """Test that upgrading from an old version raises the expected warning"""
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v9_rotkehlchen.db')
    with pytest.raises(DBUpgradeError) as upgrade_exception:
        _init_db_with_target_version(
            target_version=34,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
            resume_from_backup=False,
        )
    assert 'Your account was last opened by a very old version of rotki' in str(upgrade_exception)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_unfinished_upgrades(user_data_dir):
    msg_aggregator = MessagesAggregator()
    for backup_version in (33, 31):  # try both with correct and wrong backup
        _use_prepared_db(user_data_dir, 'v33_rotkehlchen.db')
        db = _init_db_with_target_version(
            target_version=33,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
            resume_from_backup=False,
        )
        with db.user_write() as write_cursor:
            db.set_setting(  # Pretend that an upgrade was started
                write_cursor=write_cursor,
                name='ongoing_upgrade_from_version',
                value=33,
            )
        db.logout()
        # Without resume_from_backup there is a permission error
        with pytest.raises(RotkehlchenPermissionError) as exc_info:
            _init_db_with_target_version(
                target_version=34,
                user_data_dir=user_data_dir,
                msg_aggregator=msg_aggregator,
                resume_from_backup=False,
            )
        assert 'The encrypted database is in a semi upgraded state' in str(exc_info.value)

        # There are no backups, so it is supposed to raise an error
        with pytest.raises(DBUpgradeError) as exc_info:
            _init_db_with_target_version(
                target_version=34,
                user_data_dir=user_data_dir,
                msg_aggregator=msg_aggregator,
                resume_from_backup=True,
            )
        assert 'Your encrypted database is in a half-upgraded state at v33 and' in str(exc_info.value)  # noqa: E501

        # Add multiple backups
        for write_version in (backup_version, backup_version - 1):
            backup_path = user_data_dir / f'{ts_now()}_rotkehlchen_db_v{write_version}.backup'
            shutil.copy(Path(__file__).parent.parent / 'data' / 'v33_rotkehlchen.db', backup_path)
            backup_connection = DBConnection(
                path=str(backup_path),
                connection_type=DBConnectionType.USER,
                sql_vm_instructions_cb=0,
            )
            with backup_connection.write_ctx() as write_cursor:
                write_cursor.executescript("PRAGMA key='123'")  # unlock
                write_cursor.execute('INSERT INTO settings VALUES(?, ?)', ('is_backup', write_version))  # mark as a backup  # noqa: E501
            backup_connection.close()

            if backup_version == 33:
                db = _init_db_with_target_version(  # Now the backup should be used
                    target_version=34,
                    user_data_dir=user_data_dir,
                    msg_aggregator=msg_aggregator,
                    resume_from_backup=True,
                )
            else:  # backups exist, but not matching the DB
                with pytest.raises(DBUpgradeError) as exc_info:
                    _init_db_with_target_version(
                        target_version=34,
                        user_data_dir=user_data_dir,
                        msg_aggregator=msg_aggregator,
                        resume_from_backup=True,
                    )
                assert 'Your encrypted database is in a half-upgraded state at v33 and' in str(exc_info.value)  # noqa: E501
                break  # and end the test

        else:  # Check that there is no setting left
            with db.conn.read_ctx() as cursor:
                assert db.get_setting(cursor, 'ongoing_upgrade_from_version') is None
                # Check that the backup was used
                assert cursor.execute("SELECT value FROM settings WHERE name='is_backup'").fetchone()[0] == '33'  # noqa: E501

            for f in os.listdir(user_data_dir):
                if f.endswith('backup'):
                    with suppress(PermissionError):  # in windows this can happen
                        (Path(user_data_dir) / f).unlink()

            db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_48_to_49(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 48 to version 49"""
    _use_prepared_db(user_data_dir, 'v48_rotkehlchen.db')
    db_v48 = _init_db_with_target_version(
        target_version=48,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )

    # Check the buggy schema before upgrade
    with db_v48.conn.read_ctx() as cursor:
        # Get the schema and verify it has the bug
        schema_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='zksynclite_swaps'",
        ).fetchone()
        assert schema_info is not None
        assert 'TEXT_NOT NULL' in schema_info[0], 'Expected TEXT_NOT NULL bug in schema'

        # Check that data exists - just verify we have some data
        swaps_count = cursor.execute(
            'SELECT COUNT(*) FROM zksynclite_swaps',
        ).fetchone()[0]
        assert swaps_count > 0, 'Expected some swap data'

        # check that old format solana assets exist
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE identifier IN ('$NAP', 'ACS', 'AI16Z', 'BONK', 'TRISIG', 'HODLSOL')").fetchone()[0] == 6  # noqa: E501
        tokens_mapping = {  # define before/after mapping for token identifiers
            '$NAP': 'solana/token:4G86CMxGsMdLETrYnavMFKPhQzKTvDBYGMRAdVtr72nu',
            'ACS': 'solana/token:5MAYDfq5yxtudAhtfyuMBuHZjgAbaS9tbEyEQYAhDS5y',
            'AI16Z': 'solana/token:HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC',
            'HODLSOL': 'solana/token:58UC31xFjDJhv1NnBF73mtxcsxN92SWjhYRzbfmvDREJ',
        }
        expected_timed_balances_before = [
            ('$NAP', '100.5', '15000.0'),
            ('ACS', '5000.0', '5000.0'),
            ('AI16Z', '1000000.0', '50.0'),
        ]
        expected_history_events_before = [
            ('$NAP', '10.0', 'receive'),
            ('ACS', '1000.0', 'receive'),
            ('HODLSOL', '500.0', 'receive'),
        ]
        expected_margin_positions_before = [
            ('AI16Z', '100.0'),
            ('ACS', '-50.0'),
        ]
        # check old asset references in other tables exist
        assert cursor.execute('SELECT currency, amount, usd_value FROM timed_balances WHERE currency IN ("$NAP", "ACS", "AI16Z")').fetchall() == expected_timed_balances_before  # noqa: E501
        assert cursor.execute('SELECT asset, amount, type FROM history_events WHERE asset IN ("$NAP", "ACS", "HODLSOL")').fetchall() == expected_history_events_before  # noqa: E501
        assert cursor.execute('SELECT pl_currency, profit_loss FROM margin_positions WHERE pl_currency IN ("AI16Z", "ACS")').fetchall() == expected_margin_positions_before  # noqa: E501
        # it should not have any CAIPS format assets before upgrade
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier LIKE "solana:%" ORDER BY identifier').fetchone()[0] == 0  # noqa: E501
        # user notes with empty string for global location
        assert cursor.execute('SELECT * FROM user_notes').fetchall() == [
            (1, 'Note1', 'Test note 1 contents', 'DASHBOARD', 1754674299, 0),
            (2, 'Note2', 'Test note 2 contents', '', 1754674299, 0),
        ]

        assert cursor.execute(
            solana_query := "SELECT COUNT(*) FROM location WHERE location='w' AND seq=55",
        ).fetchone()[0] == 0

    # Logout and upgrade
    db_v48.logout()

    # Now open with target version 49 to trigger upgrade
    db = _init_db_with_target_version(
        target_version=49,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )

    # Check the schema after upgrade
    with db.conn.read_ctx() as cursor:
        # Get the fixed schema
        schema_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='zksynclite_swaps'",
        ).fetchone()
        assert schema_info is not None
        assert 'TEXT_NOT NULL' not in schema_info[0], 'TEXT_NOT NULL bug should be fixed'
        assert 'to_amount TEXT NOT NULL' in schema_info[0], 'Should have correct TEXT NOT NULL syntax'  # noqa: E501

        # Test solana assets migration to CAIPS format
        # verify old format assets are gone
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier IN ("$NAP", "ACS", "AI16Z", "BONK") ORDER BY identifier').fetchone()[0] == 0  # noqa: E501
        # verify duplicates were deleted
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier IN ("TRISIG", "HODLSOL")').fetchone()[0] == 0  # noqa: E501
        # Check that asset references were updated in other tables
        assert cursor.execute('SELECT currency, amount, usd_value FROM timed_balances WHERE currency LIKE "solana%"').fetchall() == [  # noqa: E501
            (tokens_mapping[entry[0]], entry[1], entry[2])
            for entry in expected_timed_balances_before
        ]
        assert cursor.execute('SELECT asset, amount, type FROM history_events WHERE asset LIKE "solana%"').fetchall() == [  # noqa: E501
            (tokens_mapping[entry[0]], entry[1], entry[2])
            for entry in expected_history_events_before
        ]
        assert cursor.execute('SELECT pl_currency, profit_loss FROM margin_positions WHERE pl_currency LIKE "solana%"').fetchall() == [  # noqa: E501
            (tokens_mapping[entry[0]], entry[1])
            for entry in expected_margin_positions_before
        ]
        # global user note location is now None and the other note is unmodified.
        assert cursor.execute('SELECT * FROM user_notes').fetchall() == [
            (1, 'Note1', 'Test note 1 contents', 'DASHBOARD', 1754674299, 0),
            (2, 'Note2', 'Test note 2 contents', 'G', 1754674299, 0),
        ]
        assert cursor.execute(solana_query).fetchone()[0] == 1

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_49_to_50(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 49 to version 50"""
    _use_prepared_db(user_data_dir, 'v49_rotkehlchen.db')
    db_v49 = _init_db_with_target_version(
        target_version=49,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db_v49.conn.read_ctx() as cursor:
        assert table_exists(cursor=cursor, name='evm_events_info')
        assert not table_exists(cursor=cursor, name='chain_events_info')
        assert cursor.execute('SELECT identifier, counterparty, address, product FROM evm_events_info').fetchall() == [  # noqa: E501
            (5, 'uniswap-v2', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', 'staking'),
            (6, 'makerdao_dsr', '0xAaE2F0F2d7C77cF2A7261a75568128F0C6996319', 'loan'),
        ]
        assert cursor.execute(
            "SELECT identifier, event_identifier, location_label FROM history_events WHERE location = 'P'",  # noqa: E501
        ).fetchall() == [
            (1, 'TEST_EVENT_1', None),
            (2, 'TEST_EVENT_2', None),
            (3, 'TEST_EVENT_3', 'Cryptocom 1'),
        ]
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE parent_identifier=? AND name=? AND value=?',  # noqa: E501
            (2, HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        ).fetchone()[0] == 1  # TEST_EVENT_2 is customized.
        assert not table_exists(cursor=cursor, name='accounting_rule_events')
        assert cursor.execute('SELECT type, subtype, counterparty FROM accounting_rules ORDER BY identifier').fetchall() == (rules := [  # noqa: E501
            ('spend', 'return wrapped', 'aave-v1'),
            ('receive', 'reward', 'aave-v1'),
            ('deposit', 'deposit asset', NO_ACCOUNTING_COUNTERPARTY),
        ])

        # Check that SOL-2 exists in the respective tables
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', ((old_solana_id := 'SOL-2'),)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT currency, amount FROM timed_balances WHERE currency = ?', (old_solana_id,)).fetchall() == [  # noqa: E501
            (old_solana_id, '25.5'),
        ]
        assert cursor.execute('SELECT asset, label FROM manually_tracked_balances WHERE asset = ?', (old_solana_id,)).fetchall() == [  # noqa: E501
            (old_solana_id, 'Test SOL-2 Manual Balance'),
        ]
        assert cursor.execute('SELECT location, pl_currency FROM margin_positions WHERE pl_currency = ?', (old_solana_id,)).fetchall() == [  # noqa: E501
            ('A', old_solana_id),
        ]
        assert cursor.execute('SELECT event_identifier, asset FROM history_events WHERE asset = ?', (old_solana_id,)).fetchall() == [  # noqa: E501
            ('test_sol_event', old_solana_id),
        ]
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', ((new_solana_id := 'SOL'),)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT * FROM external_service_credentials WHERE name IN (?, ?)', ('monerium', 'gnosis_pay')).fetchall() == [('gnosis_pay', 'session_token_123', None), ('monerium', 'lefty@berlin.com', 'securepassword')]  # noqa: E501
        gnosispay_data = (1, b'\x01\x89\x0b\\\r\\\tm\\\xa0\xe9i\xc6\xb1\x02\xba\xec%\xc5\x00\x17\xf6l[@N\xf8wV\x13\x99\x88', 1761405955, 'sex shop', 'Berlin', 'DE', 6969, 'EUR', '42.69', 'EUR', '42.69', None, None, None)  # noqa: E501
        assert cursor.execute('SELECT * FROM gnosispay_data').fetchall() == [gnosispay_data]

    db_v49.logout()
    db = _init_db_with_target_version(
        target_version=50,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db.conn.read_ctx() as cursor:
        assert table_exists(cursor=cursor, name='chain_events_info')
        assert not table_exists(cursor=cursor, name='evm_events_info')
        assert cursor.execute('SELECT identifier, counterparty, address FROM chain_events_info').fetchall() == [  # noqa: E501
            (5, 'uniswap-v2', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'),
            (6, 'makerdao_dsr', '0xAaE2F0F2d7C77cF2A7261a75568128F0C6996319'),
        ]
        assert cursor.execute(
            "SELECT identifier, event_identifier, location_label FROM history_events WHERE location = 'P'",  # noqa: E501
        ).fetchall() == [
            (1, 'TEST_EVENT_1', 'Crypto.com App'),
            (2, 'TEST_EVENT_2', None),  # Customized events are not updated since they may not be for the app account.  # noqa: E501
            (3, 'TEST_EVENT_3', 'Cryptocom 1'),
        ]
        assert table_exists(cursor=cursor, name='accounting_rule_events')
        assert cursor.execute('SELECT type, subtype, counterparty FROM accounting_rules ORDER BY identifier').fetchall() == rules  # noqa: E501

        # Check that SOL-2 no longer exists in assets table
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', (old_solana_id,)).fetchone()[0] == 0  # noqa: E501
        # Check that SOL now exists in assets table
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier = ?', (new_solana_id,)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM timed_balances WHERE currency = ?', (old_solana_id,)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT currency, amount FROM timed_balances WHERE currency = ?', (new_solana_id,)).fetchall() == [  # noqa: E501
            (new_solana_id, '25.5'),
        ]
        assert cursor.execute('SELECT COUNT(*) FROM manually_tracked_balances WHERE asset = ?', (old_solana_id,)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT asset, label FROM manually_tracked_balances WHERE asset = ?', (new_solana_id,)).fetchall() == [  # noqa: E501
            (new_solana_id, 'Test SOL-2 Manual Balance'),
        ]
        assert cursor.execute('SELECT COUNT(*) FROM margin_positions WHERE pl_currency = ?', (old_solana_id,)).fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT location, pl_currency FROM margin_positions WHERE pl_currency = ?', (new_solana_id,)).fetchall() == [  # noqa: E501
            ('A', new_solana_id),
        ]
        assert cursor.execute('SELECT event_identifier, asset FROM history_events WHERE asset = ?', (new_solana_id,)).fetchall() == [  # noqa: E501
            ('test_sol_event', new_solana_id),
        ]
        assert cursor.execute('SELECT * FROM external_service_credentials WHERE name IN (?, ?)', ('monerium', 'gnosis_pay')).fetchall() == []  # noqa: E501
        assert cursor.execute('SELECT * FROM gnosispay_data').fetchall() == [gnosispay_data[:-1]]

    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_50_to_51(user_data_dir, messages_aggregator):
    """Test upgrading the DB from version 50 to version 51"""
    _use_prepared_db(user_data_dir, 'v50_rotkehlchen.db')
    db_v50 = _init_db_with_target_version(
        target_version=50,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db_v50.conn.read_ctx() as cursor:
        assert column_exists(cursor=cursor, table_name='history_events', column_name='event_identifier')  # noqa: E501
        assert not column_exists(cursor=cursor, table_name='history_events', column_name='group_identifier')  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM chain_events_info').fetchone()[0] == 1
        assert cursor.execute('SELECT identifier, event_identifier, sequence_index, asset FROM history_events ORDER BY identifier').fetchall() == (result := [  # noqa: E501
            (1, 'TEST_EVENT_1', 0, 'ETH'),
            (2, 'TEST_EVENT_2', 0, 'BTC'),
            (3, 'TEST_EVENT_3', 1, 'USD'),
        ])
        assert not table_exists(cursor=cursor, name='lido_csm_node_operators')
        assert not table_exists(cursor=cursor, name='lido_csm_node_operator_metrics')

    db_v50.logout()
    db = _init_db_with_target_version(
        target_version=51,
        user_data_dir=user_data_dir,
        msg_aggregator=messages_aggregator,
        resume_from_backup=False,
    )
    with db.conn.read_ctx() as cursor:
        assert not column_exists(cursor=cursor, table_name='history_events', column_name='event_identifier')  # noqa: E501
        assert column_exists(cursor=cursor, table_name='history_events', column_name='group_identifier')  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM chain_events_info').fetchone()[0] == 1  # ensure that fk relations are kept  # noqa: E501
        assert cursor.execute('SELECT identifier, group_identifier, sequence_index, asset FROM history_events ORDER BY identifier').fetchall() == result  # noqa: E501
        assert cursor.execute(  # Verify the unique constraint was updated
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='history_events'",
        ).fetchone()[0].find('UNIQUE(group_identifier, sequence_index)') != -1
        assert table_exists(cursor=cursor, name='lido_csm_node_operators')
        assert table_exists(cursor=cursor, name='lido_csm_node_operator_metrics')

    db.logout()
