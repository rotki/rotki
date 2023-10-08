import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, Any, Optional, Union, cast

from rotkehlchen.chain.base.node_inquirer import BaseInquirer
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismSuperchainTransactions(EvmTransactions, metaclass=ABCMeta):
    """
    An intermediary transactions class to be inherited by chains based on the Optimism Superchain.

    Provides support for handling the layer 1 fee structure common to optimism-based chains.
    """

    def __init__(
            self,
            node_inquirer: Union[
                OptimismInquirer,
                BaseInquirer,
            ],
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=node_inquirer, database=database)
        self.dbevmtx = DBOptimismTx(database)

    def ensure_tx_data_exists(
            self,
            cursor: 'DBCursor',
            tx_hash: 'EVMTxHash',
            relevant_address: Optional['ChecksumEvmAddress'],
    ) -> tuple[tuple[Any, ...], 'EvmTxReceipt']:
        """In addition to the base class check, also checks that the optimism transaction has
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
        transaction = cast(OptimismTransaction, transaction)
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
