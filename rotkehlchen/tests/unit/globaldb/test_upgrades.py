import json
import shutil
from contextlib import ExitStack
from pathlib import Path
from sqlite3 import IntegrityError

import pytest
from eth_utils.address import to_checksum_address
from freezegun import freeze_time

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_keys_and_values_like,
    globaldb_get_general_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
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
from rotkehlchen.globaldb.upgrades.v5_v6 import V5_V6_UPGRADE_UNIQUE_CACHE_KEYS
from rotkehlchen.globaldb.utils import GLOBAL_DB_VERSION
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_upgrade_to
from rotkehlchen.types import YEARN_VAULTS_V1_PROTOCOL, CacheType, ChainID, EvmTokenKind, Timestamp
from rotkehlchen.utils.misc import ts_now

# TODO: Perhaps have a saved version of that global DB for the tests and query it too?
ASSETS_IN_V2_GLOBALDB = 3095
YEARN_V1_ASSETS_IN_V3 = 32


def _count_sql_file_sentences(file_name: str, skip_statements: int = 0):
    """
    Count the sql lines in scripts used during upgrades. If the skip_statements argument is
    provided it ignores the [skip_statements first] statements and counts the rows for
    [the skip_statements + 1] statement.
    """
    insertions_made = 0
    skipped_statements = 0
    dir_path = Path(__file__).resolve().parent.parent.parent.parent
    with open(dir_path / 'data' / file_name, encoding='utf8') as f:
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
@pytest.mark.parametrize('reload_user_assets', [False])
@pytest.mark.parametrize('custom_globaldb', ['v2_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [2])
def test_upgrade_v2_v3(globaldb: GlobalDBHandler):
    """Test globalDB upgrade v2->v3"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 2
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
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
        )

    assert globaldb.get_setting_value('version', 0) == 3
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
@pytest.mark.parametrize('custom_globaldb', ['v3_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [3])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v3_v4(globaldb: GlobalDBHandler):
    """Test the global DB upgrade from v3 to v4"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 3
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name IN (?, ?)',
            ('contract_abi', 'contract_data'),
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute('SELECT COUNT(*) from evm_tokens WHERE protocol="yearn-v1"')
        assert cursor.fetchone()[0] == YEARN_V1_ASSETS_IN_V3

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 4)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
        )

    assert globaldb.get_setting_value('version', 0) == 4
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name IN (?, ?)',
            ('contract_abi', 'contract_data'),
        )
        assert cursor.fetchone()[0] == 2
        expected_contracts_length = 93 - 1 + 1 + 3 + 1  # len(eth_contracts) + 1 in dxdao file -1 by removing multicall1 + 3 the new optimism contracts + by adding liquity staking  # noqa: E501
        cursor.execute('SELECT COUNT(*) FROM contract_data')
        assert cursor.fetchone()[0] == expected_contracts_length

        groups = [MAKERDAO_ABI_GROUP_1, MAKERDAO_ABI_GROUP_2, MAKERDAO_ABI_GROUP_3, YEARN_ABI_GROUP_1, YEARN_ABI_GROUP_2, YEARN_ABI_GROUP_3, YEARN_ABI_GROUP_4]  # noqa: E501
        cursor.execute('SELECT COUNT(*) FROM contract_abi')
        assert cursor.fetchone()[0] == (  # len(eth_abi) + contracts_length - uniswap_NFT_MANAGER - 3 optimism contracts that share ABI with mainnet - len(7 abi groups) + 7  # noqa: E501
            15 +
            expected_contracts_length - 1 - 3 -
            sum(len(x) for x in groups) +
            len(groups)
        )

        # check balance scan, multicall and ds proxy registry are fine and in both chains
        cursor.execute('SELECT id from contract_abi WHERE name=?', ('BALANCE_SCAN',))
        balancescan_abi_id = cursor.fetchone()[0]
        cursor.execute('SELECT id from contract_abi WHERE name=?', ('MULTICALL2',))
        multicall_abi_id = cursor.fetchone()[0]
        cursor.execute('SELECT id from contract_abi WHERE name=?', ('DS_PROXY_REGISTRY',))
        ds_registry_abi_id = cursor.fetchone()[0]
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
        result = cursor.execute(
            'SELECT address, chain_id, abi, deployed_block FROM contract_data WHERE name=? ORDER BY chain_id',  # noqa: E501
            ('DS_PROXY_REGISTRY',),
        ).fetchall()
        assert result == [
            ('0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4', 1, ds_registry_abi_id, 5834629),
            ('0x283Cc5C26e53D66ed2Ea252D986F094B37E6e895', 10, ds_registry_abi_id, 2944824),
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

        # test that the blockchain column is nullable
        cursor.execute('INSERT INTO address_book(address, blockchain, name) VALUES ("0xc37b40ABdB939635068d3c5f13E7faF686F03B65", NULL, "yabir everywhere")')  # noqa: E501

        # test that address book entries were kept
        cursor.execute('SELECT * FROM address_book')
        assert cursor.fetchall() == [
            ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'ETH', 'yabir secret account'),
            ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'ETH', 'lefteris GTC'),
            ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', None, 'yabir everywhere'),
        ]

        # check that yearn tokens got their protocol updated
        cursor.execute('SELECT COUNT(*) from evm_tokens WHERE protocol="yearn-v1"')
        assert cursor.fetchone()[0] == 0
        cursor.execute('SELECT COUNT(*) from evm_tokens WHERE protocol=?', (YEARN_VAULTS_V1_PROTOCOL,))  # noqa: E501
        assert cursor.fetchone()[0] == YEARN_V1_ASSETS_IN_V3


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v4_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [4])
@pytest.mark.parametrize('reload_user_assets', [False])
@freeze_time('2023-03-20')  # freezing time just to make sure comparisons of timestamps won't fail
def test_upgrade_v4_v5(globaldb: GlobalDBHandler):
    """Test the global DB upgrade from v4 to v5"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 4
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name=?',
            ('default_rpc_nodes',),
        )
        assert cursor.fetchone()[0] == 0
        last_queried_ts = globaldb_get_general_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LP_TOKENS,),
        )
        assert last_queried_ts == Timestamp(1676727187)  # 1676727187 is just some random value in the db  # noqa: E501
        pool_tokens_in_global_db = globaldb_get_general_cache_keys_and_values_like(
            cursor=cursor,
            key_parts=(CacheType.CURVE_POOL_TOKENS,),
        )
        assert len(pool_tokens_in_global_db) > 0, 'There should be some pool tokens set'
        contracts_before_upgrade = cursor.execute(
            'SELECT address, chain_id, abi, deployed_block FROM contract_data',
        ).fetchall()
        assert len(contracts_before_upgrade) > 0, 'There should be some contracts'
        columns = [column_data[1] for column_data in cursor.execute('PRAGMA table_info(contract_data)')]  # noqa: E501
        assert 'name' in columns, 'The name column should be in the contract_data table'

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 5)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
        )

    assert globaldb.get_setting_value('version', 0) == 5

    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name=?',
            ('default_rpc_nodes',),
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes')
        assert cursor.fetchone()[0] == 10

        # check that we have five nodes for each chain
        nodes_file_path = Path(__file__).resolve().parent.parent.parent.parent / 'data' / 'nodes.json'  # noqa: E501
        with open(nodes_file_path, encoding='utf8') as f:
            nodes_info = json.loads(f.read())
            nodes_tuples_from_file = [
                (idx, node['name'], node['endpoint'], int(False), int(True), str(node['weight']), node['blockchain'])  # noqa: E501
                for idx, node in enumerate(nodes_info, start=1)
            ]

            nodes_tuples_from_db = cursor.execute('SELECT * FROM default_rpc_nodes').fetchall()
            assert nodes_tuples_from_db == nodes_tuples_from_file

        last_queried_ts = globaldb_get_general_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LP_TOKENS,),
        )
        assert last_queried_ts == Timestamp(0)
        pool_tokens_in_global_db = globaldb_get_general_cache_keys_and_values_like(
            cursor=cursor,
            key_parts=(CacheType.CURVE_POOL_TOKENS,),
        )
        assert len(pool_tokens_in_global_db) == 0, 'All curve pool tokens should have been deleted'
        contracts_after_upgrade = cursor.execute('SELECT * FROM contract_data').fetchall()
        assert contracts_after_upgrade == contracts_before_upgrade
        columns = [column_data[1] for column_data in cursor.execute('PRAGMA table_info(contract_data)')]  # noqa: E501
        assert 'name' not in columns, 'The name column should not be in the contract_data table'


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v5_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [5])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v5_v6(globaldb: GlobalDBHandler):
    """Test the global DB upgrade from v5 to v6"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        # check that unique_cache table is not present in the database
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name=?',
            ('unique_cache',),
        )
        assert cursor.fetchone()[0] == 0
        # get number of entries in general_cache before upgrade
        cursor.execute('SELECT COUNT(*) FROM general_cache')
        gen_cache_content_before = cursor.fetchone()[0]
        # check that unique_cache_keys content are still in general_cache
        unique_keys_to_num_entries = {}
        gen_cache_unique_key_content = 0
        for key_part in V5_V6_UPGRADE_UNIQUE_CACHE_KEYS:
            cursor.execute(
                'SELECT COUNT(*) FROM general_cache WHERE key LIKE ?',
                (f'{key_part.serialize()}%',),
            )
            unique_keys_to_num_entries[key_part] = int(cursor.fetchone()[0])
            gen_cache_unique_key_content += unique_keys_to_num_entries[key_part]

        # create a set of the old entries ensuring that the rows have checksummed addresses
        # for the identifiers in multiasset_mappings
        old_multiasset_mappings = set()
        cursor.execute('SELECT * FROM multiasset_mappings ORDER BY collection_id, asset')
        for collection_id, asset_id in cursor:
            address = asset_id.split(':')[-1]
            checksummed_address = to_checksum_address(address)
            new_id = asset_id.replace(address, checksummed_address)
            old_multiasset_mappings.add((collection_id, new_id))

    with globaldb.conn.write_ctx() as write_cursor:
        # add some dummy data into cache to verify behaviour during transfer.
        test_cache_key = next(iter(V5_V6_UPGRADE_UNIQUE_CACHE_KEYS)).serialize() + 'test'
        values = ['abc', 'xyz', '123']
        tuples = [(test_cache_key, value, ts_now()) for value in values]
        write_cursor.executemany(
            'INSERT OR REPLACE INTO general_cache '
            '(key, value, last_queried_ts) VALUES (?, ?, ?)',
            tuples,
        )

        # test you can add multiple combos of collection id and asset before upgrade
        write_cursor.execute(
            'INSERT INTO multiasset_mappings(collection_id, asset) VALUES(?, ?)',
            (7, 'eip155:1/erc20:0xD46bA6D942050d489DBd938a2C909A5d5039A161'),
        )
        write_cursor.execute(  # delete to preserve correctness and add 1 back
            'DELETE FROM multiasset_mappings WHERE collection_id=? AND asset=?',
            (7, 'eip155:1/erc20:0xD46bA6D942050d489DBd938a2C909A5d5039A161'),
        )
        write_cursor.execute(
            'INSERT INTO multiasset_mappings(collection_id, asset) VALUES(?, ?)',
            (7, 'eip155:1/erc20:0xD46bA6D942050d489DBd938a2C909A5d5039A161'),
        )

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 6)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
        )
    assert globaldb.get_setting_value('version', 0) == 6
    with globaldb.conn.read_ctx() as cursor:
        # check that unique_cache table is present in the database
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name=?',
            ('unique_cache',),
        )
        assert cursor.fetchone()[0] == 1
        # check that of dummy entry, only first value is transferred to unique_cache
        value = globaldb_get_unique_cache_value(cursor, (next(iter(V5_V6_UPGRADE_UNIQUE_CACHE_KEYS)), 'test'))  # type: ignore  # noqa: E501
        assert value == values[0]

        with globaldb.conn.write_ctx() as write_cursor:
            # delete dummy entry to maintain db consistency
            write_cursor.execute('DELETE FROM unique_cache WHERE key=?', (test_cache_key,))

            # Check we can't add already existing collection_id + asset to multiasset_mappings
            with pytest.raises(IntegrityError):
                write_cursor.execute(
                    'INSERT INTO multiasset_mappings(collection_id, asset) VALUES(?, ?)',
                    (7, 'eip155:1/erc20:0xD46bA6D942050d489DBd938a2C909A5d5039A161'),
                )

        # check that appropriate cache data is transfered
        for key_part in V5_V6_UPGRADE_UNIQUE_CACHE_KEYS:
            cursor.execute(
                'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ?',
                (f'{key_part.serialize()}%',),
            )
            assert cursor.fetchone()[0] == unique_keys_to_num_entries[key_part]
            cursor.execute(
                'SELECT COUNT(*) FROM general_cache WHERE key LIKE ?',
                (f'{key_part.serialize()}%',),
            )
            assert cursor.fetchone()[0] == 0
        unique_cache_content = cursor.execute('SELECT COUNT(*) FROM unique_cache').fetchone()[0]
        # get number of entries in general_cache after upgrade
        gen_cache_content_after = cursor.execute('SELECT COUNT(*) FROM general_cache').fetchone()[0]  # noqa: E501
        assert gen_cache_unique_key_content == unique_cache_content
        assert gen_cache_content_before == gen_cache_content_after + gen_cache_unique_key_content
        assert set(cursor.execute(
            'SELECT * FROM multiasset_mappings ORDER BY collection_id, asset',
        )) == old_multiasset_mappings

        # test that the VELO asset got deleted
        assert cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?',
            ('VELO',),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM common_asset_details WHERE identifier=?',
            ('VELO',),
        ).fetchone()[0] == 0


