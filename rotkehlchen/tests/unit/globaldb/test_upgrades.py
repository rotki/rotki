import json
import shutil
from contextlib import ExitStack
from pathlib import Path
from sqlite3 import IntegrityError
from typing import Final

import pytest
from eth_utils.address import to_checksum_address
from freezegun import freeze_time

from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.constants.assets import A_PAX, A_USDT
from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.utils import table_exists
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_keys_and_values_like,
    globaldb_get_general_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.schema import (
    DB_CREATE_LOCATION_ASSET_MAPPINGS,
    DB_CREATE_LOCATION_UNSUPPORTED_ASSETS,
)
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
from rotkehlchen.tests.utils.database import column_exists, index_exists
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_upgrade_to
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    CacheType,
    ChainID,
    Location,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import ts_now

# TODO: Perhaps have a saved version of that global DB for the tests and query it too?
ASSETS_IN_V2_GLOBALDB: Final = 3095
YEARN_V1_ASSETS_IN_V3: Final = 32


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
def test_upgrade_v2_v3(globaldb: GlobalDBHandler, messages_aggregator):
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
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 3
    assets_inserted_by_update = _count_sql_file_sentences('globaldb_v2_v3_assets.sql')
    with globaldb.conn.read_ctx() as cursor:
        # test that we have the same number of assets before and after the migration
        # So same assets as before plus the new ones we add via the sql file minus the ones we skip
        actual_assets_num = cursor.execute('SELECT COUNT(*) from assets').fetchone()[0]
        assert actual_assets_num == ASSETS_IN_V2_GLOBALDB + assets_inserted_by_update - len(OTHER_EVM_CHAINS_ASSETS)  # noqa: E501

        # Check that the properties of LUSD (ethereum token) have been correctly translated
        weth_token_data = cursor.execute("SELECT identifier, token_kind, chain, address, decimals, protocol FROM evm_tokens WHERE address = '0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'").fetchone()  # noqa: E501
        assert weth_token_data[0] == 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'
        assert TokenKind.deserialize_evm_from_db(weth_token_data[1]) == TokenKind.ERC20
        assert ChainID.deserialize_from_db(weth_token_data[2]) == ChainID.ETHEREUM
        assert weth_token_data[3] == '0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'
        assert weth_token_data[4] == 18
        assert weth_token_data[5] is None
        weth_asset_data = cursor.execute("SELECT symbol, coingecko, cryptocompare, forked, started, swapped_for FROM common_asset_details WHERE identifier = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'").fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'LUSD'
        assert weth_asset_data[1] == 'liquity-usd'
        assert weth_asset_data[2] == 'LUSD'
        assert weth_asset_data[3] is None
        assert weth_asset_data[4] == 1617611299
        assert weth_asset_data[5] is None
        weth_asset_data = cursor.execute("SELECT name, type FROM assets WHERE identifier = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'").fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'LUSD Stablecoin'
        assert AssetType.deserialize_from_db(weth_asset_data[1]) == AssetType.EVM_TOKEN

        # Check that a normal asset also gets correctly mapped
        weth_asset_data = cursor.execute("SELECT symbol, coingecko, cryptocompare, forked, started, swapped_for FROM common_asset_details WHERE identifier = 'BCH'").fetchone()  # noqa: E501
        assert weth_asset_data[0] == 'BCH'
        assert weth_asset_data[1] == 'bitcoin-cash'
        assert weth_asset_data[2] is None
        assert weth_asset_data[3] == 'BTC'
        assert weth_asset_data[4] == 1501593374
        assert weth_asset_data[5] is None
        weth_asset_data = cursor.execute("SELECT name, type FROM assets WHERE identifier = 'BCH'").fetchone()  # noqa: E501
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
            "SELECT swapped_for FROM common_asset_details WHERE identifier='FLO'",
        ).fetchone()
        assert flo_swapped_for is not None
        # 2. Check that its `swapped_for` was updated properly
        found_assets = cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier = ?', (flo_swapped_for[0],),
        ).fetchone()[0]
        # should have found one asset that FLO's swapped_for is pointing to
        assert found_assets == 1

        # Check that new evm tokens have been correctly upgraded in price_history. Checking BIFI
        cursor.execute("SELECT price FROM price_history WHERE from_asset == 'eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A'")  # noqa: E501
        assert cursor.fetchone()[0] == '464.99'
        cursor.execute("SELECT price FROM price_history WHERE to_asset == 'eip155:56/erc20:0xCa3F508B8e4Dd382eE878A314789373D80A5190A'")  # noqa: E501
        assert cursor.fetchone()[0] == '0.00215058388'
        cursor.execute(
            'SELECT COUNT(*) FROM price_history WHERE from_asset=? OR to_asset=?',
            ('BIFI', 'BIFI'),
        )
        assert cursor.fetchone()[0] == 0
        assert GlobalDBHandler.get_schema_version() == 3


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v3_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [3])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v3_v4(globaldb: GlobalDBHandler, messages_aggregator):
    """Test the global DB upgrade from v3 to v4"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 3
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type=? and name IN (?, ?)',
            ('table', 'contract_abi', 'contract_data'),
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute('SELECT COUNT(*) from evm_tokens WHERE protocol=?', ('yearn-v1',))
        assert cursor.fetchone()[0] == YEARN_V1_ASSETS_IN_V3

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 4)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 4
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type=? and name IN (?, ?)',
            ('table', 'contract_abi', 'contract_data'),
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
        assert GlobalDBHandler.get_schema_version() == 4

        # test that the blockchain column is nullable
        cursor.execute("INSERT INTO address_book(address, blockchain, name) VALUES ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', NULL, 'yabir everywhere')")  # noqa: E501

        # test that address book entries were kept
        cursor.execute('SELECT * FROM address_book')
        assert cursor.fetchall() == [
            ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'ETH', 'yabir secret account'),
            ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12', 'ETH', 'lefteris GTC'),
            ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', None, 'yabir everywhere'),
        ]

        # check that yearn tokens got their protocol updated
        cursor.execute('SELECT COUNT(*) from evm_tokens WHERE protocol=?', ('yearn-v1',))
        assert cursor.fetchone()[0] == 0
        cursor.execute('SELECT COUNT(*) from evm_tokens WHERE protocol=?', ('yearn_vaults_v1',))
        assert cursor.fetchone()[0] == YEARN_V1_ASSETS_IN_V3


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v4_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [4])
@pytest.mark.parametrize('reload_user_assets', [False])
@freeze_time('2023-03-20')  # freezing time just to make sure comparisons of timestamps won't fail
def test_upgrade_v4_v5(globaldb: GlobalDBHandler, messages_aggregator):
    """Test the global DB upgrade from v4 to v5"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 4
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type=? and name=?',
            ('table', 'default_rpc_nodes'),
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
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 5

    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type=? and name=?',
            ('table', 'default_rpc_nodes'),
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes')
        assert cursor.fetchone()[0] == 10

        # check that we have five nodes for each chain
        nodes_file_path = Path(__file__).resolve().parent.parent.parent.parent / 'data' / 'nodes.json'  # noqa: E501
        nodes_info = json.loads(nodes_file_path.read_text(encoding='utf8'))
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
def test_upgrade_v5_v6(globaldb: GlobalDBHandler, messages_aggregator):
    """Test the global DB upgrade from v5 to v6"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        # check that unique_cache table is not present in the database
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type=? and name=?',
            ('table', 'unique_cache'),
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
            msg_aggregator=messages_aggregator,
        )
    assert globaldb.get_setting_value('version', 0) == 6
    with globaldb.conn.read_ctx() as cursor:
        # check that unique_cache table is present in the database
        cursor.execute(
            'SELECT COUNT(*) FROM sqlite_master WHERE type=? and name=?',
            ('table', 'unique_cache'),
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

        # check that appropriate cache data is transferred
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


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v6_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [6])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v6_v7(globaldb: GlobalDBHandler, messages_aggregator):
    """Test the global DB upgrade from v6 to v7"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        # check that location_asset_mappings table is not present in the database
        assert table_exists(
            cursor=cursor,
            name='location_asset_mappings',
        ) is False
        # check that location_unsupported_assets table is not present in the database
        assert table_exists(
            cursor=cursor,
            name='location_unsupported_assets',
        ) is False

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 7)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )
    assert globaldb.get_setting_value('version', 0) == 7
    with globaldb.conn.read_ctx() as cursor:
        # check that location_asset_mappings table is present in the database
        assert table_exists(
            cursor=cursor,
            name='location_asset_mappings',
            schema=DB_CREATE_LOCATION_ASSET_MAPPINGS,
        ) is True

        # check that location_unsupported_assets table is present in the database
        assert table_exists(
            cursor=cursor,
            name='location_unsupported_assets',
            schema=DB_CREATE_LOCATION_UNSUPPORTED_ASSETS,
        ) is True

        # check that correct number of exchanges mappings are present.
        # exact values can be tested by pasting this gist here and running it
        # https://gist.github.com/OjusWiZard/0a9544ac4e985be08736cc3296e3e0d3
        for exchange, expected_mappings_count in (
            (None, 33),
            (Location.KRAKEN.serialize_for_db(), 228),
            (Location.POLONIEX.serialize_for_db(), 147),
            (Location.BITTREX.serialize_for_db(), 121),
            (Location.BINANCE.serialize_for_db(), 135),
            (Location.COINBASE.serialize_for_db(), 78),
            (Location.COINBASEPRO.serialize_for_db(), 82),
            (Location.GEMINI.serialize_for_db(), 26),
            (Location.CRYPTOCOM.serialize_for_db(), 0),
            (Location.BITSTAMP.serialize_for_db(), 16),
            (Location.BITFINEX.serialize_for_db(), 60),
            (Location.ICONOMI.serialize_for_db(), 36),
            (Location.KUCOIN.serialize_for_db(), 233),
            (Location.FTX.serialize_for_db(), 45),
            (Location.NEXO.serialize_for_db(), 2),
            (Location.BLOCKFI.serialize_for_db(), 5),
            (Location.UPHOLD.serialize_for_db(), 37),
            (Location.BITPANDA.serialize_for_db(), 41),
            (Location.OKX.serialize_for_db(), 65),
            (Location.WOO.serialize_for_db(), 32),
            (Location.BYBIT.serialize_for_db(), 78),
        ):
            assert cursor.execute(
                'SELECT COUNT(*) FROM location_asset_mappings WHERE location IS ?', (exchange,),
            ).fetchone()[0] == expected_mappings_count

        # check that correct number of unsupported assets are present.
        # exact values can be tested by pasting this gist here and running it
        # https://gist.github.com/OjusWiZard/0a9544ac4e985be08736cc3296e3e0d3
        for location, expected_mappings_count in (
            (Location.BINANCE.serialize_for_db(), 22),
            (Location.BITFINEX.serialize_for_db(), 10),
            (Location.BITTREX.serialize_for_db(), 125),
            (Location.FTX.serialize_for_db(), 65),
            (Location.GEMINI.serialize_for_db(), 10),
            (Location.ICONOMI.serialize_for_db(), 4),
            (Location.KUCOIN.serialize_for_db(), 234),
            (Location.OKX.serialize_for_db(), 7),
            (Location.POLONIEX.serialize_for_db(), 133),
        ):
            assert cursor.execute(
                'SELECT COUNT(*) FROM location_unsupported_assets WHERE location = ?', (location,),
            ).fetchone()[0] == expected_mappings_count


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v7_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [7])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v7_v8(globaldb: GlobalDBHandler, messages_aggregator, database):
    """Test the global DB upgrade from v7 to v8"""
    # Check the state before upgrading
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT protocol from evm_tokens where identifier=?',
            ('eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b',),
        ).fetchone()[0] == 'spam'
        assert cursor.execute(
            'SELECT COUNT(*) from general_cache where key=? AND value=?',
            ('SPAM_ASSET_FALSE_POSITIVE', 'eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b'),  # noqa: E501
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM contract_data WHERE address=?',
            ('0xAB392016859663Ce1267f8f243f9F2C02d93bad8',),
        ).fetchone()[0] == 1

        # check that asset asset_collections table have duplicated entries
        unique_entries = {}
        duplicated_entries = set()
        for collection_id, name, symbol in cursor.execute('SELECT id, name, symbol FROM asset_collections;'):  # noqa: E501
            if (name, symbol) not in unique_entries:
                unique_entries[name, symbol] = collection_id
            else:
                duplicated_entries.add((collection_id, name, symbol))

        v7_multiasset_mappings = cursor.execute(
            'SELECT rowid, collection_id, asset FROM multiasset_mappings;',
        ).fetchall()

        cached_lp_tokens = set(cursor.execute("SELECT value FROM general_cache WHERE key LIKE 'CURVE_LP_TOKENS%'").fetchall())  # noqa: E501
        cached_pool_tokens = set(cursor.execute("SELECT value FROM general_cache WHERE key LIKE 'CURVE_POOL_TOKENS%'").fetchall())  # noqa: E501
        cached_underlying_tokens = set(cursor.execute("SELECT value FROM general_cache WHERE key LIKE 'CURVE_POOL_UNDERLYING_TOKENS%'").fetchall())  # noqa: E501
        cached_gauges = set(cursor.execute("SELECT value FROM unique_cache WHERE key LIKE 'CURVE_GAUGE_ADDRESS%'").fetchall())  # noqa: E501
        cached_pools = set(cursor.execute("SELECT value FROM unique_cache WHERE key LIKE 'CURVE_POOL_ADDRESS%'").fetchall())  # noqa: E501

        assert len(cached_lp_tokens) == 973
        assert len(cached_pool_tokens) == 555
        assert len(cached_underlying_tokens) == 202
        assert len(cached_gauges) == 536
        assert len(cached_pools) == 973

        # cache with new keys doesn't exist yet
        assert cursor.execute("SELECT COUNT(*) FROM general_cache WHERE key LIKE 'CURVE_LP_TOKENS1%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM general_cache WHERE key LIKE 'CURVE_POOL_TOKENS1%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'CURVE_GAUGE_ADDRESS1%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'CURVE_POOL_ADDRESS1%'").fetchone()[0] == 0  # noqa: E501

        # before update, the cache is not eligible to refresh, because last_queried_ts is ts_now()
        cursor.execute('UPDATE general_cache SET last_queried_ts=? WHERE key LIKE ?', (ts_now(), 'CURVE_LP_TOKENS%'))  # noqa: E501
        assert should_update_protocol_cache(database, CacheType.CURVE_LP_TOKENS) is False

    assert unique_entries['Wormhole Token', 'W'] == 263
    assert unique_entries['TokenFi', 'TOKEN'] == 264
    assert unique_entries['HTX', 'HTX'] == 265
    assert unique_entries['Kyber Network Crystal v2', 'KNC'] == 301
    assert unique_entries['PancakeSwap Token', 'CAKE'] == 302
    assert (262, 'Starknet', 'STRK') in duplicated_entries
    assert (303, 'Starknet', 'STRK') in duplicated_entries
    assert (304, 'Wormhole Token', 'W') in duplicated_entries
    assert (305, 'TokenFi', 'TOKEN') in duplicated_entries
    assert (306, 'HTX', 'HTX') in duplicated_entries

    # execute upgrade
    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 8)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )
    assert globaldb.get_setting_value('version', 0) == 8

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT protocol from evm_tokens where identifier=?',
            ('eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b',),
        ).fetchone()[0] is None
        assert cursor.execute(
            'SELECT COUNT(*) from general_cache where key=? AND value=?',
            ('SPAM_ASSET_FALSE_POSITIVE', 'eip155:1/erc20:0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b'),  # noqa: E501
        ).fetchone()[0] == 1

        # check that asset_collections have unique entries now with correctly mapped ids
        assert table_exists(
            cursor=cursor,
            name='asset_collections',
            schema="""CREATE TABLE IF NOT EXISTS asset_collections (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                UNIQUE(name, symbol))
            """,
        ) is True

        for collection_id, name, symbol in (
            (260, 'Moon App', 'APP'),
            (261, 'Starknet', 'STRK'),
            (262, 'Wormhole Token', 'W'),
            (263, 'TokenFi', 'TOKEN'),
            (264, 'HTX', 'HTX'),
            (300, 'Kyber Network Crystal v2', 'KNC'),
            (301, 'PancakeSwap Token', 'CAKE'),
        ):
            assert cursor.execute(
                'SELECT COUNT(*) FROM asset_collections WHERE id=? AND name=? AND symbol=?',
                (collection_id, name, symbol),
            ).fetchone()[0] == 1

        # and multiasset_mappings are exactly same
        assert v7_multiasset_mappings == cursor.execute(
            'SELECT rowid, collection_id, asset FROM multiasset_mappings;',
        ).fetchall()

        assert cursor.execute(
            'SELECT COUNT(*) FROM contract_data WHERE address=?',
            ('0xAB392016859663Ce1267f8f243f9F2C02d93bad8',),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM contract_data WHERE address=?',
            ('0xc97EE9490F4e3A3136A513DB38E3C7b47e69303B',),
        ).fetchone()[0] == 1

        # previous keys were deleted
        assert cursor.execute("SELECT COUNT(*) FROM general_cache WHERE key LIKE 'CURVE_LP_TOKENS0x%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM general_cache WHERE key LIKE 'CURVE_POOL_TOKENS0x%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'CURVE_GAUGE_ADDRESS0x%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'CURVE_POOL_ADDRESS0x%'").fetchone()[0] == 0  # noqa: E501

        # values are same as in v7 with key containing the chain id
        assert set(cursor.execute("SELECT value FROM general_cache WHERE key LIKE 'CURVE_LP_TOKENS1%'").fetchall()) == cached_lp_tokens  # noqa: E501
        assert set(cursor.execute("SELECT value FROM general_cache WHERE key LIKE 'CURVE_POOL_TOKENS1%'").fetchall()) == cached_pool_tokens  # noqa: E501
        assert set(cursor.execute("SELECT value FROM unique_cache WHERE key LIKE 'CURVE_GAUGE_ADDRESS1%'").fetchall()) == cached_gauges  # noqa: E501
        assert set(cursor.execute("SELECT value FROM unique_cache WHERE key LIKE 'CURVE_POOL_ADDRESS1%'").fetchall()) == cached_pools  # noqa: E501

        # CURVE_POOL_UNDERLYING_TOKENS should be deleted
        assert cursor.execute("SELECT COUNT(*) FROM general_cache WHERE key LIKE 'CURVE_POOL_UNDERLYING_TOKENS%'").fetchone()[0] == 0  # noqa: E501

        # ensure that now curve cache should be eligible to update
        assert should_update_protocol_cache(database, CacheType.CURVE_LP_TOKENS, '1') is True

    with (
        pytest.raises(IntegrityError),
        globaldb.conn.write_ctx() as write_cursor,
    ):
        write_cursor.execute(
            "INSERT INTO contract_abi(id, value, name) SELECT 100, value, 'yabir' FROM contract_abi WHERE id=1",  # noqa: E501
        )  # test that raises unique error when trying to copy an existing abi


