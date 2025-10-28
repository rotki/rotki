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
@pytest.mark.parametrize('custom_globaldb', ['v14_global.db'])
def test_migration3_updates_address_book(globaldb: 'GlobalDBHandler') -> None:
    """Test that migration 3 replaces 'NONE' with ecosystem key in address_book"""
    evm_addr = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'
    eth_addr = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
    polkadot_addr = '12uFGYC47mG8PCjyT9DrBW4HkhPYuREcii2ao5YPYQQsdgK7'
    bitcoin_addr = 'bc1qnpme4ak6rs9nhustupr6rdhrfydtnytezt86aa'

    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute('DELETE FROM address_book')
        write_cursor.executemany(
            'INSERT OR REPLACE INTO address_book(address, blockchain, name) VALUES(?, ?, ?)',
            [
                (eth_addr, 'ETH', 'yabir.eth'),
                (evm_addr, 'NONE', 'Bitfinex'),
                (polkadot_addr, 'NONE', 'SUBSTRATE'),
                (bitcoin_addr, 'NONE', 'saylor'),
                ('0xcde6dbe01902be1f200ff03dbbd149e586847be8cee15235f82750d9b06c0e04', 'NONE', 'My sui address'),  # noqa: E501
            ],
        )

    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[2]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    with globaldb.conn.read_ctx() as cursor:
        rows = list(cursor.execute('SELECT address, blockchain, name FROM address_book ORDER BY blockchain').fetchall())  # noqa: E501
        assert rows == [
            (eth_addr, 'ETH', 'yabir.eth'),
            (bitcoin_addr, 'TYPE_BITCOIN', 'saylor'),
            (evm_addr, 'TYPE_EVMLIKE', 'Bitfinex'),
            (polkadot_addr, 'TYPE_SUBSTRATE', 'SUBSTRATE'),
        ]
