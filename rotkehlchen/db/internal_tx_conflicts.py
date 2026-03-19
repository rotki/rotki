from typing import TYPE_CHECKING, Final, cast

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
from rotkehlchen.db.filtering import INTERNAL_TX_CONFLICTS_JOIN
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ChainID,
    EVMTxHash,
    Location,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.filtering import InternalTxConflictsFilterQuery

INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE: Final = 'fix_redecode'
INTERNAL_TX_CONFLICT_ACTION_REPULL: Final = 'repull'
INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS: Final = 'all_zero_gas'
INTERNAL_TX_CONFLICT_REPULL_REASON_OTHER: Final = 'other'
INTERNAL_TX_CONFLICT_REDECODE_REASON_MIXED_ZERO_GAS: Final = 'mixed_zero_gas'
INTERNAL_TX_CONFLICT_REDECODE_REASON_DUPLICATE_EXACT_ROWS: Final = 'duplicate_exact_rows'
INTERNAL_TX_CONFLICT_REDECODE_REASON_MIXED_ZERO_GAS_AND_DUPLICATE: Final = 'mixed_zero_gas_and_duplicate'  # noqa: E501
INTERNAL_TXS_TO_REPULL: Final = 20


POPULATE_INTERNAL_TX_CONFLICTS_QUERY: Final = """
WITH considered_rows AS (
  SELECT *
  FROM evm_internal_transactions
  WHERE NOT (gas != '0' AND gas_used = '0')
),
key_stats AS (
  SELECT
    parent_tx,
    from_address,
    to_address,
    value,
    SUM(CASE WHEN gas = '0' THEN 1 ELSE 0 END) AS bad_rows,
    SUM(CASE WHEN gas != '0' AND gas_used != '0' THEN 1 ELSE 0 END) AS good_rows
  FROM considered_rows
  GROUP BY parent_tx, from_address, to_address, value
),
dup_txs AS (
  SELECT DISTINCT parent_tx
  FROM (
    SELECT
      parent_tx, from_address, to_address, value, gas, gas_used, COUNT(*) AS cnt
    FROM considered_rows
    GROUP BY parent_tx, from_address, to_address, value, gas, gas_used
    HAVING COUNT(*) > 1
  )
),
tx_flags AS (
  SELECT
    ks.parent_tx,
    MAX(CASE WHEN ks.bad_rows > 0 AND ks.good_rows = 0 THEN 1 ELSE 0 END) AS has_repull_group,
    MAX(CASE WHEN ks.bad_rows > 0 AND ks.good_rows > 0 THEN 1 ELSE 0 END) AS has_mixed_bad_group
  FROM key_stats ks
  GROUP BY ks.parent_tx
)
INSERT OR IGNORE INTO evm_internal_tx_conflicts(
  transaction_hash,
  chain,
  action,
  repull_reason,
  redecode_reason,
  fixed
)
SELECT
  et.tx_hash,
  et.chain_id,
  CASE
    WHEN tf.has_repull_group = 1 THEN 'repull'
    ELSE 'fix_redecode'
  END AS action,
  CASE
    WHEN tf.has_repull_group = 1 THEN 'all_zero_gas'
    ELSE NULL
  END AS repull_reason,
  CASE
    WHEN tf.has_repull_group = 1 THEN NULL
    WHEN tf.has_mixed_bad_group = 1 AND dt.parent_tx IS NOT NULL THEN
      'mixed_zero_gas_and_duplicate'
    WHEN tf.has_mixed_bad_group = 1 THEN 'mixed_zero_gas'
    WHEN dt.parent_tx IS NOT NULL THEN 'duplicate_exact_rows'
    ELSE NULL
  END AS redecode_reason,
  0 AS fixed
FROM tx_flags tf
JOIN evm_transactions et ON et.identifier = tf.parent_tx
LEFT JOIN dup_txs dt ON dt.parent_tx = tf.parent_tx
WHERE tf.has_repull_group = 1 OR tf.has_mixed_bad_group = 1 OR dt.parent_tx IS NOT NULL;
"""


