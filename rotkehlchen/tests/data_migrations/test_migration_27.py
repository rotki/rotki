"""Test for data migration 27 - cleanup of defunct Loopring module settings."""
import json

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.tests.utils.factories import make_evm_address


@pytest.mark.parametrize('data_migration_version', [26])
def test_migration_27_remove_loopring_module_settings(database: DBHandler) -> None:
    """Loopring tracking settings and cached account id mappings are removed."""
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('active_modules', json.dumps(['uniswap', 'loopring', 'eth2'])),
        )
        write_cursor.executemany(
            'INSERT INTO multisettings(name, value) VALUES(?, ?)',
            [
                ('queried_address_loopring', make_evm_address()),
                ('loopring_0xfoo_account_id', '42'),
                ('queried_address_uniswap', make_evm_address()),
            ],
        )
        write_cursor.execute(
            'INSERT INTO external_service_credentials(name, api_key, api_secret) '
            'VALUES(?, ?, ?)',
            ('loopring', 'loopring-api-key', None),
        )

    run_single_migration(database=database, migration=27)

    with database.conn.read_ctx() as cursor:
        assert json.loads(cursor.execute(
            "SELECT value FROM settings WHERE name='active_modules'",
        ).fetchone()[0]) == ['uniswap', 'eth2']
        assert cursor.execute(
            "SELECT name FROM multisettings WHERE name='queried_address_loopring'",
        ).fetchall() == []
        assert cursor.execute(
            "SELECT COUNT(*) FROM multisettings WHERE name='loopring_0xfoo_account_id'",
        ).fetchone()[0] == 0
        assert cursor.execute(
            "SELECT COUNT(*) FROM external_service_credentials WHERE name='loopring'",
        ).fetchone()[0] == 0
        assert cursor.execute(
            "SELECT COUNT(*) FROM multisettings WHERE name='queried_address_uniswap'",
        ).fetchone()[0] == 1