@pytest.mark.parametrize('custom_globaldb', ['v2_global.db'])
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
    backup_path = globaldb._data_directory / GLOBALDIR_NAME / f'{ts_now()}_global_db_v2.backup'  # type: ignore  # _data_directory is definitely not null here
    shutil.copy(Path(__file__).parent.parent.parent / 'data' / 'v2_global.db', backup_path)
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
@pytest.mark.parametrize('custom_globaldb', ['v2_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_applying_all_upgrade(globaldb: GlobalDBHandler):
    """Test globalDB upgrade from v2 to latest"""
    # Check the state before upgrading
    assert globaldb.get_setting_value('version', 0) == 2
    with globaldb.conn.cursor() as cursor:
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="eip155:/erc20:0x32c6fcC9bC912C4A30cd53D2E606461e44B77AF2"').fetchone()[0] == 0  # noqa: E501

    maybe_upgrade_globaldb(
        connection=globaldb.conn,
        global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
        db_filename=GLOBALDB_NAME,
    )

    assert globaldb.get_setting_value('version', 0) == GLOBAL_DB_VERSION
    with globaldb.conn.cursor() as cursor:
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="eip155:/erc20:0x32c6fcC9bC912C4A30cd53D2E606461e44B77AF2"').fetchone()[0] == 1  # noqa: E501
