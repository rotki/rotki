"""Repository for database utility operations."""
import logging
from typing import TYPE_CHECKING, Any, Sequence

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.utils import DBTupleType, db_tuple_to_str
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

log = logging.getLogger(__name__)


class DatabaseUtilsRepository:
    """Repository for handling database utility operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the database utils repository."""
        self.msg_aggregator = msg_aggregator

    def write_tuples(
            self,
            write_cursor: 'DBCursor',
            tuple_type: DBTupleType,
            query: str,
            tuples: Sequence[tuple[Any, ...]],
            **kwargs: ChecksumEvmAddress | None,
    ) -> None:
        """
        Helper function to help write multiple tuples of some kind of entry and
        log the error if anything is raised.

        For transactions the query is INSERT OR IGNORE as the uniqueness constraints
        are known in advance. Also when used for inputting transactions make sure that
        for one write it's all for the same chain id.

        For the other tables simple `INSERT` is used but the primary key is a unique
        identifier each time so they can't be considered duplicates.
        """
        relevant_address = kwargs.get('relevant_address')
        try:
            write_cursor.executemany(query, tuples)
            if relevant_address is not None:
                if tuple_type == 'evm_transaction':
                    tx_hash_idx, chain_id_idx = 0, 1
                else:  # relevant address can only be left for internal tx
                    tx_hash_idx, chain_id_idx = 6, 7
                write_cursor.executemany(
                    'INSERT OR IGNORE INTO evmtx_address_mappings(tx_id, address) '
                    'SELECT TX.identifier, ? FROM evm_transactions TX WHERE '
                    'TX.tx_hash=? AND TX.chain_id=?',
                    [(relevant_address, x[tx_hash_idx], x[chain_id_idx]) for x in tuples],
                )
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            # That means that one of the tuples hit a constraint, probably some
            # foreign key connection is broken. Try to put them 1 by one.
            for entry in tuples:
                self.write_single_tuple(
                    write_cursor=write_cursor,
                    tuple_type=tuple_type,
                    query=query,
                    entry=entry,
                    relevant_address=relevant_address,
                )
        except OverflowError:
            self.msg_aggregator.add_error(
                f'Failed to add "{tuple_type}" to the DB with overflow error. '
                f'Check the logs for more details',
            )
            log.error(
                f'Overflow error while trying to add "{tuple_type}" tuples to the'
                f' DB. Tuples: {tuples} with query: {query}',
            )

    @staticmethod
    def write_single_tuple(
            write_cursor: 'DBCursor',
            tuple_type: DBTupleType,
            query: str,
            entry: tuple[Any, ...],
            relevant_address: ChecksumEvmAddress | None,
    ) -> int | None:
        """Helper to write an entry of a tuple type and handle address mapping"""
        try:
            write_cursor.execute(query, entry)
            if tuple_type == 'evm_transaction':
                tx_id = write_cursor.execute(
                    'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                    (entry[0], entry[1]),
                ).fetchone()[0]

                # add address mapping if relevant_address is provided and transaction exists
                if relevant_address is not None and tx_id is not None:
                    write_cursor.execute(
                        'INSERT OR IGNORE INTO evmtx_address_mappings(tx_id, address) VALUES (?, ?)',  # noqa: E501
                        (tx_id, relevant_address),
                    )

                return tx_id  # return the transaction id (new or existing)
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            string_repr = db_tuple_to_str(entry, tuple_type)
            log.warning(
                f'Did not add "{string_repr}" to the DB due to "{e!s}".'
                f'Some other constraint was hit.',
            )
        except sqlcipher.InterfaceError:  # pylint: disable=no-member
            log.critical(f'Interface error with tuple: {entry}')

        return None