@pytest.mark.parametrize('custom_globaldb', ['v8_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [8])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v8_v9(globaldb: GlobalDBHandler, messages_aggregator):
    """We use version 8 of the globaldb at 1.34.3 and we set the
    target_globaldb_version to version 8 to avoid an automatic update of the globaldb
    and insert some data in it before updating to v9.
    """
    bad_address, tether_address = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'  # noqa: E501
    inserted_rows = [
        (bad_address, 'yabir.eth', None),
        (bad_address, 'yabirgb.eth', None),
        (tether_address, 'Black Tether', None),
    ]
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO address_book (address, name, blockchain) VALUES (?, ?, ?)',
            inserted_rows,
        )
        write_cursor.execute(
            "INSERT OR REPLACE INTO general_cache ('key', 'value', 'last_queried_ts') "
            "VALUES (?, ?, ?);",
            ('CURVE_LP_TOKENS1', '0xEd4064f376cB8d68F770FB1Ff088a3d0F3FF5c4d', 0),
        )  # entry to ensure that cache with wrong entries gets cleared correctly
        write_cursor.execute(
            'INSERT INTO underlying_tokens_list (identifier, parent_token_entry, weight) VALUES (?, ?, ?)',  # noqa: E501
            (A_USDT.identifier, A_USDT.identifier, 1),
        )
        write_cursor.execute(
            'INSERT INTO underlying_tokens_list (identifier, parent_token_entry, weight) VALUES (?, ?, ?)',  # noqa: E501
            (A_PAX.identifier, A_PAX.identifier, 1),
        )

    with globaldb.conn.read_ctx() as cursor:  # check we have the wrong case of an underlying token with itself as underlying in the Global DB before the upgrade  # noqa: E501
        underlying_count_before = cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list',
        ).fetchone()[0]
        assert cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE identifier=parent_token_entry',
        ).fetchone()[0] == 2

    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 9)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 9
    with globaldb.conn.read_ctx() as cursor:
        assert table_exists(
            cursor=cursor,
            name='address_book',
            schema="""
            CREATE TABLE IF NOT EXISTS address_book (
                address TEXT NOT NULL,
                blockchain TEXT NOT NULL,
                name TEXT NOT NULL,
                PRIMARY KEY(address, blockchain)
            );
            """,
        )
        assert cursor.execute(
            'SELECT * FROM address_book WHERE address IN (?, ?)',
            (bad_address, tether_address),
        ).fetchall() == [
            (tether_address, ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, 'Black Tether'),
            (bad_address, ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, 'yabirgb.eth'),
        ]
        assert len(cursor.execute(
            "SELECT * FROM price_history_source_types WHERE type IN ('G', 'H') AND seq IN (7, 8);",
        ).fetchall()) == 2
        assert cursor.execute(
            "SELECT last_queried_ts FROM general_cache WHERE key LIKE 'CURVE_LP_TOKENS%' "
            'ORDER BY last_queried_ts ASC LIMIT 2',
        ).fetchall() == [(1718795451,), (1718795451,)]
        assert cursor.execute(  # Check that the two underlying tokens that havethemselves as underlying have been removed  # noqa: E501
            'SELECT COUNT(*) FROM underlying_tokens_list',
        ).fetchone()[0] == underlying_count_before - 2
        assert cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE identifier=parent_token_entry',
        ).fetchone()[0] == 0


