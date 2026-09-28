from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.l2_with_l1_fees.types import (
    L1_ORIGINATED_TX_TYPE,
    L2_CHAINIDS_WITH_L1_FEES,
    L2ChainIdsWithL1FeesType,
)
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import ChainID, EVMTxHash, Location
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_28(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:
    """Introduced at v1.44.1

    Legacy L1 fees of zero were stored both for resolved zero fees and for fees that could
    not be resolved, so their gas events may be missing the L1 portion. Mark them unresolved
    and reset the decoded events of those transactions so that redecoding repairs the fee.
    L1 originated transactions are skipped since their L1 fee is always zero. Transactions
    with customized or matched events stay decoded, as in reset_events_for_redecode(), since
    redecoding them on top of the preserved events would not repair the fee and could add
    duplicates. Only their fee is marked unresolved so a manual redecode repairs it.
    """
    @progress_step(description='Resetting transactions with legacy zero L1 fees')
    def _reset_legacy_zero_l1_fees(rotki: Rotkehlchen) -> None:
        tx_ids: list[int] = []
        redecode_tx_ids: list[int] = []
        tx_hashes: defaultdict[L2ChainIdsWithL1FeesType, list[EVMTxHash]] = defaultdict(list)
        with rotki.data.db.conn.read_ctx() as cursor:
            for tx_id, tx_hash, chain_id, is_customized in cursor.execute(
                'SELECT txs.identifier, txs.tx_hash, txs.chain_id, EXISTS('
                'SELECT 1 FROM chain_events_info AS info INNER JOIN history_events_mappings '
                'AS mappings ON mappings.parent_identifier=info.identifier WHERE '
                'info.tx_ref=txs.tx_hash AND mappings.name=? AND mappings.value IN (?, ?)'
                ') FROM optimism_transactions AS fees INNER JOIN evm_transactions AS txs '
                'ON txs.identifier=fees.tx_id '
                'LEFT JOIN evmtx_receipts AS receipts ON receipts.tx_id=fees.tx_id '
                f"WHERE fees.l1_fee='0' AND txs.chain_id IN ({','.join('?' * len(L2_CHAINIDS_WITH_L1_FEES))}) "  # noqa: E501
                'AND (receipts.type IS NULL OR receipts.type!=?)',
                (
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                    HistoryMappingState.MATCHED.serialize_for_db(),
                    *(x.serialize_for_db() for x in L2_CHAINIDS_WITH_L1_FEES),
                    L1_ORIGINATED_TX_TYPE,
                ),
            ):
                tx_ids.append(tx_id)
                if is_customized:
                    continue

                redecode_tx_ids.append(tx_id)
                tx_hashes[ChainID.deserialize_from_db(chain_id)].append(EVMTxHash(tx_hash))  # type: ignore[index]  # chain ids are filtered in the query

        if len(tx_ids) == 0:
            return

        dbevents = DBHistoryEvents(rotki.data.db)
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.executemany(
                'UPDATE optimism_transactions SET l1_fee=NULL WHERE tx_id=?',
                [(tx_id,) for tx_id in tx_ids],
            )
            for chain_id, chain_tx_hashes in tx_hashes.items():
                dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=chain_tx_hashes,
                    location=Location.from_chain_id(chain_id),
                    customized_handling='preserve_transactions',
                )
            write_cursor.executemany(
                'DELETE FROM evm_tx_mappings WHERE tx_id=? AND value=?',
                [(tx_id, TX_DECODED) for tx_id in redecode_tx_ids],
            )

    perform_userdb_migration_steps(rotki, progress_handler)
