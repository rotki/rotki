import uuid
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.connections.types import ConnectorIdentifier
from rotkehlchen.db.connections import DBConnections
from rotkehlchen.locations.constants import (
    LOCATION_COINBASE,
)
from rotkehlchen.tests.data_migrations.test_migrations import (
    MockRotkiForMigrationsWithExchangeManager,
)
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.types import ApiKey, ApiSecret

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('data_migration_version', [21])
def test_migration_22_remove_coinbase_legacy_keys(database: DBHandler) -> None:
    """Test that migration 22 removes Coinbase legacy keys but doesn't touch ECDSA or ED25519 keys.
    Generates uuids to simulate valid keys in the proper formats. Doesn't include api secrets
    since they are not referenced in the migration.
    """
    with database.user_write() as write_cursor:
        for name, api_key in (
                ('Coinbase 1', 'BADKEY'),
                ('Coinbase 2', str(uuid.uuid4())),
                ('Coinbase 3', f'organizations/{uuid.uuid4()!s}/apiKeys/{uuid.uuid4()!s}'),
        ):
            DBConnections.add(write_cursor, name=name, connector=ConnectorIdentifier(LOCATION_COINBASE), location=LOCATION_COINBASE, api_key=ApiKey(api_key), api_secret=ApiSecret(b''))  # noqa: E501

    with (patch(
        target='rotkehlchen.tests.utils.data_migrations.MockRotkiForMigrations',
        new=MockRotkiForMigrationsWithExchangeManager,
    )):
        rotki = run_single_migration(database=database, migration=22)

    assert [x.name for x in rotki.exchange_manager.connected_exchanges[LOCATION_COINBASE]] == ['Coinbase 2', 'Coinbase 3']  # noqa: E501
    with database.conn.read_ctx() as cursor:
        result = cursor.execute('SELECT name FROM integration_connections ORDER BY name').fetchall()  # noqa: E501
        assert result == [('Coinbase 2',), ('Coinbase 3',)]


@pytest.mark.parametrize('data_migration_version', [21])
def test_migration_22_purge_eth_validators_data_cache(database: DBHandler) -> None:
    """Test that migration 22 purges eth_validators_data_cache only for accumulating validators."""
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO eth2_validators (validator_index, public_key, ownership_proportion, validator_type) VALUES (?, ?, ?, ?)',  # noqa: E501
            [
                (123, '0xabcd', '1.0', 2),
                ((non_accumulating_validator_index := 456), '0xefgh', '1.0', 1),
            ],
        )
        write_cursor.executemany(
            'INSERT INTO eth_validators_data_cache (validator_index, timestamp, balance, withdrawals_pnl, exit_pnl) VALUES (?, ?, ?, ?, ?)',  # noqa: E501
            [
                (123, 1700000000000, '32000000000', '100000000', '0'),
                (non_accumulating_validator_index, 1700000000000, '32000000000', '0', '0'),
            ],
        )

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM eth_validators_data_cache').fetchone()[0] == 2

    run_single_migration(database=database, migration=22)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT validator_index FROM eth_validators_data_cache').fetchall() == [(non_accumulating_validator_index,)]  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM eth2_validators').fetchone()[0] == 2