@pytest.mark.parametrize('custom_globaldb', ['v9_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [9])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v9_v10(globaldb: GlobalDBHandler, messages_aggregator):
    """Test upgrade from v9 to v10 which adds main_asset column to asset_collections"""
    with globaldb.conn.read_ctx() as cursor:
        assert not column_exists(
            cursor=cursor,
            table_name='asset_collections',
            column_name='main_asset',
        )
        # get all collection groups and their first assets before upgrade
        pre_upgrade_groups = cursor.execute("""
            SELECT collection_id, MIN(asset) as first_asset
            FROM multiasset_mappings
            GROUP BY collection_id
            ORDER BY collection_id
        """).fetchall()

        mappings_count = cursor.execute('SELECT COUNT(*) FROM multiasset_mappings').fetchone()[0]

    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 10)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 10

    with globaldb.conn.read_ctx() as cursor:
        assert column_exists(
            cursor=cursor,
            table_name='asset_collections',
            column_name='main_asset',
        )

        # verify number of mappings hasn't changed
        assert cursor.execute('SELECT COUNT(*) FROM multiasset_mappings').fetchone()[0] == mappings_count  # noqa: E501

        # verify each collection has its main asset properly set in asset_collections
        for collection_id, first_asset in pre_upgrade_groups:
            cursor.execute('SELECT main_asset FROM asset_collections WHERE id=?', (collection_id,))
            result = cursor.fetchone()
            if collection_id == 23:  # DAI special case
                assert result[0] == 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'
            else:
                assert result[0] == first_asset


@pytest.mark.parametrize('custom_globaldb', ['v10_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [10])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v10_v11(globaldb: GlobalDBHandler, messages_aggregator):
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM price_history_source_types WHERE seq = 9')
        assert cursor.fetchone()[0] == 0
        assert len(cursor.execute(
            'SELECT name FROM sqlite_master WHERE type="index" and sql IS NOT NULL',
        ).fetchall()) == 0
        assert cursor.execute("SELECT COUNT(*) FROM asset_types WHERE type IN ('S', 'X')").fetchone()[0] == 2  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE identifier IN ('BIDR', 'TEDDY')").fetchone()[0] == 2  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM common_asset_details WHERE identifier IN ('BIDR', 'TEDDY')").fetchone()[0] == 2  # noqa: E501
        # Make sure that non movable binance assets have their type changed
        assert cursor.execute("SELECT type FROM assets WHERE identifier='BVND'").fetchone()[0] == 'S'  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE identifier='eip155:56/erc20:0x0409633A72D846fc5BBe2f98D88564D35987904D'").fetchone()[0] == 0  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 11)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 11
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM price_history_source_types WHERE seq = 9')
        assert cursor.fetchone()[0] == 1
        assert cursor.execute(
            'SELECT name FROM sqlite_master WHERE type="index" and sql IS NOT NULL',
        ).fetchall() == [
            ('idx_assets_identifier',),
            ('idx_evm_tokens_identifier',),
            ('idx_multiasset_mappings_asset',),
            ('idx_asset_collections_main_asset',),
            ('idx_user_owned_assets_asset_id',),
            ('idx_common_assets_identifier',),
            ('idx_price_history_identifier',),
            ('idx_location_mappings_identifier',),
            ('idx_underlying_tokens_lists_identifier',),
            ('idx_binance_pairs_identifier',),
            ('idx_multiasset_mappings_identifier',),
        ]
        assert cursor.execute("SELECT COUNT(*) FROM asset_types WHERE type IN ('S', 'X')").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE identifier IN ('BIDR', 'TEDDY')").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM common_asset_details WHERE identifier IN ('BIDR', 'TEDDY')").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT type FROM assets WHERE identifier='BVND'").fetchone()[0] == 'W'  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE identifier='eip155:56/erc20:0x0409633A72D846fc5BBe2f98D88564D35987904D'").fetchone()[0] == 1  # noqa: E501
        assert cursor.execute("SELECT swapped_for FROM common_asset_details WHERE identifier='PHX'").fetchone()[0] == 'eip155:56/erc20:0x0409633A72D846fc5BBe2f98D88564D35987904D'  # noqa: E501


