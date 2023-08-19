import json
import shutil
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants.misc import DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.data_handler import DataHandler
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
from rotkehlchen.db.utils import table_exists
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    mock_db_schema_sanity_check,
    mock_dbhandler_sync_globaldb_assets,
    mock_dbhandler_update_owned_assets,
)
from rotkehlchen.types import Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import HexBytes
from rotkehlchen.utils.misc import ts_now


def make_serialized_event_identifier(location: Location, raw_event_identifier: bytes) -> str:
    """Creates a serialized event identifeir using the logic at the moment of v32_v33 upgrade"""
    if location == Location.KRAKEN or raw_event_identifier.startswith(b'rotki_events'):
        return raw_event_identifier.decode()

    hex_representation = raw_event_identifier.hex()
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
    for _old, _new in zip(old, new):
        assert isinstance(_new[tx_hash_index], bytes)
        assert isinstance(_old[tx_hash_index], str)
        _old = list(_old)
        _new = list(_new)
        if is_history_event is True:
            _new[tx_hash_index] = make_serialized_event_identifier(
                location=Location.deserialize_from_db(_new[4]),
                raw_event_identifier=_new[1],
            )
        else:
            _new[tx_hash_index] = deserialize_evm_tx_hash(_new[tx_hash_index]).hex()  # noqa: E501 pylint: disable=no-member
        assert _old == _new


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
        if target_version <= 25:
            stack.enter_context(mock_dbhandler_update_owned_assets())
            stack.enter_context(mock_dbhandler_sync_globaldb_assets())
        db = DBHandler(
            user_data_dir=user_data_dir,
            password='123',
            msg_aggregator=msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
            resume_from_backup=resume_from_backup,
        )
    return db


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
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "uniswap%";',
    ).fetchone()[0] == 2
    assert cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name LIKE "balancer%";',
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
        'SELECT COUNT(*) FROM pragma_table_info("yearn_vaults_events") '
        'WHERE name="version"',
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
    base_entries_query = 'SELECT * from history_events WHERE event_identifier="KRAKEN-REMOTE-ID3"'
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 4
    assert len([True for event in result if event[-1] is not None]) == 2

    base_entries_query = 'SELECT * from history_events WHERE event_identifier="KRAKEN-REMOTE-ID4"'
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 3

    # check that user_credential_mappings with setting_name=PAIRS are present
    selected_binance_markets_before = cursor.execute('SELECT * from user_credentials_mappings WHERE setting_name="PAIRS"').fetchall()  # noqa: E501
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
    cursor.execute('SELECT COUNT(*) FROM history_events WHERE subtype="staking remove asset" AND type="unstaking"')  # noqa: E501
    assert cursor.fetchone() == (1,)
    cursor.execute('SELECT COUNT(*), timestamp FROM history_events WHERE subtype="staking receive asset" AND type="unstaking"')  # noqa: E501
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

    assert [1, 2, 3] == [x[0] for x in manual_balance_ids]

    # Check that trades with fee missing sets fee_currency to NULL and vice versa
    trades_expected = cursor.execute('SELECT * FROM trades WHERE id != ? AND id != ?', ('foo1', 'foo2')).fetchall()  # noqa: E501
    assert trades_expected == [
        ('1111111', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', '3.4', 'USD', None, None),  # noqa: E501
        ('1111112', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', None, None, None, None),  # noqa: E501
        ('1111113', 1595640208, 'external', 'ETH', 'USD', 'buy', '1.5541', '22.1', None, None, None, None),  # noqa: E501
    ]

    # Check that sequence indeces are unique for the same event identifier
    base_entries_query = 'SELECT * from history_events WHERE event_identifier="KRAKEN-REMOTE-ID3"'
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 5

    base_entries_query = 'SELECT * from history_events WHERE event_identifier="KRAKEN-REMOTE-ID4"'
    result = cursor.execute(base_entries_query).fetchall()
    assert len(result) == 5
    assert len([row[2] for row in result]) == 5
    assert len({row[2] for row in result}) == 5

    ens_names_test_data = ('0xASDF123', 'TEST_ENS_NAME', 1)
    cursor.execute('INSERT INTO ens_mappings(address, ens_name, last_update) VALUES(?, ?, ?)', ens_names_test_data)  # noqa: E501
    data_in_db = cursor.execute('SELECT address, ens_name, last_update FROM ens_mappings').fetchone()  # noqa: E501
    assert data_in_db == ens_names_test_data
    # Check that selected binance markets settings_name changed to the updated one.
    selected_binance_markets_after = cursor.execute('SELECT * from user_credentials_mappings WHERE setting_name="binance_selected_trade_pairs"').fetchall()  # noqa: E501
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
    cursor.execute('SELECT COUNT(*) FROM history_events WHERE subtype="staking remove asset" AND type="unstaking"')  # noqa: E501
    assert cursor.fetchone() == (0,)
    cursor.execute('SELECT COUNT(*) FROM history_events WHERE subtype="staking receive asset" AND type="unstaking"')  # noqa: E501
    assert cursor.fetchone() == (0,)
    cursor.execute('SELECT COUNT(*), timestamp FROM history_events WHERE subtype="remove asset" AND type="staking"')  # noqa: E501
    assert cursor.fetchone() == (1, expected_timestamp // 10)
    cursor.execute('SELECT COUNT(*), timestamp FROM history_events WHERE subtype="remove asset" AND type="staking"')  # noqa: E501
    assert cursor.fetchone() == (1, expected_timestamp // 10)


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
            'INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index, blockchain) '  # noqa: E501
            'VALUES ("1234", "abcd", "d", 3, 6, "BCH");',
        )
    assert 'cannot INSERT into generated column "blockchain"' in str(exc_info)
    xpub_mapping_data = (
        '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r',
        'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk',  # noqa: E501
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
    blockchain_account_label_initial = cursor.execute('SELECT * FROM blockchain_accounts WHERE account="0x45E6CA515E840A4e9E02A3062F99216951825eB2"').fetchone()[2]  # noqa: E501
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
    blockchain_account_label_upgraded = cursor.execute('SELECT * FROM blockchain_accounts WHERE account="0x45E6CA515E840A4e9E02A3062F99216951825eB2"').fetchone()[2]  # noqa: E501
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
        assert HexBytes(result[-1][10]).hex() == '0xb1fcf4aef6af87a061ca03e92c4eb8039efe600d501ba288a8bae90f78c91db5'  # noqa: E501

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
        for table_name, expected_result in zip(upgraded_tables, expected_timestamps):
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
            'SELECT COUNT(*) FROM sqlite_master WHERE type="view" AND name=?', ('combined_trades_view',),  # noqa: E501
        ).fetchone()[0] == 1

        with pytest.raises(sqlcipher.OperationalError) as exc_info:  # pylint: disable=no-member
            cursor.execute('SELECT blockchain FROM web3_nodes;')
        assert "no such column: blockchain'" in str(exc_info)

        # check that ignored assets are present in the previous format.
        old_ignored_assets_ids = cursor.execute('SELECT value FROM multisettings WHERE name="ignored_asset";').fetchall()  # noqa: E501
        assert old_ignored_assets_ids == expected_old_ignored_assets_ids
        cursor.execute('SELECT tokens_list from ethereum_accounts_details WHERE account="0x45E6CA515E840A4e9E02A3062F99216951825eB2"')  # noqa: E501

        tokens = json.loads(cursor.fetchone()[0])
        assert tokens['tokens'] == ['_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e']
        # check that history events contain a transaction with an old style token identifier
        old_tx_assets_ids = cursor.execute('SELECT DISTINCT asset FROM history_events;').fetchall()  # noqa: E501
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
            'SELECT value FROM settings WHERE name="current_price_oracles"',
        ).fetchone()[0]
        assert oracles_before_upgrade == '["cryptocompare", "coingecko", "uniswapv2", "uniswapv3", "saddle"]'  # noqa: E501

        oracles_after_upgrade = cursor.execute(
            'SELECT value FROM settings WHERE name="historical_price_oracles"',
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
    with db_v34.conn.write_ctx() as write_cursor, pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member  # noqa: E501
        try_insert_mapping(write_cursor)

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
        for table_name, expected_result in zip(upgraded_tables, expected_timestamps):
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
            'SELECT COUNT(*) FROM sqlite_master WHERE type="view" AND name=?', ('combined_trades_view',),  # noqa: E501
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
        new_ignored_assets_ids = cursor.execute('SELECT value FROM multisettings WHERE name="ignored_asset";').fetchall()  # noqa: E501
        for new_ignored_assets_id in expected_new_ignored_assets_ids:
            assert new_ignored_assets_id in new_ignored_assets_ids

        fixed_asset_id = 'eip155:1/erc20:0xb3d608c31ACa7a1c7D6DAcec5978E5493181b67A'
        # check that history events contain a transaction with new style token identifier
        new_tx_assets_ids = cursor.execute('SELECT DISTINCT asset FROM history_events;').fetchall()  # noqa: E501
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
        cursor.execute('SELECT value from accounts_details WHERE account="0x45E6CA515E840A4e9E02A3062F99216951825eB2" AND blockchain="eth" AND key="tokens"')  # noqa: E501
        token = cursor.fetchone()[0]
        assert token == 'eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'

        # Check that oracles were upgraded properly
        oracles_after_upgrade = cursor.execute(
            'SELECT value FROM settings WHERE name="current_price_oracles"',
        ).fetchone()[0]
        assert oracles_after_upgrade == '["manualcurrent", "cryptocompare", "coingecko", "defillama", "uniswapv2", "uniswapv3", "saddle"]'  # noqa: E501

        oracles_after_upgrade = cursor.execute(
            'SELECT value FROM settings WHERE name="historical_price_oracles"',
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
    result = cursor.execute('SELECT value FROM settings WHERE name="active_modules" ;')
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
            assert entry[3] in ('1669718731', '1669715131', '1669711531', '1669698971')
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
    tx_address_mappings_result = cursor.execute('SELECT * from ethtx_address_mappings').fetchall()  # noqa: E501
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
    result = cursor.execute('SELECT sql from sqlite_master WHERE type="table" AND name="nfts"')
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
    cursor.execute('SELECT extra_data FROM history_events WHERE counterparty="liquity"')
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
    result = cursor.execute('SELECT value FROM settings WHERE name="active_modules" ;')
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
            if i in (0, 1):
                assert entry[i] == tx_address_mappings_result[idx][i]
            elif i == 2:
                assert entry[i] == 1
            else:
                assert entry[i] == tx_address_mappings_result[idx][i - 1]
    new_tx_mappings_result = cursor.execute('SELECT * from evm_tx_mappings').fetchall()  # noqa: E501
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
    result = cursor.execute('SELECT sql from sqlite_master WHERE type="table" AND name="nfts"')
    assert result.fetchone()[0] == (
        'CREATE TABLE nfts (\n'
        '            identifier TEXT NOT NULL PRIMARY KEY,\n'
        '            name TEXT,\n'
        '            last_price TEXT,\n'
        '            last_price_asset TEXT,\n'
        '            manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),\n'
        '            owner_address TEXT,\n'
        '            blockchain TEXT GENERATED ALWAYS AS ("ETH") VIRTUAL,\n'
        '            is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),\n'
        '            image_url TEXT,\n'
        '            collection_name TEXT,\n'
        '            FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,\n'  # noqa: E501
        '            FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n'
        '            FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n'  # noqa: E501
        '        )'
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
    cursor.execute('INSERT INTO address_book(address, blockchain, name) VALUES ("0xc37b40ABdB939635068d3c5f13E7faF686F03B65", NULL, "yabir everywhere")')  # noqa: E501

    # test that address book entries were kept
    cursor.execute('SELECT * FROM address_book')
    assert cursor.fetchall() == [
        ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'ETH', 'yabir secret account'),
        ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'ETH', 'lefteris GTC'),
        ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', None, 'yabir everywhere'),
    ]
    cursor.execute('SELECT extra_data FROM history_events WHERE counterparty="liquity"')
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
    cursor.execute('SELECT COUNT(*) FROM history_events WHERE location = "J";')
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
        'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name=?', ('eth2_deposits',),
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
        'SELECT value FROM settings WHERE name="non_syncing_exchanges"',
    ).fetchone()[0] == '[{"name": "Kucoin 1", "location": "kucoin"}, {"name": "FTX 1", "location": "ftx"}]'  # noqa: E501
    assert cursor.execute(
        'SELECT value FROM settings WHERE name="ssf_0graph_multiplier"',
    ).fetchone()[0] == '42'
    assert cursor.execute(
        'SELECT value FROM settings WHERE name="ssf_graph_multiplier"',
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

    new_kraken_events = set(cursor.execute('SELECT * FROM history_events WHERE location="B";'))
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
        'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name=?', ('eth2_deposits',),
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
        'SELECT value FROM settings WHERE name="non_syncing_exchanges"',
    ).fetchone()[0] == '[{"name": "Kucoin 1", "location": "kucoin"}]'
    assert cursor.execute(  # Check the 0graph multiplier setting got updated properly
        'SELECT value FROM settings WHERE name="ssf_0graph_multiplier"',
    ).fetchone() is None
    assert cursor.execute(
        'SELECT value FROM settings WHERE name="ssf_graph_multiplier"',
    ).fetchone()[0] == '42'


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
    assert cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="amm_events";').fetchone()[0] == 1  # noqa: E501
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
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE "uniswap_events_%"').fetchone() == (1,)  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE "sushiswap_events_%"').fetchone() == (1,)  # noqa: E501

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
        (id, *node)
        for id, node in enumerate(DEFAULT_POLYGON_NODES_AT_V38, start=max_initial_node_id + 1)
    ]
    assert nodes_after == nodes_before + default_polygon_nodes_with_ids
    expected_internal_txs = [tuple(x[:3]) + tuple(x[5:]) for x in expected_internal_txs]
    assert cursor.execute('SELECT * from evm_internal_transactions ORDER BY value DESC').fetchall() == expected_internal_txs  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM used_query_ranges WHERE name=?', (aave_range_key,)).fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="aave_events";').fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="amm_events";').fetchone()[0] == 0  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE "uniswap_events_%"').fetchone() == (0,)  # noqa: E501
    assert cursor.execute('SELECT COUNT(name) FROM used_query_ranges WHERE name LIKE "sushiswap_events_%"').fetchone() == (0,)  # noqa: E501
    # Make sure that duplicate events were removed
    expected_history_events = [expected_history_events[0]] + expected_history_events[2:6]
    assert cursor.execute('SELECT * from history_events WHERE entry_type=4;').fetchall() == expected_history_events  # noqa: E501
    expected_eth_staking_events_info = [expected_eth_staking_events_info[0]] + expected_eth_staking_events_info[2:6]  # noqa: E501
    assert cursor.execute('SELECT * from eth_staking_events_info').fetchall() == expected_eth_staking_events_info  # noqa: E501


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
        "SELECT identifier FROM history_events WHERE event_identifier LIKE 'eth2_withdrawal_%'",  # noqa: E501
    ).fetchall()}
    block_events_before = {x[0] for x in cursor.execute(
        "SELECT identifier FROM history_events WHERE event_identifier LIKE 'evm_1_block_%'",  # noqa: E501
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
    cursor.execute('SELECT value FROM settings WHERE name="current_price_oracles"')
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
    assert cursor.execute('SELECT COUNT(*) FROM evm_tx_mappings').fetchone()[0] == 0  # noqa: E501  # events have been reset so no transactions are now decoded
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
    with db.conn.write_ctx() as write_cursor, pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member  # noqa: E501
        write_cursor.execute(
            'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',   # noqa: E501
            ('flashbots2', 'https://rpc.flashbots.net/', 0, 1, '0.2', 'ETH'),
        )

    # get current oracles and check that saddle was removed and all others remain as they were.
    settings = db.get_settings(cursor=cursor)
    expected_oracles = [CurrentPriceOracle.deserialize(oracle) for oracle in oracles if oracle != 'saddle']  # noqa: E501
    assert settings.current_price_oracles == expected_oracles


def test_latest_upgrade_adds_remove_tables(user_data_dir):
    """
    This is a test that we can only do for the last upgrade.
    It tests that we know and have included addition statements for all
    of the new database tables introduced.

    Each time a new database upgrade is added this will need to be modified as
    this is just to reminds us not to forget to add create table statements.
    """
    msg_aggregator = MessagesAggregator()
    base_database = 'v37_rotkehlchen.db'
    _use_prepared_db(user_data_dir, base_database)
    last_db = _init_db_with_target_version(
        target_version=37,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = last_db.conn.cursor()
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables_before = {x[0] for x in result}
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="view"')
    views_before = {x[0] for x in result}

    last_db.logout()

    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=38,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables_after_upgrade = {x[0] for x in result}
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="view"')
    views_after_upgrade = {x[0] for x in result}
    # also add latest tables (this will indicate if DB upgrade missed something
    db.conn.executescript(DB_SCRIPT_CREATE_TABLES)
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables_after_creation = {x[0] for x in result}
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="view"')
    views_after_creation = {x[0] for x in result}

    removed_tables = {'aave_events', 'amm_events'}
    removed_views = set()
    missing_tables = tables_before - tables_after_upgrade
    missing_views = views_before - views_after_upgrade
    assert missing_tables == removed_tables
    assert missing_views == removed_views
    assert tables_after_creation - tables_after_upgrade == {'optimism_transactions'}
    assert views_after_creation - views_after_upgrade == set()
    new_tables = tables_after_upgrade - tables_before
    assert new_tables == set()
    new_views = views_after_upgrade - views_before
    assert new_views == set()


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
    del data
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    with pytest.raises(DBUpgradeError):
        data.unlock(username, '123', create_new=False, resume_from_backup=False)


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


def test_unfinished_upgrades(user_data_dir):
    _use_prepared_db(user_data_dir, 'v33_rotkehlchen.db')
    msg_aggregator = MessagesAggregator()
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
    # There are no backups, so it is supposed to raise an error
    with pytest.raises(DBUpgradeError):
        _init_db_with_target_version(
            target_version=34,
            user_data_dir=user_data_dir,
            msg_aggregator=msg_aggregator,
            resume_from_backup=True,
        )

    # Add a backup
    backup_path = user_data_dir / f'{ts_now()}_rotkehlchen_db_v33.backup'
    shutil.copy(Path(__file__).parent.parent / 'data' / 'v33_rotkehlchen.db', backup_path)
    backup_connection = DBConnection(
        path=str(backup_path),
        connection_type=DBConnectionType.USER,
        sql_vm_instructions_cb=0,
    )
    backup_connection.executescript('PRAGMA key="123"')  # unlock
    with backup_connection.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO settings VALUES("is_backup", "Yes")')  # mark as a backup  # noqa: E501

    db = _init_db_with_target_version(  # Now the backup should be used
        target_version=34,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        resume_from_backup=True,
    )
    # Check that there is no setting left
    with db.conn.read_ctx() as cursor:
        assert db.get_setting(cursor, 'ongoing_upgrade_from_version') is None
        # Check that the backup was used
        assert cursor.execute('SELECT value FROM settings WHERE name="is_backup"').fetchone()[0] == 'Yes'  # noqa: E501
