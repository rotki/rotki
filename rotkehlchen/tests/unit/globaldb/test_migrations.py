import json
from contextlib import ExitStack
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.globaldb.migrations.manager import (
    MIGRATIONS_LIST,
    maybe_apply_globaldb_migrations,
)
from rotkehlchen.globaldb.migrations.migration1 import ilk_mapping
from rotkehlchen.globaldb.utils import GLOBAL_DB_VERSION
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_migrations
from rotkehlchen.types import CacheType

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_migration1(globaldb: 'GlobalDBHandler'):
    """Test for the 1st globalDB data migration"""
    # Check state before migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', -1) == GLOBAL_DB_VERSION
        assert globaldb.get_setting_value('last_data_migration', -1) == -1
        assert globaldb.get_setting_value('last_assets_json_version', -1) == 72
        assert cursor.execute("SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'MAKERDAO_VAULT_ILK%'").fetchone()[0] == 0  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[0]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    # assert state is correct after migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', -1) == GLOBAL_DB_VERSION
        assert globaldb.get_setting_value('last_assets_json_version', -1) == -1
        assert globaldb.get_setting_value('last_data_migration', -1) == 1
        assert cursor.execute("SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'MAKERDAO_VAULT_ILK%'").fetchone()[0] == 25  # noqa: E501

        for ilk, info in ilk_mapping.items():
            cursor.execute(
                'SELECT value FROM unique_cache WHERE KEY=?',
                (f'MAKERDAO_VAULT_ILK{ilk}',),
            )
            assert json.loads(cursor.fetchone()[0]) == list(info)


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v8_global.db'])
def test_migration2(globaldb: 'GlobalDBHandler'):
    """Test for the 1st globalDB data migration"""
    # Check state before migration
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT value FROM unique_cache WHERE key=?', ('YEARN_VAULTS',)).fetchone()[0] == '179'  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[1]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT value FROM unique_cache WHERE key=?', ('YEARN_VAULTS',)).fetchone() is None  # noqa: E501


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v9_global.db'])
def test_migration3(globaldb: 'GlobalDBHandler'):
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

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[2]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_POOL_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_ADDRESS.serialize(),
                CacheType.AERODROME_POOL_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_ADDRESS.serialize(),
            ),
        ).fetchone()[0] == 0
