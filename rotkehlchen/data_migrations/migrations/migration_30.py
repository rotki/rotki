import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.compound.v3.constants import CPT_COMPOUND_V3
from rotkehlchen.chain.solana.constants import SOLANA_V1_ACTIVATION_SLOT
from rotkehlchen.constants.assets import A_ETH, A_POL
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVM_LOCATIONS_TYPE,
    ChainID,
    EVMTxHash,
    Location,
    SolanaAddress,
    SupportedBlockchain,
)
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_30(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:
    """Introduced at v1.44.3.

    Solana v1 transactions were skipped while querying transaction details. Mark accounts whose
    stored history has already advanced past v1 activation so their affected interval is backfilled
    during the next normal transaction sync. The migration itself performs no network requests.

    It also removes the last balances query timestamp of chains that are fully disabled in
    disabled_chain_queries. Nothing refreshes it while the chain is disabled, so the one it had
    when it was disabled was still reported as its last refresh.

    It also resets for redecoding the transactions with a Compound v3 collateral deposit or
    withdrawal of the chain's native token. The bulker wraps it, so these are now decoded in
    the wrapped token, and a position opened before this change would otherwise be withdrawn
    in a token it never deposited. Transactions with customized or matched events stay
    decoded, as in reset_events_for_redecode().
    """
    @progress_step(description='Scheduling missing Solana v1 transaction recovery')
    def _schedule_solana_transaction_backfill(rotki: Rotkehlchen) -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            accounts = [SolanaAddress(row[0]) for row in cursor.execute(
                'SELECT ba.account FROM blockchain_accounts ba '
                'WHERE ba.blockchain=? AND EXISTS('
                'SELECT 1 FROM solana_transactions st '
                'JOIN solanatx_address_mappings sam ON st.identifier=sam.tx_id '
                'WHERE st.slot >= ? AND (sam.address=ba.account OR sam.address IN ('
                'SELECT ata_address FROM solana_ata_address_mappings WHERE account=ba.account)))',
                (SupportedBlockchain.SOLANA.value, SOLANA_V1_ACTIVATION_SLOT),
            )]

        with rotki.data.db.user_write() as write_cursor:
            write_cursor.executemany(
                'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES(?, ?)',
                [(
                    DBCacheDynamic.SOLANA_TX_BACKFILL_FROM_SLOT.get_db_key(address=account),
                    SOLANA_V1_ACTIVATION_SLOT,
                ) for account in accounts],
            )

    @progress_step(description='Removing stale balance refresh times of disabled chains')
    def _delete_stale_balances_query_timestamps(rotki: Rotkehlchen) -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            disabled_chain_queries = rotki.data.db.get_settings(cursor).disabled_chain_queries

        with rotki.data.db.user_write() as write_cursor:
            rotki.data.db.delete_balances_query_ts_for_disabled_chains(
                write_cursor=write_cursor,
                disabled_chain_queries=disabled_chain_queries,
            )

    @progress_step(description='Resetting Compound v3 native collateral transactions')
    def _reset_compound_v3_native_collateral(rotki: Rotkehlchen) -> None:
        tx_ids: list[int] = []
        tx_hashes: defaultdict[EVM_LOCATIONS_TYPE, list[EVMTxHash]] = defaultdict(list)
        chain_native_assets: tuple[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, Asset], ...] = (
            (ChainID.ETHEREUM, A_ETH),
            (ChainID.ARBITRUM_ONE, A_ETH),
            (ChainID.BASE, A_ETH),
            (ChainID.OPTIMISM, A_ETH),
            (ChainID.SCROLL, A_ETH),
            (ChainID.POLYGON_POS, A_POL),
        )
        with rotki.data.db.conn.read_ctx() as cursor:
            for chain_id, native_asset in chain_native_assets:
                location = Location.from_chain_id(chain_id)
                for tx_id, tx_hash in cursor.execute(
                    'SELECT DISTINCT txs.identifier, txs.tx_hash FROM history_events AS events '
                    'INNER JOIN chain_events_info AS info ON info.identifier=events.identifier '
                    'INNER JOIN evm_transactions AS txs '
                    'ON txs.tx_hash=info.tx_ref AND txs.chain_id=? '
                    'WHERE events.location=? AND events.asset=? AND info.counterparty=? AND '
                    '((events.type=? AND events.subtype=?) OR (events.type=? AND events.subtype=?)) '  # noqa: E501
                    'AND NOT EXISTS(SELECT 1 FROM chain_events_info AS tx_info INNER JOIN '
                    'history_events_mappings AS mappings ON '
                    'mappings.parent_identifier=tx_info.identifier WHERE '
                    'tx_info.tx_ref=txs.tx_hash AND mappings.name=? AND mappings.value IN (?, ?))',
                    (
                        chain_id.serialize_for_db(),
                        location.serialize_for_db(),
                        native_asset.identifier,
                        CPT_COMPOUND_V3,
                        HistoryEventType.DEPOSIT.serialize(),
                        HistoryEventSubType.DEPOSIT_TO_PROTOCOL.serialize(),
                        HistoryEventType.WITHDRAWAL.serialize(),
                        HistoryEventSubType.WITHDRAW_FROM_PROTOCOL.serialize(),
                        HISTORY_MAPPING_KEY_STATE,
                        HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                        HistoryMappingState.MATCHED.serialize_for_db(),
                    ),
                ):
                    tx_ids.append(tx_id)
                    tx_hashes[location].append(EVMTxHash(tx_hash))

        if len(tx_ids) == 0:
            return

        dbevents = DBHistoryEvents(rotki.data.db)
        with rotki.data.db.user_write() as write_cursor:
            for location, location_tx_hashes in tx_hashes.items():
                dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=location_tx_hashes,
                    location=location,
                    customized_handling='preserve_transactions',
                )
            write_cursor.executemany(
                'DELETE FROM evm_tx_mappings WHERE tx_id=? AND value=?',
                [(tx_id, TX_DECODED) for tx_id in tx_ids],
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
