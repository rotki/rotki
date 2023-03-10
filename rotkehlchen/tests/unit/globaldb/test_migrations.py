import json
from contextlib import ExitStack

import pytest

from rotkehlchen.globaldb.migrations.manager import (
    MIGRATIONS_LIST,
    maybe_apply_globaldb_migrations,
)
from rotkehlchen.globaldb.migrations.migration1 import ILK_REGISTRY_ABI, ilk_mapping
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_migrations


@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_migration1(globaldb):
    """Test for the 1st globalDB data migration"""
    # Check state before migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', None) == 5
        assert globaldb.get_setting_value('last_data_migration', None) is None
        assert globaldb.get_setting_value('last_assets_json_version', None) == 72
        assert cursor.execute('SELECT COUNT(*) FROM contract_abi').fetchone()[0] == 66
        assert cursor.execute('SELECT COUNT(*) FROM contract_abi WHERE name="ILK_REGISTRY"').fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM contract_data').fetchone()[0] == 97
        assert cursor.execute('SELECT COUNT(*) FROM general_cache WHERE key LIKE "MAKERDAO_VAULT_ILK%"').fetchone()[0] == 0  # noqa: E501

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[0]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    # assert state is correct after migration
    with globaldb.conn.read_ctx() as cursor:
        assert globaldb.get_setting_value('version', None) == 5
        assert globaldb.get_setting_value('last_assets_json_version', None) is None
        assert globaldb.get_setting_value('last_data_migration', None) == 1
        assert cursor.execute('SELECT COUNT(*) FROM contract_abi').fetchone()[0] == 67
        ilk_abi_id, ilk_abi_value = cursor.execute('SELECT id, value FROM contract_abi WHERE name="ILK_REGISTRY"').fetchone()  # noqa: E501
        assert ilk_abi_value == ILK_REGISTRY_ABI
        assert cursor.execute('SELECT COUNT(*) FROM contract_data').fetchone()[0] == 98
        cursor.execute('SELECT abi, address, deployed_block FROM contract_data WHERE name="ILK_REGISTRY"')  # noqa: E501
        assert cursor.fetchone() == (ilk_abi_id, '0x5a464C28D19848f44199D003BeF5ecc87d090F87', 12251871)  # noqa: E501

        assert cursor.execute('SELECT COUNT(*) FROM general_cache WHERE key LIKE "MAKERDAO_VAULT_ILK%"').fetchone()[0] == 25  # noqa: E501

        for ilk, info in ilk_mapping.items():
            cursor.execute(
                'SELECT value FROM general_cache WHERE KEY=?',
                (f'MAKERDAO_VAULT_ILK{ilk}',),
            )
            assert json.loads(cursor.fetchone()[0]) == list(info)
