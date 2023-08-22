import json
from contextlib import ExitStack

import pytest

from rotkehlchen.globaldb.migrations.manager import (
    MIGRATIONS_LIST,
    maybe_apply_globaldb_migrations,
)
from rotkehlchen.globaldb.migrations.migration1 import ilk_mapping
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_migrations


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_migration1(globaldb):
    """Test for the 1st globalDB data migration"""
    # Check state before migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', None) == 6
        assert globaldb.get_setting_value('last_data_migration', None) is None
        assert globaldb.get_setting_value('last_assets_json_version', None) == 72
        assert cursor.execute('SELECT COUNT(*) FROM unique_cache WHERE key LIKE "MAKERDAO_VAULT_ILK%"').fetchone()[0] == 0  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[0]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    # assert state is correct after migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', None) == 6
        assert globaldb.get_setting_value('last_assets_json_version', None) is None
        assert globaldb.get_setting_value('last_data_migration', None) == 1
        assert cursor.execute('SELECT COUNT(*) FROM unique_cache WHERE key LIKE "MAKERDAO_VAULT_ILK%"').fetchone()[0] == 25  # noqa: E501

        for ilk, info in ilk_mapping.items():
            cursor.execute(
                'SELECT value FROM unique_cache WHERE KEY=?',
                (f'MAKERDAO_VAULT_ILK{ilk}',),
            )
            assert json.loads(cursor.fetchone()[0]) == list(info)
