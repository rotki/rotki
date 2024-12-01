import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Optional, cast

from rotkehlchen.chain.evm.l2_with_l1_fees.node_inquirer import L2WithL1FeesInquirer
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class L2WithL1FeesTransactions(EvmTransactions, ABC):
    """
    An intermediary transactions class to be inherited by L2 chains with an extra L1 Fee structure.
    """

    def __init__(
            self,
            node_inquirer: L2WithL1FeesInquirer,
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=node_inquirer, database=database)
        self.dbevmtx = DBL2WithL1FeesTx(database)

    def ensure_tx_data_exists(
            self,
            cursor: 'DBCursor',
            tx_hash: 'EVMTxHash',
            relevant_address: Optional['ChecksumEvmAddress'],
    ) -> tuple[tuple[Any, ...], 'EvmTxReceipt']:
        """In addition to the base class check, also checks that the transaction has
        a corresponding l1_fee value in the database. If not, pulls it.

        May raise:
        - RemoteError if there is a problem querying the data sources or transaction hash does
        not exist.
        """
        tx_data, tx_receipt = super().ensure_tx_data_exists(
            cursor=cursor,
            tx_hash=tx_hash,
            relevant_address=relevant_address,
        )
        l1_fee = cursor.execute(
            'SELECT op_txs.l1_fee FROM evm_transactions AS txs '
            'INNER JOIN optimism_transactions AS op_txs ON txs.identifier = op_txs.tx_id '
            'WHERE txs.tx_hash = ?',
            (tx_hash,),
        ).fetchone()

        if l1_fee is not None:
            return tx_data, tx_receipt  # all good, l1_fee is in the database

        transaction, _ = self.evm_inquirer.get_transaction_by_hash(tx_hash=tx_hash)
        transaction = cast('L2WithL1FeesTransaction', transaction)
        tx_id = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash = ?',
            (tx_hash,),
        ).fetchone()[0]
        with self.database.user_write() as write_cursor:
            write_cursor.execute(
                'INSERT OR IGNORE INTO optimism_transactions(tx_id, l1_fee) VALUES(?, ?)',
                (tx_id, str(transaction.l1_fee)),
            )
        query, bindings = EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id).prepare()  # noqa: E501
        query, bindings = self.dbevmtx._form_evm_transaction_dbquery(query=query, bindings=bindings, has_premium=True)  # noqa: E501
        tx_data = cursor.execute(query, bindings).fetchone()
        return tx_data, tx_receipt
