"""Test data migration 30, which schedules recovery of skipped Solana v1 transactions."""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.solana.constants import SOLANA_V1_ACTIVATION_SLOT
from rotkehlchen.chain.solana.types import SolanaTransaction
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.tests.utils.factories import make_solana_address, make_solana_signature
from rotkehlchen.types import SolanaAddress, SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor


@pytest.mark.parametrize('data_migration_version', [29])
def test_migration_30_schedules_only_accounts_past_v1_activation(database: DBHandler) -> None:
    """Tracked accounts past the activation slot are marked, including activity via an ATA."""
    direct_account = make_solana_address()
    ata_account = make_solana_address()
    old_account = make_solana_address()
    empty_account = make_solana_address()
    untracked_account = make_solana_address()
    ata_address = make_solana_address()
    dbtx = DBSolanaTx(database)

    def add_transaction(
            write_cursor: DBCursor,
            relevant_address: SolanaAddress,
            slot: int,
    ) -> None:
        dbtx.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=[SolanaTransaction(
                fee=0,
                slot=slot,
                success=True,
                signature=make_solana_signature(),
                block_time=Timestamp(1),
                account_keys=[],
                instructions=[],
            )],
            relevant_address=relevant_address,
        )

    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES(?, ?)',
            [(SupportedBlockchain.SOLANA.value, account) for account in (
                direct_account,
                ata_account,
                old_account,
                empty_account,
            )],
        )
        write_cursor.execute(
            'INSERT INTO solana_ata_address_mappings(account, ata_address) VALUES(?, ?)',
            (ata_account, ata_address),
        )
        add_transaction(write_cursor, direct_account, SOLANA_V1_ACTIVATION_SLOT)
        add_transaction(write_cursor, ata_address, SOLANA_V1_ACTIVATION_SLOT + 1)
        add_transaction(write_cursor, old_account, SOLANA_V1_ACTIVATION_SLOT - 1)
        add_transaction(write_cursor, untracked_account, SOLANA_V1_ACTIVATION_SLOT + 1)

    run_single_migration(database=database, migration=30)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            "SELECT name, value FROM key_value_cache WHERE name LIKE 'solana_tx_backfill_from_slot_%' ORDER BY name",  # noqa: E501
        ).fetchall() == sorted([
            (
                DBCacheDynamic.SOLANA_TX_BACKFILL_FROM_SLOT.get_db_key(address=account),
                str(SOLANA_V1_ACTIVATION_SLOT),
            ) for account in (direct_account, ata_account)
        ])
