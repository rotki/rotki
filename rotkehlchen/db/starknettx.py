from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.starknet.types import StarknetTransaction
from rotkehlchen.db.dbtx import DBCommonTx
from rotkehlchen.db.filtering import (
    StarknetTransactionsFilterQuery,
    StarknetTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.types import Location, StarknetAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class DBStarknetTx(DBCommonTx[StarknetAddress, StarknetTransaction, str, StarknetTransactionsFilterQuery, StarknetTransactionsNotDecodedFilterQuery]):  # noqa: E501
    """Database handler for Starknet transactions"""

    def get_existing_tx_hashes(
            self,
            cursor: 'DBCursor',
            tx_hashes: Sequence[str],
    ) -> set[str]:
        """Filter the provided transaction hashes returning only those that already exist in DB."""
        existing: set[str] = set()
        if len(tx_hashes) == 0:
            return existing

        for chunk, placeholders in get_query_chunks(tx_hashes):
            cursor.execute(
                f'SELECT transaction_hash FROM starknet_transactions '
                f'WHERE transaction_hash IN ({placeholders})',
                list(chunk),
            )
            existing.update(entry[0] for entry in cursor)

        return existing

    def add_transactions(
            self,
            write_cursor: 'DBCursor',
            starknet_transactions: list[StarknetTransaction],
            relevant_address: StarknetAddress | None,
    ) -> None:
        """Add starknet transactions to the database"""
        query = (
            'INSERT OR IGNORE INTO starknet_transactions'
            '(transaction_hash, block_number, block_timestamp, from_address, to_address, '
            'selector, max_fee, actual_fee, status, transaction_type) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        )
        for tx in starknet_transactions:
            if self.db.write_single_tuple(
                write_cursor=write_cursor,
                tuple_type='starknet_transaction',
                query=query,
                entry=(
                    tx.transaction_hash,
                    tx.block_number,
                    tx.block_timestamp,
                    tx.from_address,
                    tx.to_address,
                    tx.selector,
                    str(tx.max_fee),
                    str(tx.actual_fee),
                    tx.status,
                    tx.transaction_type,
                ),
                relevant_address=relevant_address,
            ) is None:
                continue

    @staticmethod
    def get_transactions(
            cursor: 'DBCursor',
            filter_: StarknetTransactionsFilterQuery,
    ) -> list[StarknetTransaction]:
        """Get starknet transactions from the database with filtering"""
        query, bindings = filter_.prepare()
        transactions: list[StarknetTransaction] = []
        for row in cursor.execute(
                'SELECT identifier, transaction_hash, block_number, block_timestamp, '
                'from_address, to_address, selector, max_fee, actual_fee, status, '
                f'transaction_type FROM starknet_transactions {query}',
                bindings,
        ):
            calldata: list[str] = []
            transactions.append(StarknetTransaction(
                transaction_hash=row[1],
                block_number=row[2],
                block_timestamp=Timestamp(row[3]),
                from_address=StarknetAddress(row[4]),
                to_address=StarknetAddress(row[5]) if row[5] is not None else None,
                selector=row[6],
                calldata=calldata,
                max_fee=int(row[7]),
                actual_fee=int(row[8]),
                status=row[9],
                transaction_type=row[10],
                db_id=row[0],
            ))

        return transactions

    def deserialize_tx_hash_from_db(self, raw_tx_hash: bytes) -> str:
        if isinstance(raw_tx_hash, bytes):
            return raw_tx_hash.decode('utf-8')
        return str(raw_tx_hash)

    def _get_txs_not_decoded_column_and_query(self) -> tuple[str, str]:
        return (
            'transaction_hash',
            'starknet_transactions AS A LEFT JOIN starknet_tx_mappings AS B ON A.identifier = B.tx_id ',  # noqa: E501
        )

    def delete_transaction_data(
            self,
            write_cursor: 'DBCursor',
            tx_hash: str | None = None,
    ) -> None:
        """Deletes starknet transactions from the DB. If tx_hash is given, only deletes
        the transaction with that hash.
        """
        query = 'DELETE FROM starknet_transactions'
        bindings: list[str] = []
        if tx_hash is not None:
            query += ' WHERE transaction_hash = ?'
            bindings.append(tx_hash)

        write_cursor.execute(query, bindings)

    def count_transactions_in_range(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> int:
        """Return the number of transactions between from_ts and to_ts"""
        with self.db.conn.read_ctx() as cursor:
            return cursor.execute(
                'SELECT COUNT(*) FROM starknet_transactions WHERE block_timestamp BETWEEN ? AND ?',
                (from_ts, to_ts),
            ).fetchone()[0]

    def delete_data_for_address(
            self,
            write_cursor: 'DBCursor',
            address: StarknetAddress,
    ) -> None:
        """Deletes all starknet transactions and their related data for a given address."""
        where_str = """
        WHERE M.address = ?
        AND M.tx_id NOT IN (SELECT tx_id FROM starknettx_address_mappings WHERE address != ?)
        """
        if len(results := write_cursor.execute(
            'SELECT DISTINCT S.transaction_hash FROM starknettx_address_mappings AS M '
            f'INNER JOIN starknet_transactions AS S ON S.identifier = M.tx_id {where_str}',
            (address, address),
        ).fetchall()) == 0:
            return

        DBHistoryEvents(self.db).delete_events_by_tx_ref(
            write_cursor=write_cursor,
            tx_refs=[row[0] for row in results],
            location=Location.STARKNET,
        )
        write_cursor.execute(
            'DELETE FROM starknet_transactions WHERE identifier IN ('
            f'SELECT DISTINCT tx_id FROM starknettx_address_mappings AS M {where_str})',
            (address, address),
        )