def is_tx_customized(
        cursor: 'DBCursor',
        tx_hash: EVMTxHash,
        chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
) -> bool:
    """Return whether tx has any customized events."""
    return cursor.execute(
        'SELECT COUNT(*) FROM history_events AS h '
        'INNER JOIN chain_events_info AS c ON h.identifier = c.identifier '
        'INNER JOIN history_events_mappings AS m ON h.identifier = m.parent_identifier '
        'WHERE c.tx_ref = ? AND h.location = ? AND m.name = ? AND m.value = ?',
        (
            tx_hash,
            Location.from_chain_id(chain_id).serialize_for_db(),
            HISTORY_MAPPING_KEY_STATE,
            HistoryMappingState.CUSTOMIZED.serialize_for_db(),
        ),
    ).fetchone()[0] > 0


def clean_internal_tx_conflict(
        write_cursor: 'DBCursor',
        tx_hash: EVMTxHash,
        chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
) -> None:
    """Delete invalid/duplicate internals and queue decode-only refresh.

    TX_INTERNALS_QUERIED is intentionally not cleared for fix_redecode actions because
    these transactions are repaired in-place and do not need an internal repull.

    For non-customized transactions we also remove decoded history events linked to this tx
    so the next decode recreates them from the repaired internals.
    """
    write_cursor.execute("""
    WITH fix_txs AS (
      SELECT identifier AS parent_tx
      FROM evm_transactions
      WHERE tx_hash = ? AND chain_id = ?
    ),
    ranked AS (
      SELECT
        eit.rowid,
        eit.parent_tx,
        eit.gas,
        eit.gas_used,
        ROW_NUMBER() OVER (
          PARTITION BY
            eit.parent_tx, eit.from_address, eit.to_address, eit.value, eit.gas, eit.gas_used
          ORDER BY eit.rowid
        ) AS rn
      FROM evm_internal_transactions AS eit
      JOIN fix_txs AS ft ON ft.parent_tx = eit.parent_tx
    )
    DELETE FROM evm_internal_transactions
    WHERE rowid IN (
      SELECT rowid
      FROM ranked
      WHERE gas = '0' OR rn > 1
    )
    """, (tx_hash, chain_id.serialize_for_db()))

    write_cursor.execute(
        'DELETE FROM history_events WHERE identifier IN ('
        'SELECT h.identifier FROM history_events h '
        'INNER JOIN chain_events_info c ON h.identifier = c.identifier '
        'WHERE c.tx_ref = ? AND h.location = ?'
        ')',
        (tx_hash, Location.from_chain_id(chain_id).serialize_for_db()),
    )

    write_cursor.execute(
        'DELETE FROM evm_tx_mappings WHERE tx_id IN ('
        'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?'
        ') AND value=?',
        (tx_hash, chain_id.serialize_for_db(), TX_DECODED),
    )


