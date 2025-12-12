import uuid

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.types import Location


@pytest.mark.parametrize('data_migration_version', [21])
def test_migration_22_remove_coinbase_legacy_keys(database: DBHandler) -> None:
    """Test that migration 22 removes Coinbase legacy keys but doesn't touch ECDSA or ED25519 keys.
    Uses a uuid to simulate a valid ED25519 key.
    """
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO user_credentials (name, location, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?, ?)',  # noqa: E501
            [('Coinbase 1', Location.COINBASE.serialize_for_db(), 'BADKEY', None, None),
            ('Coinbase 2', Location.COINBASE.serialize_for_db(), str(uuid.uuid4()), None, None),
            ('Coinbase 3', Location.COINBASE.serialize_for_db(), f'organizations/{uuid.uuid4()!s}/apiKeys/{uuid.uuid4()!s}', None, None)],  # noqa: E501
        )

    run_single_migration(database=database, migration=22)
    with database.conn.read_ctx() as cursor:
        result = cursor.execute('SELECT name FROM user_credentials').fetchall()
        assert result == [('Coinbase 2',), ('Coinbase 3',)]