@pytest.mark.parametrize('custom_globaldb', ['v11_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [11])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v11_v12(globaldb: GlobalDBHandler, messages_aggregator):
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_POOL_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_ADDRESS.serialize(),
                CacheType.AERODROME_POOL_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_ADDRESS.serialize(),
            ),
        ).fetchone()[0] == 1914
        assert cursor.execute(
            'SELECT COUNT(*) FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_GAUGE_FEE_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_BRIBE_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_BRIBE_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_FEE_ADDRESS.serialize(),
            ),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT value, last_queried_ts FROM unique_cache WHERE key = ?',
            (CacheType.CURVE_LENDING_VAULTS.serialize(),),
        ).fetchone() == ('10000', 1741813725)
        assert cursor.execute(
            'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ? ESCAPE ?',
            ('CURVE\\_LENDING\\_VAULT\\_AMM%', '\\'),
        ).fetchone()[0] == 2
        assert cursor.execute(
            'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ? ESCAPE ?',
            ('CURVE\\_LENDING\\_VAULT\\_COLLATERAL\\_TOKEN%', '\\'),
        ).fetchone()[0] == 2
        assert table_exists(cursor=cursor, name='counterparty_asset_mappings') is False
        assert cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes').fetchone()[0] == 41
        assert {row[0] for row in cursor.execute('SELECT name FROM default_rpc_nodes WHERE endpoint=""')} == {  # noqa: E501
            'arbitrum one etherscan',
            'base etherscan',
            'bsc etherscan',
            'etherscan',
            'gnosis etherscan',
            'optimism etherscan',
            'polygon pos etherscan',
            'scroll etherscan',
        }

    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 12)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 12
    with globaldb.conn.read_ctx() as cursor:
        assert table_exists(cursor=cursor, name='counterparty_asset_mappings') is True
        assert cursor.execute(
            'SELECT COUNT(*) FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_POOL_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_ADDRESS.serialize(),
                CacheType.AERODROME_POOL_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_ADDRESS.serialize(),
            ),
        ).fetchone()[0] == 4420
        assert cursor.execute(
            'SELECT COUNT(*) FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_GAUGE_FEE_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_BRIBE_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_BRIBE_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_FEE_ADDRESS.serialize(),
            ),
        ).fetchone()[0] == 1194
        assert cursor.execute(
            'SELECT value, last_queried_ts FROM unique_cache WHERE key = ?',
            (CacheType.CURVE_LENDING_VAULTS.serialize(),),
        ).fetchone() == ('0', 0)
        assert cursor.execute(
            'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ? ESCAPE ?',
            ('CURVE\\_LENDING\\_VAULT\\_AMM%', '\\'),
        ).fetchone()[0] == 0
        assert cursor.execute(
            'SELECT COUNT(*) FROM unique_cache WHERE key LIKE ? ESCAPE ?',
            ('CURVE\\_LENDING\\_VAULT\\_COLLATERAL\\_TOKEN%', '\\'),
        ).fetchone()[0] == 0
        assert cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes').fetchone()[0] == 33
        assert cursor.execute(
            'SELECT COUNT(*) FROM default_rpc_nodes WHERE endpoint=""',
        ).fetchone()[0] == 0