def get_internal_tx_conflicts(
        cursor: 'DBCursor',
        action: str,
        fixed: bool,
        limit: int | None = None,
) -> list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash]]:
    """Get internal tx conflict entries."""
    query = (
        'SELECT chain, transaction_hash FROM evm_internal_tx_conflicts '
        'WHERE action=? AND fixed=? '
        'ORDER BY '
        'CASE WHEN last_retry_ts IS NULL THEN 0 ELSE 1 END, '
        'last_retry_ts ASC, '
        'chain, transaction_hash'
    )
    bindings: tuple[object, ...] = (action, int(fixed))
    if limit is not None:
        query += ' LIMIT ?'
        bindings = (*bindings, limit)

    entries: list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash]] = []
    for chain, tx_hash in cursor.execute(query, bindings):
        chain_id = ChainID.deserialize_from_db(chain)
        assert chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
        entries.append((cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', chain_id), deserialize_evm_tx_hash(tx_hash)))  # noqa: E501

    return entries


def get_pending_internal_tx_repull_conflicts(
        cursor: 'DBCursor',
        filter_query: 'InternalTxConflictsFilterQuery',
) -> list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash, int | None, str, str | None, str | None, int | None, str | None, str | None]]:  # noqa: E501
    """Return internal tx conflicts with action and metadata, including the transaction timestamp."""  # noqa: E501
    base_query = (
        'SELECT c.chain, c.transaction_hash, et.timestamp, c.action, '
        'c.repull_reason, c.redecode_reason, c.last_retry_ts, c.last_error '
        f'FROM evm_internal_tx_conflicts c {INTERNAL_TX_CONFLICTS_JOIN}'
    )
    filter_str, bindings = filter_query.prepare()
    # First pass: collect rows and compute default group identifiers
    rows: list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash, int | None, str, str | None, str | None, int | None, str | None]] = []  # noqa: E501
    tx_hashes: list[bytes] = []
    for row_chain, row_tx_hash, tx_timestamp, action, repull_reason, redecode_reason, last_retry_ts, last_error in cursor.execute(  # noqa: E501
            base_query + filter_str,
            bindings,
    ):
        chain_id = ChainID.deserialize_from_db(row_chain)
        assert chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
        tx_hash = deserialize_evm_tx_hash(row_tx_hash)
        rows.append((
            cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', chain_id),
            tx_hash,
            tx_timestamp,
            action,
            repull_reason,
            redecode_reason,
            last_retry_ts,
            last_error,
        ))
        tx_hashes.append(bytes(tx_hash))

    # Single batch query to get group identifiers for all tx hashes at once.
    group_id_map: dict[bytes, str] = {}
    if tx_hashes:
        placeholders = ','.join(['?'] * len(tx_hashes))
        for tx_ref, group_id in cursor.execute(
                'SELECT ce.tx_ref, MIN(h.group_identifier) '
                'FROM history_events h '
                'INNER JOIN chain_events_info ce ON h.identifier = ce.identifier '
                f'WHERE ce.tx_ref IN ({placeholders}) '
                'GROUP BY ce.tx_ref',
                tx_hashes,
        ):
            group_id_map[bytes(tx_ref)] = group_id

    entries: list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash, int | None, str, str | None, str | None, int | None, str | None, str | None]] = []  # noqa: E501
    for chain_id, tx_hash, tx_timestamp, action, repull_reason, redecode_reason, last_retry_ts, last_error in rows:  # noqa: E501
        entries.append((
            chain_id,
            tx_hash,
            tx_timestamp,
            action,
            repull_reason,
            redecode_reason,
            last_retry_ts,
            last_error,
            group_id_map.get(bytes(tx_hash)),
        ))

    return entries


def count_pending_internal_tx_repull_conflicts(
        cursor: 'DBCursor',
        filter_query: 'InternalTxConflictsFilterQuery',
) -> int:
    """Count internal tx conflicts matching the pending-conflicts filters."""
    filter_str, bindings = filter_query.prepare(
        with_pagination=False,
        with_order=False,
    )
    return cursor.execute(
        f'SELECT COUNT(*) FROM evm_internal_tx_conflicts c {INTERNAL_TX_CONFLICTS_JOIN}' + filter_str,  # noqa: E501
        bindings,
    ).fetchone()[0]


def set_internal_tx_conflict_fixed(
        write_cursor: 'DBCursor',
        tx_hash: EVMTxHash,
        chain_id: ChainID,
) -> None:
    write_cursor.execute(
        'UPDATE evm_internal_tx_conflicts SET fixed=1, last_error=NULL WHERE transaction_hash=? AND chain=?',  # noqa: E501
        (tx_hash, chain_id.serialize_for_db()),
    )


def set_internal_tx_conflict_repull_error(
        write_cursor: 'DBCursor',
        tx_hash: EVMTxHash,
        chain_id: ChainID,
        retry_ts: int,
        error: str,
) -> None:
    write_cursor.execute(
        'UPDATE evm_internal_tx_conflicts SET last_retry_ts=?, last_error=? WHERE transaction_hash=? AND chain=?',  # noqa: E501
        (retry_ts, error, tx_hash, chain_id.serialize_for_db()),
    )
