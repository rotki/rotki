"""Test data migration 30, which schedules recovery of skipped Solana v1 transactions,
removes stale balance refresh times of disabled chains and resets Compound v3 native
collateral transactions for redecoding."""
import json
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.compound.v3.constants import CPT_COMPOUND_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.solana.constants import SOLANA_V1_ACTIVATION_SLOT
from rotkehlchen.chain.solana.types import SolanaTransaction
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_POL, A_WETH
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.chains import location_from_chain_id
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import (
    make_evm_address,
    make_evm_tx_hash,
    make_solana_address,
    make_solana_signature,
)
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    SolanaAddress,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
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
            value=Timestamp(1),
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


@pytest.mark.parametrize('data_migration_version', [29])
def test_migration_30_resets_compound_v3_native_collateral(database: DBHandler) -> None:
    """Compound v3 collateral deposits and withdrawals of the chain's native token are reset
    for redecoding, so they get the bulker's wrapping. Wrapped token collateral, native
    movements of other protocols and transactions with a customized event, whether the
    collateral event itself or a sibling, stay decoded with their events unmodified."""
    cases: list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, HistoryEventType, HistoryEventSubType, Asset, str, int | None, bool]] = [  # noqa: E501
        (ChainID.ETHEREUM, HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, A_ETH, CPT_COMPOUND_V3, None, True),  # noqa: E501
        (ChainID.BASE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL, A_ETH, CPT_COMPOUND_V3, None, True),  # noqa: E501
        (ChainID.POLYGON_POS, HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, A_POL, CPT_COMPOUND_V3, None, True),  # noqa: E501
        (ChainID.ETHEREUM, HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, A_WETH, CPT_COMPOUND_V3, None, False),  # noqa: E501
        (ChainID.ETHEREUM, HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, A_ETH, 'aave-v3', None, False),  # noqa: E501
        (ChainID.ETHEREUM, HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, A_ETH, CPT_COMPOUND_V3, 1, False),  # noqa: E501
        (ChainID.ETHEREUM, HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL, A_ETH, CPT_COMPOUND_V3, 0, False),  # noqa: E501
    ]
    transactions = [EvmTransaction(
        tx_hash=make_evm_tx_hash(),
        chain_id=chain_id,
        timestamp=Timestamp(1),
        block_number=1,
        from_address=make_evm_address(),
        to_address=None,
        value=0,
        gas=21000,
        gas_price=1,
        gas_used=21000,
        input_data=b'',
        nonce=0,
    ) for chain_id, *_ in cases]
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=transactions,
            relevant_address=None,
        )
        tx_ids = [write_cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx.tx_hash, tx.chain_id.serialize_for_db()),
        ).fetchone()[0] for tx in transactions]
        stored_events: list[list[EvmEvent]] = []
        for tx, tx_id, (chain_id, event_type, event_subtype, asset, counterparty, customized_index, _) in zip(transactions, tx_ids, cases, strict=True):  # noqa: E501
            stored_events.append(tx_events := [EvmEvent(
                tx_ref=tx.tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=(location := location_from_chain_id(chain_id)),
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                amount=FVal('1'),
                location_label=tx.from_address,
                notes='Edited by the user' if customized_index == 0 else None,
                counterparty=counterparty,
            ), EvmEvent(
                tx_ref=tx.tx_hash,
                sequence_index=1,
                timestamp=TimestampMS(1000),
                location=location,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=FVal('1'),
                location_label=tx.from_address,
            )])
            for sequence_index, event in enumerate(tx_events):
                event.identifier = dbevents.add_history_event(
                    write_cursor=write_cursor,
                    event=event,
                    mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if sequence_index == customized_index else None,  # noqa: E501
                )
            write_cursor.execute(
                'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, TX_DECODED),
            )

    run_single_migration(database=database, migration=30)

    with database.conn.read_ctx() as cursor:
        for tx, tx_id, tx_events, (*_, customized_index, reset) in zip(transactions, tx_ids, stored_events, cases, strict=True):  # noqa: E501
            assert cursor.execute(
                'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
                (tx_id, TX_DECODED),
            ).fetchone()[0] == int(not reset)
            assert dbevents.get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(tx_hashes=[tx.tx_hash]),
            ) == ([] if reset else tx_events)
            if customized_index is not None:  # the customized event keeps its state
                assert cursor.execute(
                    'SELECT value FROM history_events_mappings WHERE parent_identifier=? AND name=?',  # noqa: E501
                    (tx_events[customized_index].identifier, HISTORY_MAPPING_KEY_STATE),
                ).fetchall() == [(HistoryMappingState.CUSTOMIZED.serialize_for_db(),)]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('data_migration_version', [29])
@pytest.mark.parametrize('ethereum_accounts', [['0xD413dCf1b80E10a8Ba7Cab329DA7545cCc827319']])
def test_migration_30_redecodes_real_compound_v3_native_collateral(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """A real bulker deposit of native ETH collateral, stored as the decoder produced it before
    the wrapping was added, is reset by the migration and the normal undecoded transactions
    task then redecodes it as the wrap followed by the WETH deposit."""
    tx_hash = deserialize_evm_tx_hash('0xde4dcd5588a4f2e2c3a6f24b5386cf289aad5f3b7a3f99d5411ca815dccc9fa3')  # noqa: E501
    # pulls the real transaction and receipt into the DB and marks it decoded
    current_events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:  # replace them with the legacy decoding
        dbevents.delete_events_by_tx_ref(
            write_cursor=write_cursor,
            tx_refs=[tx_hash],
            location=LOCATION_ETHEREUM,
        )
        dbevents.add_history_events(write_cursor=write_cursor, history=[EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1761848615000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees := '0.000082791232942678'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ETH,
            amount=FVal(deposit_amount := '0.01'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} ETH into Compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=(compound_contract := string_to_evm_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3')),  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Enable {deposit_amount} ETH as collateral on Compound v3',
            counterparty=CPT_COMPOUND_V3,
            address=compound_contract,
        )])

    run_single_migration(database=database, migration=30)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM chain_events_info WHERE tx_ref=?', (tx_hash,),
        ).fetchone()[0] == 0

    with patch_decoder_reload_data():
        assert decoder.get_and_decode_undecoded_transactions(limit=None) == [tx_hash]

    with database.conn.read_ctx() as cursor:
        redecoded_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(tx_hashes=[tx_hash]),
        )

    for event in redecoded_events:
        event.identifier = None
    assert redecoded_events == current_events
    assert [(event.event_subtype, event.asset) for event in redecoded_events] == [
        (HistoryEventSubType.FEE, A_ETH),
        (HistoryEventSubType.DEPOSIT_FOR_WRAPPED, A_ETH),
        (HistoryEventSubType.RECEIVE_WRAPPED, A_WETH),
        (HistoryEventSubType.DEPOSIT_TO_PROTOCOL, A_WETH),
        (HistoryEventSubType.NONE, A_WETH),
    ]
