from typing import TYPE_CHECKING, Final, cast

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, TX_DECODED, HistoryMappingState
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

INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE: Final = 'fix_redecode'
INTERNAL_TX_CONFLICT_ACTION_REPULL: Final = 'repull'
INTERNAL_TXS_TO_REPULL: Final = 20

CREATE_INTERNAL_TX_CONFLICTS_TABLE_QUERY: Final = """
CREATE TABLE IF NOT EXISTS evm_internal_tx_conflicts (
    transaction_hash BLOB NOT NULL,
    chain INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('fix_redecode', 'repull')),
    fixed INTEGER NOT NULL CHECK (fixed IN (0, 1)),
    PRIMARY KEY (transaction_hash, chain)
);
"""

POPULATE_INTERNAL_TX_CONFLICTS_QUERY: Final = """
WITH key_stats AS (
  SELECT
    parent_tx,
    from_address,
    to_address,
    value,
    SUM(CASE WHEN gas = '0' OR gas_used = '0' THEN 1 ELSE 0 END) AS bad_rows,
    SUM(CASE WHEN gas != '0' AND gas_used != '0' THEN 1 ELSE 0 END) AS good_rows
  FROM evm_internal_transactions
  GROUP BY parent_tx, from_address, to_address, value
),
dup_txs AS (
  SELECT DISTINCT parent_tx
  FROM (
    SELECT
      parent_tx, from_address, to_address, value, gas, gas_used, COUNT(*) AS cnt
    FROM evm_internal_transactions
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
INSERT OR IGNORE INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed)
SELECT
  et.tx_hash,
  et.chain_id,
  CASE
    WHEN tf.has_repull_group = 1 THEN 'repull'
    ELSE 'fix_redecode'
  END AS action,
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
        chain_id: ChainID,
) -> None:
    """Delete invalid/duplicate internals and queue decode-only refresh.

    TX_INTERNALS_QUERIED is intentionally not cleared for fix_redecode actions because
    these transactions are repaired in-place and do not need an internal repull.
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
      WHERE gas = '0' OR gas_used = '0' OR rn > 1
    )
    """, (tx_hash, chain_id.serialize_for_db()))

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
        'WHERE action=? AND fixed=? ORDER BY chain, transaction_hash'
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


def set_internal_tx_conflict_fixed(
        write_cursor: 'DBCursor',
        tx_hash: EVMTxHash,
        chain_id: ChainID,
) -> None:
    write_cursor.execute(
        'UPDATE evm_internal_tx_conflicts SET fixed=1 WHERE transaction_hash=? AND chain=?',
        (tx_hash, chain_id.serialize_for_db()),
    )
