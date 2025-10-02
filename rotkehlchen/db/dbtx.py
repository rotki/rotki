from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from rotkehlchen.db.filtering import (
    EvmTransactionsNotDecodedFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
)

if TYPE_CHECKING:
    from solders.solders import Signature

    from rotkehlchen.chain.solana.types import SolanaTransaction
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.types import EvmTransaction, EVMTxHash

T_Address = TypeVar('T_Address')
T_Transaction = TypeVar('T_Transaction', bound='SolanaTransaction | EvmTransaction')
T_TxHash = TypeVar('T_TxHash', bound='EVMTxHash | Signature')
T_TxFilterQuery = TypeVar('T_TxFilterQuery')
T_TxNotDecodedFilterQuery = TypeVar(
    'T_TxNotDecodedFilterQuery',
    bound=EvmTransactionsNotDecodedFilterQuery | SolanaTransactionsNotDecodedFilterQuery,
)


class DBCommonTx(ABC, Generic[T_Address, T_Transaction, T_TxHash, T_TxFilterQuery, T_TxNotDecodedFilterQuery]):  # noqa: E501

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    @abstractmethod
    def add_transactions(
            self,
            write_cursor: 'DBCursor',
            solana_transactions: list[T_Transaction],
            relevant_address: T_Address | None,
    ) -> None:
        """Add transactions to the database."""

    @abstractmethod
    def get_transactions(
            self,
            cursor: 'DBCursor',
            filter_: T_TxFilterQuery,
    ) -> list[T_Transaction]:
        """Get transactions from the database using the given filter."""

    @abstractmethod
    def deserialize_tx_hash_from_db(self, raw_tx_hash: bytes) -> T_TxHash:
        """Given a raw tx hash from the DB, deserialize it into a tx hash object."""

    @abstractmethod
    def _get_txs_not_decoded_column_and_query(self) -> tuple[str, str]:
        """Returns the tx hash column name and partial query used in conjunction with either
        the Evm or Solana TransactionsNotDecodedFilterQuery in get_transaction_hashes_not_decoded
        and count_hashes_not_decoded.
        """

    def get_transaction_hashes_not_decoded(
            self,
            filter_query: T_TxNotDecodedFilterQuery,
    ) -> list[T_TxHash]:
        """Get tx hashes for the txs that have not been decoded."""
        column, base_query = self._get_txs_not_decoded_column_and_query()
        query, bindings = filter_query.prepare()
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(f'SELECT {column} FROM {base_query} {query}', bindings)
            return [self.deserialize_tx_hash_from_db(x[0]) for x in cursor]

    def count_hashes_not_decoded(self, filter_query: T_TxNotDecodedFilterQuery) -> int:
        """Count the number of txs that have not been decoded."""
        _, base_query = self._get_txs_not_decoded_column_and_query()
        query, bindings = filter_query.prepare()
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM {base_query} {query}', bindings)
            return cursor.fetchone()[0]
