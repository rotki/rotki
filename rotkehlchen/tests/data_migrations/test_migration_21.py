"""Test for data migration 21 - address_book NONE -> ecosystem key"""
from unittest.mock import patch

import pytest

from rotkehlchen.data_migrations.manager import MIGRATION_LIST, DataMigrationManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.data_migrations.test_migrations import MockRotkiForMigrations


@pytest.mark.parametrize('data_migration_version', [20])
def test_migration_21_address_book_chain_key(database: DBHandler) -> None:
    rotki = MockRotkiForMigrations(database)
    evm_addr = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'
    eth_addr = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
    polkadot_addr = '12uFGYC47mG8PCjyT9DrBW4HkhPYuREcii2ao5YPYQQsdgK7'
    bitcoin_addr = 'bc1qnpme4ak6rs9nhustupr6rdhrfydtnytezt86aa'

    with database.user_write() as write_cursor:
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

    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[-1]]):
        DataMigrationManager(rotki).maybe_migrate_data()

    with database.conn.read_ctx() as cursor:
        rows = list(cursor.execute('SELECT address, blockchain, name FROM address_book ORDER BY blockchain').fetchall())  # noqa: E501
        assert rows == [
            (eth_addr, 'ETH', 'yabir.eth'),
            (bitcoin_addr, 'TYPE_BITCOIN', 'saylor'),
            (evm_addr, 'TYPE_EVMLIKE', 'Bitfinex'),
            (polkadot_addr, 'TYPE_SUBSTRATE', 'SUBSTRATE'),
        ]
