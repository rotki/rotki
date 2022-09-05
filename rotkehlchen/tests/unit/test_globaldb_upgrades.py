from pathlib import Path
from unittest.mock import patch

import pytest

from rotkehlchen.assets.types import AssetType
from rotkehlchen.globaldb.upgrades.manager import maybe_upgrade_globaldb
from rotkehlchen.globaldb.upgrades.v2_v3 import OTHER_EVM_CHAINS_ASSETS
from rotkehlchen.types import ChainID, EvmTokenKind

# TODO: Perhaps have a saved version of that global DB for the tests and query it too?
ASSETS_IN_V2_GLOBALDB = 3095


def _count_v2_v3_assets_inserted() -> int:
    """Counts and returns how many assets are to be inserted by globaldb_v2_v3_assets.sql"""
    assets_inserted_by_update = 0
    dir_path = Path(__file__).resolve().parent.parent.parent
    with open(dir_path / 'data' / 'globaldb_v2_v3_assets.sql', 'r') as f:
        line = ' '
        while line:
            line = f.readline()
            assets_inserted_by_update += 1
            if ';' in line:
                break

    return assets_inserted_by_update - 1


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('globaldb_version', [2])
@pytest.mark.parametrize('target_globaldb_version', [2])
@pytest.mark.parametrize('reload_user_assets', [False])
def test_upgrade_v2_v3(globaldb):
    """At the start of this test global DB is upgraded to v3"""
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
    with patch('rotkehlchen.globaldb.utils.GLOBAL_DB_VERSION', 2):
        maybe_upgrade_globaldb(
            connection=globaldb.conn,
            dbpath=globaldb._data_directory / 'global_data' / 'global.db',
        )

    assert globaldb.get_setting_value('version', None) == 3
    assets_inserted_by_update = _count_v2_v3_assets_inserted()
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