@pytest.mark.parametrize('custom_globaldb', ['v12_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [12])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v12_v13(globaldb: GlobalDBHandler, messages_aggregator):
    with globaldb.conn.read_ctx() as cursor:
        assert table_exists(cursor=cursor, name='solana_tokens') is False
        assert index_exists(cursor=cursor, name='idx_solana_tokens_identifier') is False
        assert cursor.execute("SELECT COUNT(*) FROM token_kinds WHERE token_kind IN ('D', 'E')").fetchone()[0] == 0  # noqa: E501
        assert (solana_tokens_count := cursor.execute("SELECT COUNT(*) FROM assets WHERE type='Y'").fetchone()[0]) == 431  # noqa: E501
        assert cursor.execute("SELECT identifier, name FROM assets WHERE type='Y' LIMIT 10").fetchall() == [  # noqa: E501
            ('COPE', 'Cope'),
            ('FIDA', 'Bonfida'),
            ('HOLY', 'Holy Trinity'),
            ('RAY', 'Raydium'),
            ('MEDIA', 'Media Network'),
            ('STEP', 'Step Finance'),
            ('SNY', 'Synthetify Token'),
            ('MNGO', 'Mango'),
            ('MER-2', 'Mercurial'),
            ('ATLAS', 'Star Atlas'),
        ]
        assert (tokens_before := cursor.execute('SELECT COUNT(*) FROM assets').fetchone()[0]) == 12164  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM common_asset_details').fetchone()[0] == tokens_before  # noqa: E501
        assert cursor.execute('SELECT main_asset FROM asset_collections WHERE id IN (500, 501, 502) ORDER BY id').fetchall() == [  # noqa: E501
            ('COPE',),
            ('RAY',),
            ('MNGO',),
        ]
        assert cursor.execute('SELECT asset FROM multiasset_mappings WHERE collection_id IN (500, 501, 502) ORDER BY collection_id').fetchall() == [  # noqa: E501
            ('COPE',),
            ('RAY',),
            ('MNGO',),
        ]
        assert cursor.execute('SELECT * FROM user_owned_assets').fetchall() == [
            ('COPE',),
            ('RAY',),
            ('MNGO',),
        ]
        assert cursor.execute('SELECT from_asset, to_asset FROM price_history').fetchall() == [
            ('COPE', 'USD'),
            ('MNGO', 'ETH'),
            ('USD', 'RAY'),
        ]
        assert cursor.execute("SELECT exchange_symbol, local_id FROM location_asset_mappings WHERE exchange_symbol IN ('TRISIG', 'TRUMPSOL')").fetchall() == [  # noqa: E501
            ('TRISIG', 'TRISIG'),
            ('TRUMPSOL', 'TRUMP'),
            ('TRISIG', 'TRISIG'),
        ]
        assert cursor.execute("SELECT symbol, local_id FROM counterparty_asset_mappings WHERE symbol IN ('BONK', 'WIF', 'POPCAT')").fetchall() == [  # noqa: E501
            ('BONK', 'BONK'),
            ('WIF', 'WIF'),
            ('POPCAT', 'POPCAT'),
        ]
        assert cursor.execute('SELECT base_asset, quote_asset FROM binance_pairs').fetchall() == [
            ('COPE', 'USDT'),
            ('MNGO', 'USDT'),
            ('RAY', 'BUSD'),
        ]
        assert cursor.execute("SELECT identifier, name FROM assets WHERE type='Y' AND identifier IN ('HODLER','LAND','LEMON')").fetchall() == (user_added_tokens_before := [  # tokens that were added manually  # noqa: E501
            ('HODLER', 'The Little Hodler'),
            ('LAND', 'The Real Goal'),
            ('LEMON', 'Dog Stolen From Tesla'),
        ])
        assert table_exists(cursor=cursor, name='user_added_solana_tokens') is False

        protocol_mapping = {
            'aerodrome_pool': 'aerodrome',
            'velodrome_pool': 'velodrome',
            'pickle_jar': 'pickle finance',
            'SLP': 'sushiswap-v2',
            'UNI-V2': 'uniswap-v2',
            'UNI-V3': 'uniswap-v3',
            'yearn_vaults_v1': 'yearn-v1',
            'yearn_vaults_v2': 'yearn-v2',
            'yearn_vaults_v3': 'yearn-v3',
            'curve_pool': 'curve',
            'curve_lending_vaults': 'curve',
            'pendle': 'pendle',
            'hop_lp': 'hop',
            'morpho_vaults': 'morpho',
        }
        # Check that protocol names are still in old format before upgrade
        assert (protocol_tokens_count := cursor.execute(
            f"SELECT COUNT(*) FROM evm_tokens WHERE protocol IN ({','.join(['?' for _ in protocol_mapping])})",  # noqa: E501
            tuple(protocol_mapping),
        ).fetchone()[0]) > 0

    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 13)
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 13
    with globaldb.conn.read_ctx() as cursor:
        assert table_exists(cursor=cursor, name='solana_tokens') is True
        assert index_exists(cursor=cursor, name='idx_solana_tokens_identifier') is True
        assert cursor.execute("SELECT COUNT(*) FROM token_kinds WHERE token_kind IN ('D', 'E')").fetchone()[0] == 2  # noqa: E501
        assert cursor.execute("SELECT identifier, name FROM assets WHERE type='Y' LIMIT 10").fetchall() == [  # noqa: E501
            (cope_identifier := 'solana/token:8HGyAAB1yoM1ttS7pXjHMa3dukTFGQggnFFH3hJZgzQh', 'Cope'),  # noqa: E501
            ('solana/token:EchesyfXePKdLtoiZSL8pBe8Myagyy8ZRqsACNCFGnvp', 'Bonfida'),
            ('solana/token:3GECTP7H4Tww3w8jEPJCJtXUtXxiZty31S9szs84CcwQ', 'Holy Trinity'),
            (raydium_identifier := 'solana/token:4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R', 'Raydium'),  # noqa: E501
            ('solana/token:ETAtLmCmsoiEEKfNrHKJ2kYy3MoABhU6NQvpSfij5tDs', 'Media Network'),
            ('solana/token:StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT', 'Step Finance'),
            ('solana/token:4dmKkXNHdgYsXqBHCuMikNQWwVomZURhYvkkX5c4pQ7y', 'Synthetify Token'),
            (mango_identifier := 'solana/token:MangoCzJ36AjZyKwVj3VnYU4GTonjfVEnJmvvWaxLac', 'Mango'),  # noqa: E501
            ('solana/token:MERt85fc5boKw3BW1eYdxonEuJNvXbiMbs6hvheau5K', 'Mercurial'),
            ('solana/token:ATLASXmbPQxBUYbxPsV97usA3fPQYEqzQBUHgiFCUsXx', 'Star Atlas'),
        ]
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE identifier IN ('HODLSOL','TRISIG')").fetchone()[0] == 0  # noqa: E501
        # solana_tokens count reduced by 5: 2 duplicates removed + 3 user-added tokens migrated to AssetType.OTHER i.e. 'W'  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM solana_tokens').fetchone()[0] == solana_tokens_count - 5  # noqa: E501
        # token count reduced by 2 due to removal of duplicate HODLSOL and TRISIG entries
        assert cursor.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == tokens_before - 2
        assert cursor.execute('SELECT COUNT(*) FROM common_asset_details').fetchone()[0] == tokens_before - 2  # noqa: E501
        # Ensure all solana tokens have corresponding entries in the assets table
        assert cursor.execute('SELECT COUNT(*) FROM solana_tokens s LEFT JOIN assets a ON s.identifier = a.identifier WHERE a.identifier IS NULL').fetchone()[0] == 0  # noqa: E501
        # Ensure all solana tokens have corresponding entries in the common_asset_details table
        assert cursor.execute('SELECT COUNT(*) FROM solana_tokens s LEFT JOIN common_asset_details c ON s.identifier = c.identifier WHERE c.identifier IS NULL').fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE type='Y' AND identifier NOT LIKE 'solana%'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT main_asset FROM asset_collections WHERE id IN (500, 501, 502) ORDER BY id').fetchall() == [  # noqa: E501
            (cope_identifier,),
            (raydium_identifier,),
            (mango_identifier,),
        ]
        assert cursor.execute('SELECT asset FROM multiasset_mappings WHERE collection_id IN (500, 501, 502) ORDER BY collection_id').fetchall() == [  # noqa: E501
            (cope_identifier,),
            (raydium_identifier,),
            (mango_identifier,),
        ]
        assert cursor.execute('SELECT * FROM user_owned_assets').fetchall() == [
            (cope_identifier,),
            (raydium_identifier,),
            (mango_identifier,),
        ]
        assert cursor.execute('SELECT from_asset, to_asset FROM price_history').fetchall() == [
            (cope_identifier, 'USD'),
            (mango_identifier, 'ETH'),
            ('USD', raydium_identifier),
        ]
        assert cursor.execute("SELECT exchange_symbol, local_id FROM location_asset_mappings WHERE exchange_symbol IN ('TRISIG', 'TRUMPSOL')").fetchall() == [  # noqa: E501
            ('TRISIG', trisig_sol_identifier := 'solana/token:BLDiYcvm3CLcgZ7XUBPgz6idSAkNmWY6MBbm8Xpjpump'),  # noqa: E501
            ('TRUMPSOL', 'solana/token:6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN'),
            ('TRISIG', trisig_sol_identifier),
        ]
        assert cursor.execute("SELECT symbol, local_id FROM counterparty_asset_mappings WHERE symbol IN ('BONK', 'WIF', 'POPCAT')").fetchall() == [  # noqa: E501
            ('BONK', 'solana/token:DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'),
            ('WIF', 'solana/token:EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm'),
            ('POPCAT', 'solana/token:7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr'),
        ]
        assert cursor.execute('SELECT base_asset, quote_asset FROM binance_pairs').fetchall() == [
            (raydium_identifier, 'BUSD'),
            (cope_identifier, 'USDT'),
            (mango_identifier, 'USDT'),
        ]
        # check that the temporary table was created and the assets' type changed.
        assert table_exists(cursor=cursor, name='user_added_solana_tokens') is True
        assert cursor.execute("SELECT COUNT(*) FROM assets WHERE type='Y' AND identifier IN ('HODLER','LAND','LEMON')").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT identifier, name FROM assets WHERE type='W' AND identifier IN ('HODLER','LAND','LEMON')").fetchall() == user_added_tokens_before  # noqa: E501

        # verify that old protocol names are gone and new counterparty identifiers are present
        for protocols, expected_count in (
            (protocol_mapping, 0),
            (protocol_mapping.values(), protocol_tokens_count),
        ):
            assert cursor.execute(
                f"SELECT COUNT(*) FROM evm_tokens WHERE protocol IN ({','.join(['?' for _ in protocols])})",  # noqa: E501
                tuple(protocols),
            ).fetchone()[0] == expected_count


