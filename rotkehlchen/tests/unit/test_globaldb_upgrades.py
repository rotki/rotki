import shutil
from contextlib import ExitStack
from pathlib import Path

import pytest

from rotkehlchen.assets.types import AssetType
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.upgrades.manager import maybe_upgrade_globaldb
from rotkehlchen.globaldb.upgrades.v2_v3 import OTHER_EVM_CHAINS_ASSETS
from rotkehlchen.globaldb.upgrades.v3_v4 import (
    MAKERDAO_ABI_GROUP_1,
    MAKERDAO_ABI_GROUP_2,
    MAKERDAO_ABI_GROUP_3,
    YEARN_ABI_GROUP_1,
    YEARN_ABI_GROUP_2,
    YEARN_ABI_GROUP_3,
    YEARN_ABI_GROUP_4,
)
from rotkehlchen.globaldb.utils import GLOBAL_DB_FILENAME, GLOBAL_DB_VERSION
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_upgrade_to
from rotkehlchen.types import ChainID, EvmTokenKind
from rotkehlchen.utils.misc import ts_now

# TODO: Perhaps have a saved version of that global DB for the tests and query it too?
ASSETS_IN_V2_GLOBALDB = 3095


def _count_sql_file_sentences(file_name: str, skip_statements: int = 0):
    """
    Count the sql lines in scripts used during upgrades. If the skip_statements argument is
    provided it ignores the [skip_statements first] statements and counts the rows for
    [the skip_statements + 1] statement.
    """
    insertions_made = 0
    skipped_statements = 0
    dir_path = Path(__file__).resolve().parent.parent.parent
    with open(dir_path / 'data' / file_name) as f:
        insertions_made = 0
        line = ' '
        while line:
            line = f.readline()
            if skipped_statements < skip_statements:
                if ';' in line:
                    skipped_statements += 1
                continue

            if skipped_statements == skip_statements and 'INSERT' in line:
                insertions_made = 1
                continue

            insertions_made += 1
            if ';' in line:
                break

    return insertions_made - 1


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('globaldb_version', [2])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v2_v3(globaldb):
    """Test globalDB upgrade v2->v3"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', None) == 2
        cursor.execute(
            'SELECT COUNT(*) FROM price_history WHERE from_asset=? OR to_asset=?',
            ('BIFI', 'BIFI'),
        )
        assert cursor.fetchone()[0] == 2

        # Check that the expected assets are present
        ids_in_db = {row[0] for row in cursor.execute('SELECT * FROM user_owned_assets')}
        assert ids_in_db == {
            '_ceth_0x4E15361FD6b4BB609Fa63C81A2be19d873717870',
            '_ceth_0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5',
            '_ceth_0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0',
            'BTC',
            'ETH',
            'USD',
            'EUR',
            'BCH',
            'BIFI',
        }

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 3)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / 'global_data',
            db_filename=GLOBAL_DB_FILENAME,
        )

    assert globaldb.get_setting_value('version', None) == 3
    assets_inserted_by_update = _count_sql_file_sentences('globaldb_v2_v3_assets.sql')
    with globaldb.conn.read_ctx() as cursor:
        # test that we have the same number of assets before and after the migration
        # So same assets as before plus the new ones we add via the sql file minus the ones we skip
        actual_assets_num = cursor.execute('SELECT COUNT(*) from assets').fetchone()[0]
        assert actual_assets_num == ASSETS_IN_V2_GLOBALDB + assets_inserted_by_update - len(OTHER_EVM_CHAINS_ASSETS)  # noqa: E501

        # Check that the properties of LUSD (ethereum token) have been correctly translated
        weth_token_data = cursor.execute('SELECT identifier, token_kind, chain, address, decimals, protocol FROM evm_tokens WHERE address = "0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"').fetchone()  # noqa: E501
        assert weth_token_data[0] == 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'
        assert EvmTokenKind.deserialize_from_db(weth_token_data[1]) == EvmTokenKind.ERC20
        assert ChainID.deserialize_from_db(weth_token_data[2]) == ChainID.ETHEREUM
        assert weth_token_data[3] == '0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'
        assert weth_token_data[4] == 18
        assert weth_token_data[5] is None
        weth_asset_data = cursor.execute('SELECT symbol, coingecko, cryptocompare, forked, started, swapped_for FROM common_asset_details WHERE identifier = "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"').fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'LUSD'
        assert weth_asset_data[1] == 'liquity-usd'
        assert weth_asset_data[2] == 'LUSD'
        assert weth_asset_data[3] is None
        assert weth_asset_data[4] == 1617611299
        assert weth_asset_data[5] is None
        weth_asset_data = cursor.execute('SELECT name, type FROM assets WHERE identifier = "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"').fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'LUSD Stablecoin'
        assert AssetType.deserialize_from_db(weth_asset_data[1]) == AssetType.EVM_TOKEN

        # Check that a normal asset also gets correctly mapped
        weth_asset_data = cursor.execute('SELECT symbol, coingecko, cryptocompare, forked, started, swapped_for FROM common_asset_details WHERE identifier = "BCH"').fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'BCH'
        assert weth_asset_data[1] == 'bitcoin-cash'
        assert weth_asset_data[2] is None
        assert weth_asset_data[3] == 'BTC'
        assert weth_asset_data[4] == 1501593374
        assert weth_asset_data[5] is None
        weth_asset_data = cursor.execute('SELECT name, type FROM assets WHERE identifier = "BCH"').fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'Bitcoin Cash'
        assert AssetType.deserialize_from_db(weth_asset_data[1]) == AssetType.OWN_CHAIN

        ids_in_db = {row[0] for row in cursor.execute('SELECT * FROM user_owned_assets')}
        assert ids_in_db == {
            'eip155:1/erc20:0x4E15361FD6b4BB609Fa63C81A2be19d873717870',
            'eip155:1/erc20:0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5',
            'eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0',
            'BTC',
            'ETH',
            'USD',
            'EUR',
            'BCH',
            'eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A',
        }

        # FLO asset is the one that is not an evm token but has `swapped_for` pointing to an evm
        # token. Here we check that its `swapped_for` field is updated properly.
        # 1. Check that FLO asset exists
        flo_swapped_for = cursor.execute(
            'SELECT swapped_for FROM common_asset_details WHERE identifier="FLO"',
        ).fetchone()
        assert flo_swapped_for is not None
        # 2. Check that its `swapped_for` was updated properly
        found_assets = cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier = ?', (flo_swapped_for[0],),
        ).fetchone()[0]
        # should have found one asset that FLO's swapped_for is pointing to
        assert found_assets == 1

        # Check that new evm tokens have been correctly upgraded in price_history. Checking BIFI
        cursor.execute('SELECT price FROM price_history WHERE from_asset == "eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A"')  # noqa: E501
        assert cursor.fetchone()[0] == '464.99'
        cursor.execute('SELECT price FROM price_history WHERE to_asset == "eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A"')  # noqa: E501
        assert cursor.fetchone()[0] == '0.00215058388'
        cursor.execute(
            'SELECT COUNT(*) FROM price_history WHERE from_asset=? OR to_asset=?',
            ('BIFI', 'BIFI'),
        )
        assert cursor.fetchone()[0] == 0
        assert GlobalDBHandler().get_schema_version() == 3


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('globaldb_version', [3])
@pytest.mark.parametrize('target_globaldb_version', [3])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v3_v4(globaldb):
    """Test the global DB upgrade from v3 to v4"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', None) == 3
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name IN (?, ?)',
            ('contract_abi', 'contract_data'),
        )
        assert cursor.fetchone()[0] == 2

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 4)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / 'global_data',
            db_filename=GLOBAL_DB_FILENAME,
        )

    assert globaldb.get_setting_value('version', None) == 4
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name IN (?, ?)',
            ('contract_abi', 'contract_data'),
        )
        expected_contracts_length = 93 - 1 + 1 + 2 + 1  # len(eth_contracts) + 1 in dxdao file -1 by removing multicall1 + 2 the new optimism contracts + by adding liquity staking  # noqa: E501
        assert cursor.fetchone()[0] == 2
        cursor.execute('SELECT COUNT(*) FROM contract_data')
        assert cursor.fetchone()[0] == expected_contracts_length

        groups = [MAKERDAO_ABI_GROUP_1, MAKERDAO_ABI_GROUP_2, MAKERDAO_ABI_GROUP_3, YEARN_ABI_GROUP_1, YEARN_ABI_GROUP_2, YEARN_ABI_GROUP_3, YEARN_ABI_GROUP_4]  # noqa: E501
        cursor.execute('SELECT COUNT(*) FROM contract_abi')
        assert cursor.fetchone()[0] == (  # len(eth_abi) + contracts_length - uniswap_NFT_MANAGER -2 optimism contracts that share ABI with mainnet - len(7 abi groups) + 7  # noqa: E501
            15 +
            expected_contracts_length - 1 - 2 -
            sum(len(x) for x in groups) +
            len(groups)
        )

        # check balance scan and multicall are fine and in both chains
        cursor.execute('SELECT id from contract_abi WHERE name=?', ('BALANCE_SCAN',))
        balancescan_abi_id = cursor.fetchone()[0]
        cursor.execute('SELECT id from contract_abi WHERE name=?', ('MULTICALL2',))
        multicall_abi_id = cursor.fetchone()[0]
        result = cursor.execute(
            'SELECT address, chain_id, abi, deployed_block FROM contract_data WHERE name=? ORDER BY chain_id',  # noqa: E501
            ('BALANCE_SCAN',),
        ).fetchall()
        assert result == [
            ('0x86F25b64e1Fe4C5162cDEeD5245575D32eC549db', 1, balancescan_abi_id, 9665853),
            ('0x1e21bc42FaF802A0F115dC998e2F0d522aDb1F68', 10, balancescan_abi_id, 46787373),
        ]
        result = cursor.execute(
            'SELECT address, chain_id, abi, deployed_block FROM contract_data WHERE name=? ORDER BY chain_id',  # noqa: E501
            ('MULTICALL2',),
        ).fetchall()
        assert result == [
            ('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696', 1, multicall_abi_id, 12336033),
            ('0x2DC0E2aa608532Da689e89e237dF582B783E552C', 10, multicall_abi_id, 722566),
        ]

        # check that old names are not in there
        assert cursor.execute(
            'SELECT COUNT(*) from contract_abi WHERE name in (?, ?, ?)',
            ('ETH_SCAN', 'ETH_MULTICALL', 'ETH_MULTICALL2'),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) from contract_data WHERE name in (?, ?, ?)',
            ('ETH_SCAN', 'ETH_MULTICALL', 'ETH_MULTICALL2'),
        ).fetchone()[0] == 0

        cursor.execute('SELECT COUNT(*) FROM asset_collections')
        assert cursor.fetchone()[0] == _count_sql_file_sentences('populate_asset_collections.sql')
        cursor.execute('SELECT COUNT(*) FROM multiasset_mappings')
        assert cursor.fetchone()[0] == _count_sql_file_sentences('populate_multiasset_mappings.sql')  # noqa: E501
        assert GlobalDBHandler().get_schema_version() == 4


