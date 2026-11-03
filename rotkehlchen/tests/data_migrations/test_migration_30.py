"""Test data migration 30, which schedules recovery of skipped Solana v1 transactions and
removes stale balance refresh times of disabled chains."""
import json
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
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


@pytest.mark.parametrize('data_migration_version', [29])
def test_migration_30_removes_query_ts_of_fully_disabled_chains(database: DBHandler) -> None:
    """Chains with no active address lose their timestamp, whether disabled entirely or with
    all their tracked addresses disabled. Chains with an enabled address keep it."""
    fully_disabled, all_addresses_disabled, partially_disabled, enabled = (
        SupportedBlockchain.ETHEREUM,
        SupportedBlockchain.GNOSIS,
        SupportedBlockchain.OPTIMISM,
        SupportedBlockchain.BITCOIN,
    )
    keys = {chain: DBCacheDynamic.LAST_BLOCKCHAIN_BALANCES_QUERY_TS.get_db_key(
        blockchain=chain.serialize(),
    ) for chain in (fully_disabled, all_addresses_disabled, partially_disabled, enabled)}
    addresses = ('0x9531C059098e3d194fF87FebB587aB07B30B1306', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c')  # noqa: E501
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('disabled_chain_queries', json.dumps({
                fully_disabled.serialize(): [],
                all_addresses_disabled.serialize(): list(addresses),
                partially_disabled.serialize(): [addresses[0]],
            })),
        )
        write_cursor.executemany(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES(?, ?)',
            [(chain.value, address) for chain in (all_addresses_disabled, partially_disabled) for address in addresses],  # noqa: E501
        )
        write_cursor.executemany(
            'INSERT INTO key_value_cache(name, value) VALUES(?, ?)',
            [(key, 1) for key in keys.values()],
        )

    run_single_migration(database=database, migration=30)

    with database.conn.read_ctx() as cursor:
        assert {row[0] for row in cursor.execute(
            "SELECT name FROM key_value_cache WHERE name LIKE '%_last_balances_query_ts'",
        )} == {keys[partially_disabled], keys[enabled]}


@pytest.mark.parametrize('data_migration_version', [29])
@pytest.mark.parametrize('disabled_validator_indices', [[], [0], [0, 1], [2]])
def test_migration_30_preserves_enabled_validators(
        database: DBHandler,
        disabled_validator_indices: list[int],
) -> None:
    """The migration uses validator public keys, not the empty ETH2 blockchain_accounts set."""
    chain = SupportedBlockchain.ETHEREUM_BEACONCHAIN
    pubkeys = [f'0x{index:096x}' for index in range(3)]
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('disabled_chain_queries', json.dumps({
                chain.serialize(): [pubkeys[index] for index in disabled_validator_indices],
            })),
        )
        write_cursor.executemany(
            'INSERT INTO eth2_validators(public_key, validator_type, ownership_proportion) '
            'VALUES(?, 0, ?)',
            [(pubkey, '1') for pubkey in pubkeys[:2]],
        )
        database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_BLOCKCHAIN_BALANCES_QUERY_TS,
            blockchain=chain.serialize(),
            value=1,
        )
        write_cursor.executemany(
            'INSERT INTO blockchain_balances_cache(blockchain, address, asset, label, category, amount) '  # noqa: E501
            'VALUES(?, ?, ?, ?, ?, ?)',
            [(chain.serialize(), pubkey, chain.get_native_token_id(), '', BalanceType.ASSET.serialize_for_db(), '32') for pubkey in pubkeys[:2]],  # noqa: E501
        )

    run_single_migration(database=database, migration=30)

    with database.conn.read_ctx() as cursor:
        should_preserve = disabled_validator_indices in ([0], [2])
        assert cursor.execute(
            'SELECT address, amount FROM blockchain_balances_cache WHERE blockchain=? ORDER BY address',  # noqa: E501
            (chain.serialize(),),
        ).fetchall() == ([(pubkey, '32') for pubkey in pubkeys[:2]] if should_preserve else [])
        assert cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            (DBCacheDynamic.LAST_BLOCKCHAIN_BALANCES_QUERY_TS.get_db_key(
                blockchain=chain.serialize(),
            ),),
        ).fetchone() == (('1',) if should_preserve else None)