@pytest.mark.parametrize('custom_globaldb', ['v2_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_unfinished_upgrades(globaldb: GlobalDBHandler, messages_aggregator):
    assert globaldb.used_backup is False
    globaldb.add_setting_value(  # Pretend that an upgrade was started
        name='ongoing_upgrade_from_version',
        value=2,
    )
    # There are no backups, so it is supposed to raise an error
    with pytest.raises(DBUpgradeError):
        create_globaldb(globaldb._data_directory, 0, messages_aggregator)

    globaldb.conn.execute('PRAGMA wal_checkpoint;')  # flush the wal file

    # Add a backup
    backup_path = globaldb._data_directory / GLOBALDIR_NAME / f'{ts_now()}_global_db_v2.backup'  # type: ignore  # _data_directory is definitely not null here
    shutil.copy(Path(__file__).parent.parent.parent / 'data' / 'v2_global.db', backup_path)
    backup_connection = DBConnection(
        path=str(backup_path),
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    with backup_connection.write_ctx() as write_cursor:
        write_cursor.execute("INSERT INTO settings VALUES('is_backup', 'Yes')")  # mark as a backup  # noqa: E501
    backup_connection.close()

    globaldb = create_globaldb(globaldb._data_directory, 0, messages_aggregator)  # Now the backup should be used  # noqa: E501
    assert globaldb.used_backup is True
    # Check that there is no setting left
    assert globaldb.get_setting_value('ongoing_upgrade_from_version', -1) == -1
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT value FROM settings WHERE name=?', ('is_backup',)).fetchone()[0] == 'Yes'  # noqa: E501
    globaldb.cleanup()


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v2_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_applying_all_upgrade(globaldb: GlobalDBHandler, messages_aggregator):
    """Test globalDB upgrade from v2 to latest"""
    # Check the state before upgrading
    assert globaldb.get_setting_value('version', 0) == 2
    maybe_upgrade_globaldb(
        connection=globaldb.conn,
        global_dir=globaldb._data_directory / GLOBALDIR_NAME,  # type: ignore
        db_filename=GLOBALDB_NAME,
        msg_aggregator=messages_aggregator,
    )
    assert globaldb.get_setting_value('version', 0) == GLOBAL_DB_VERSION


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('custom_globaldb', ['v4_global.db'])
@pytest.mark.parametrize('target_globaldb_version', [4])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_assets_updates_applied_before_v10_change(globaldb, messages_aggregator):
    """Test that asset updates v17-31 are applied before db schema v10.

    Schema v10 adds the main_asset column which prevents pulling additional
    asset updates. This ensures compatible updates are applied first.
    """
    with globaldb.conn.read_ctx() as cursor:
        assert not column_exists(  # breaking schema change not present.
            cursor=cursor,
            table_name='asset_collections',
            column_name='main_asset',
        )

        # see that certain assets are not present in the db.
        rocket_pool_asset = 'eip155:1/erc20:0xD33526068D116cE69F19A9ee46F0bd304F21A51f'  # from update 24.  # noqa: E501
        compound_usdt_asset = 'eip155:1/erc20:0x3Afdc9BCA9213A35503b077a6072F3D0d5AB0840'  # from update 29  # noqa: E501
        morpho_asset = 'eip155:1/erc20:0x58D97B57BB95320F9a05dC918Aef65434969c2B2'  # from update 31  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier IN (?, ?, ?)', (rocket_pool_asset, compound_usdt_asset, morpho_asset)).fetchone()[0] == 0  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_upgrade_to(stack, 10)
        maybe_upgrade_globaldb(
            globaldb=globaldb,
            connection=globaldb.conn,
            global_dir=globaldb._data_directory / GLOBALDIR_NAME,
            db_filename=GLOBALDB_NAME,
            msg_aggregator=messages_aggregator,
        )

    assert globaldb.get_setting_value('version', 0) == 10
    with globaldb.conn.read_ctx() as cursor:
        assert column_exists(
            cursor=cursor,
            table_name='asset_collections',
            column_name='main_asset',
        )
        # see that said assets are now present in the db
        assert cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier IN (?, ?, ?)', (rocket_pool_asset, compound_usdt_asset, morpho_asset)).fetchone()[0] == 3  # noqa: E501