@pytest.mark.parametrize('globaldb_version', [2])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_unfinished_upgrades(globaldb: GlobalDBHandler):
    assert globaldb.used_backup is False
    globaldb.add_setting_value(  # Pretend that an upgrade was started
        name='ongoing_upgrade_from_version',
        value=2,
    )
    # There are no backups, so it is supposed to raise an error
    with pytest.raises(DBUpgradeError):
        create_globaldb(globaldb._data_directory, 0)

    # Add a backup
    backup_path = globaldb._data_directory / 'global_data' / f'{ts_now()}_global_db_v2.backup'  # type: ignore  # _data_directory is definitely not null here  # noqa: E501
    shutil.copy(Path(__file__).parent.parent / 'data' / 'v2_global.db', backup_path)
    backup_connection = DBConnection(
        path=str(backup_path),
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    with backup_connection.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO settings VALUES("is_backup", "Yes")')  # mark as a backup  # noqa: E501

    globaldb = create_globaldb(globaldb._data_directory, 0)  # Now the backup should be used
    assert globaldb.used_backup is True
    # Check that there is no setting left
    assert globaldb.get_setting_value('ongoing_upgrade_from_version', -1) == -1
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT value FROM settings WHERE name="is_backup"').fetchone()[0] == 'Yes'  # noqa: E501


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('globaldb_version', [2])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_applying_all_upgrade(globaldb):
    """Test globalDB upgrade from v2 to latest"""
    # Check the state before upgrading
    assert globaldb.get_setting_value('version', None) == 2
    with globaldb.conn.cursor() as cursor:
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="eip155:/erc20:0x32c6fcC9bC912C4A30cd53D2E606461e44B77AF2"')[0] == 0  # noqa: E501

    maybe_upgrade_globaldb(
        connection=globaldb.conn,
        global_dir=globaldb._data_directory / 'global_data',
        db_filename=GLOBAL_DB_FILENAME,
    )

    assert globaldb.get_setting_value('version', None) == GLOBAL_DB_VERSION
    with globaldb.conn.cursor() as cursor:
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="eip155:/erc20:0x32c6fcC9bC912C4A30cd53D2E606461e44B77AF2"')[0] == 1  # noqa: E501
