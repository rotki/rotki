from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.constants.misc import DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.upgrade_manager import MIN_SUPPORTED_USER_DB_VERSION, UPGRADES_LIST
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    mock_dbhandler_add_globaldb_assetids,
    mock_dbhandler_update_owned_assets,
)
from rotkehlchen.types import make_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import HexBytes


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
            _new_deserialized = HistoryBaseEntry.deserialize_from_db(_new)
            _new[tx_hash_index] = _new_deserialized.serialized_event_identifier
        else:
            _new[tx_hash_index] = make_evm_tx_hash(_new[tx_hash_index]).hex()  # noqa: 501 pylint: disable=no-member
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
) -> DBHandler:
    no_tables_created_after_init = patch(
        'rotkehlchen.db.dbhandler.DB_SCRIPT_CREATE_TABLES',
        new='',
    )
    with ExitStack() as stack:
        stack.enter_context(target_patch(target_version=target_version))
        if target_version not in (2, 4):
            # Some early upgrade tests rely on a mocked creation so we need to not touch it
            # for others do not allow latest tables to be created after init
            stack.enter_context(no_tables_created_after_init)
        if target_version <= 25:
            stack.enter_context(mock_dbhandler_update_owned_assets())
            stack.enter_context(mock_dbhandler_add_globaldb_assetids())
        db = DBHandler(
            user_data_dir=user_data_dir,
            password='123',
            msg_aggregator=msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
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
    transactions_before = []
    transactions_before_query = cursor.execute('SELECT tx_hash, block_number, from_address, to_address, nonce from ethereum_transactions;')  # noqa: E501
    for entry in transactions_before_query:
        transactions_before.append((
            '0x' + entry[0].hex(),
            entry[1],
            entry[2],
            entry[3],
            entry[4],
        ))
    assert transactions_before == expected_transactions_before

    db_v28.logout()
    # Migrate to v29
    db = _init_db_with_target_version(
        target_version=29,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
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
    transactions_after = []
    transactions_after_query = cursor.execute('SELECT tx_hash, block_number, from_address, to_address, nonce from ethereum_transactions;')  # noqa: E501
    for entry in transactions_after_query:
        transactions_after.append((
            '0x' + entry[0].hex(),
            entry[1],
            entry[2],
            entry[3],
            entry[4],
        ))
    assert transactions_after == expected_transactions_after

    # check that uniswap_events table was renamed
    cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="uniswap_events";',
    )
    assert cursor.fetchone()[0] == 0
    cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="amm_events";')
    assert cursor.fetchone()[0] == 1

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
    )
    # Finally also make sure that we have updated to the target version
    with db.conn.read_ctx() as cursor:
        assert db.get_setting(cursor, 'version') == 30
    cursor = db.conn.cursor()
    # Check that existing balances are not considered as liabilities after migration
    cursor.execute('SELECT category FROM manually_tracked_balances;')
    assert cursor.fetchone() == ('A',)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_30_to_31(user_data_dir):  # pylint: disable=unused-argument  # noqa: E501
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
    )

    cursor = db.conn.cursor()
    # Finally also make sure that we have updated to the target version
    assert db.get_setting(cursor, 'version') == 31
    cursor = db.conn.cursor()
    # Check that the new table is created
    result = cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="eth2_validators"')  # noqa: E501
    assert result.fetchone()[0] == 1
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
def test_upgrade_db_31_to_32(user_data_dir):  # pylint: disable=unused-argument  # noqa: E501
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
        assert cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name=?', (name,),
        ).fetchone()[0] == 1

    manual_balance_before = cursor.execute(
        'SELECT asset, label, amount, location, category FROM '
        'manually_tracked_balances;',
    ).fetchall()

    # check that the trades with invalid fee/fee_currency are present at this point
    trades_before = cursor.execute('SELECT * FROM trades WHERE id != ? AND id != ?', ("foo1", "foo2")).fetchall()  # noqa: E501
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
        assert cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name=?', (name,),
        ).fetchone()[0] == 0

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
def test_upgrade_db_32_to_33(user_data_dir):  # pylint: disable=unused-argument  # noqa: E501
    """Test upgrading the DB from version 32 to version 33.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v32_rotkehlchen.db')
    db_v32 = _init_db_with_target_version(
        target_version=32,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db_v32.conn.cursor()
    # check that you cannot add blockchain column in xpub_mappings
    with pytest.raises(sqlcipher.OperationalError) as exc_info:  # pylint: disable=no-member
        cursor.execute(
            'INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index, blockchain) '  # noqa: 501
            'VALUES ("1234", "abcd", "d", 3, 6, "BCH");',
        )
    assert 'cannot INSERT into generated column "blockchain"' in str(exc_info)
    xpub_mapping_data = (
        '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r',
        'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk',  # noqa: 501
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
    old_history_events = cursor.execute('SELECT * FROM history_events').fetchall()  # noqa: 501
    assert len(old_history_events) == 5
    db_v32.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=33,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()
    # check that xpubs mappings were not altered.
    new_xpub_mappings = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
    assert new_xpub_mappings == old_xpub_mappings
    # check that you can now add blockchain column in xpub_mappings
    address = '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe'
    cursor.execute(
        'INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index, blockchain) '  # noqa: 501
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
def test_upgrade_db_33_to_34(user_data_dir):  # pylint: disable=unused-argument  # noqa: E501
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
    )
    with db.conn.read_ctx() as cursor:
        cursor.execute('SELECT * FROM combined_trades_view ORDER BY time ASC')
        result = cursor.fetchall()
        assert isinstance(result[-1][10], str)
        assert result[-1][10] == '0xb1fcf4aef6af87a061ca03e92c4eb8039efe600d501ba288a8bae90f78c91db5'  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upgrade_db_34_to_35(user_data_dir):  # pylint: disable=unused-argument  # noqa: E501
    """Test upgrading the DB from version 34 to version 35.

    - Check that expected information for the changes in timestamps exists and is correct
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v34_rotkehlchen.db')
    db_v34 = _init_db_with_target_version(
        target_version=34,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    upgraded_tables = (
        'timed_balances',
        'timed_location_data',
        'ethereum_accounts_details',
        'trades',
        'asset_movements',
    )
    expected_timestamps = (
        [(1658564495,)],
        [(1637574520,)],
        [(1637574640,)],
        [(1595640208,), (1595640208,), (1595640208,)],
        [(1,)],
    )
    with db_v34.conn.read_ctx() as cursor:
        for table_name, expected_result in zip(upgraded_tables, expected_timestamps):
            cursor.execute(f'SELECT time from {table_name}')
            assert cursor.fetchall() == expected_result
    # Migrate the database
    db_v35 = _init_db_with_target_version(
        target_version=35,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    with db_v35.conn.read_ctx() as cursor:
        for table_name, expected_result in zip(upgraded_tables, expected_timestamps):
            cursor.execute(f'SELECT timestamp from {table_name}')
            assert cursor.fetchall() == expected_result


def test_latest_upgrade_adds_remove_tables(user_data_dir):
    """
    This is a test that we can only do for the last upgrade.
    It tests that we know and have included addition statements for all
    of the new database tables introduced.

    Each time a new database upgrade is added this will need to be modified as
    this is just to reminds us not to forget to add create table statements.
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v34_rotkehlchen.db')
    last_db = _init_db_with_target_version(
        target_version=34,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = last_db.conn.cursor()
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables_before = {x[0] for x in result}

    last_db.logout()
    # Execute upgrade
    db = _init_db_with_target_version(
        target_version=35,
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
    )
    cursor = db.conn.cursor()
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables_after_upgrade = {x[0] for x in result}
    # also add latest tables (this will indicate if DB upgrade missed something
    db.conn.executescript(DB_SCRIPT_CREATE_TABLES)
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables_after_creation = {x[0] for x in result}

    removed_tables = set()
    missing_tables = tables_before - tables_after_upgrade
    assert missing_tables == removed_tables
    assert tables_after_creation - tables_after_upgrade == set()
    new_tables = tables_after_upgrade - tables_before
    assert new_tables == {'user_notes'}


def test_db_newer_than_software_raises_error(data_dir, username, sql_vm_instructions_cb):
    """
    If the DB version is greater than the current known version in the
    software warn the user to use the latest version of the software
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True)
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
        data.unlock(username, '123', create_new=False)


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
        )
    assert 'Your account was last opened by a very old version of rotki' in str(upgrade_exception)
