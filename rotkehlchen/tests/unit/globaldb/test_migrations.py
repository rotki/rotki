import json
from contextlib import ExitStack

import pytest

from rotkehlchen.db.upgrades.v38_v39 import DEFAULT_ARBITRUM_ONE_NODES_AT_V39
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.migrations.manager import (
    MIGRATIONS_LIST,
    maybe_apply_globaldb_migrations,
)
from rotkehlchen.globaldb.migrations.migration1 import ilk_mapping
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_migrations


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_migration1(globaldb: GlobalDBHandler) -> None:
    """Test for the 1st globalDB data migration"""
    # Check state before migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 5
        assert globaldb.get_setting_value('last_data_migration', 0) is None
        assert globaldb.get_setting_value('last_assets_json_version', 0) == 72
        assert cursor.execute('SELECT COUNT(*) FROM general_cache WHERE key LIKE "MAKERDAO_VAULT_ILK%"').fetchone()[0] == 0  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[0]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    # assert state is correct after migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 5
        assert globaldb.get_setting_value('last_assets_json_version', 0) is None
        assert globaldb.get_setting_value('last_data_migration', 0) == 1
        assert cursor.execute('SELECT COUNT(*) FROM general_cache WHERE key LIKE "MAKERDAO_VAULT_ILK%"').fetchone()[0] == 25  # noqa: E501

        for ilk, info in ilk_mapping.items():
            cursor.execute(
                'SELECT value FROM general_cache WHERE KEY=?',
                (f'MAKERDAO_VAULT_ILK{ilk}',),
            )
            assert json.loads(cursor.fetchone()[0]) == list(info)


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['globaldb_as_1.29.1.db'])
def test_migration2(globaldb: GlobalDBHandler) -> None:
    """Test for the 1st globalDB data migration"""
    # Check state before migration
    with globaldb.conn.write_ctx() as write_cursor:
        assert globaldb.get_setting_value('version', 0) == 5
        assert write_cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE blockchain="ARBITRUM_ONE"').fetchone()[0] == 0  # noqa: E501
        # add one node to test that we don't add duplicates
        write_cursor.execute(
            'INSERT INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            DEFAULT_ARBITRUM_ONE_NODES_AT_V39[0],
        )

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[1]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    # assert state is correct after migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', 0) == 5
        # check that we don't have extra nodes
        assert cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE blockchain="ARBITRUM_ONE"').fetchone()[0] == 5  # noqa: E501
        endpoints = {row[0] for row in cursor.execute('SELECT endpoint FROM default_rpc_nodes').fetchall()}  # noqa: E501
        # check that we have the expected ones
        for entry in DEFAULT_ARBITRUM_ONE_NODES_AT_V39:
            assert entry[1] in endpoints
