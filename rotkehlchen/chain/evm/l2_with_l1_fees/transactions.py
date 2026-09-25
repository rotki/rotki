import logging
from abc import ABC
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.utils import read_integer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EVMTxHash, deserialize_evm_tx_hash
from rotkehlchen.utils.data_structures import LRUSetCache

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class L2WithL1FeesTransactions(EvmTransactions, ABC):
    """
    An intermediary transactions class to be inherited by L2 chains with an extra L1 Fee structure.
    """

    def __init__(
            self,
            node_inquirer: EvmNodeInquirer,
            database: DBHandler,
    ) -> None:
        super().__init__(evm_inquirer=node_inquirer, database=database)
        self.dbevmtx = DBL2WithL1FeesTx(database)
        self._fresh_zero_fee_hashes: LRUSetCache[EVMTxHash] = LRUSetCache(maxsize=512)

    def _enrich_receipts(self, receipts: list[dict[str, Any]]) -> None:
        """Fill missing receipt fees from indexers before writing the receipt batch."""
        missing: dict[EVMTxHash, dict[str, Any]] = {}
        for receipt in receipts:
            tx_hash = deserialize_evm_tx_hash(receipt['transactionHash'])
            if tx_hash == GENESIS_HASH:
                continue
            try:
                read_integer(receipt, 'l1Fee')
            except (KeyError, DeserializationError):
                missing[tx_hash] = receipt

        if len(missing) == 0:
            return

        placeholders = ','.join('?' for _ in missing)
        with self.database.conn.read_ctx() as cursor:
            rows = cursor.execute(
                'SELECT txs.tx_hash, txs.from_address, txs.block_number, fees.l1_fee '
                'FROM evm_transactions AS txs LEFT JOIN optimism_transactions AS fees '
                'ON txs.identifier=fees.tx_id '
                f'WHERE txs.chain_id=? AND txs.tx_hash IN ({placeholders})',
                (self.evm_inquirer.chain_id.serialize_for_db(), *missing),
            ).fetchall()

        for raw_hash, account, block_number, saved_fee in rows:
            if saved_fee is not None and int(saved_fee) != 0:
                continue
            tx_hash = deserialize_evm_tx_hash(raw_hash)
            if (fee := self.evm_inquirer.maybe_get_l1_fees(
                account=account,
                tx_hash=tx_hash,
                block_number=block_number,
            )) is not None:
                missing[tx_hash]['l1Fee'] = fee
            if fee in (None, 0):
                self._fresh_zero_fee_hashes.add(tx_hash)

    def ensure_tx_data_exists(
            self,
            cursor: DBCursor,
            tx_hash: EVMTxHash,
            relevant_address: ChecksumEvmAddress | None,
    ) -> tuple[L2WithL1FeesTransaction, EvmTxReceipt]:
        """In addition to the base class check, also checks that the transaction has
        a corresponding l1_fee value in the database. If not, pulls it.

        May raise:
        - RemoteError if there is a problem querying the data sources.
        - InputError if the transaction hash does not exist.
        """
        evm_tx, tx_receipt = super().ensure_tx_data_exists(
            cursor=cursor,
            tx_hash=tx_hash,
            relevant_address=relevant_address,
        )
        tx_id, saved_fee = cursor.execute(
            'SELECT txs.identifier, fees.l1_fee FROM evm_transactions AS txs '
            'LEFT JOIN optimism_transactions AS fees ON txs.identifier=fees.tx_id '
            'WHERE txs.tx_hash=? AND txs.chain_id=?',
            (tx_hash, self.evm_inquirer.chain_id.serialize_for_db()),
        ).fetchone()
        if saved_fee is not None and int(saved_fee) != 0 and isinstance(evm_tx, L2WithL1FeesTransaction):  # noqa: E501
            return evm_tx, tx_receipt

        # A fresh query or receipt batch already tried to resolve the fee. Reuse that
        # result during the next decode, then allow later attempts to repair old zero fees.
        if (saved_fee is None or int(saved_fee) == 0) and isinstance(evm_tx, L2WithL1FeesTransaction):  # noqa: E501
            if tx_hash in self._fresh_zero_fee_hashes:
                self._fresh_zero_fee_hashes.remove(tx_hash)
                return evm_tx, tx_receipt

            if (l1_fee := self.evm_inquirer.maybe_get_l1_fees(
                account=evm_tx.from_address,
                tx_hash=tx_hash,
                block_number=evm_tx.block_number,
            )) in (None, 0):
                # Old rows do not retain raw receipt fields. If indexers cannot repair one,
                # retry the direct transaction path, which can read l1Fee from an RPC receipt.
                try:
                    queried_tx, _ = self.evm_inquirer.get_transaction_by_hash(tx_hash=tx_hash)
                    if isinstance(queried_tx, L2WithL1FeesTransaction):
                        l1_fee = queried_tx.l1_fee
                except RemoteError as e:
                    log.warning('Could not repair L1 fee for %s from a receipt: %s', tx_hash, e)

            if l1_fee is not None:
                with self.database.user_write() as write_cursor:
                    DBL2WithL1FeesTx.set_l1_fee(
                        write_cursor=write_cursor,
                        tx_id=tx_id,
                        l1_fee=l1_fee,
                    )
            else:
                l1_fee = 0
                log.warning(
                    'Could not resolve L1 fee for %s on %s',
                    tx_hash,
                    self.evm_inquirer.chain_name,
                )
        else:
            if saved_fee is None or int(saved_fee) == 0:
                self._fresh_zero_fee_hashes.add(tx_hash)
            l1_fee = 0 if saved_fee is None else int(saved_fee)

        return L2WithL1FeesTransaction(
            tx_hash=evm_tx.tx_hash,
            chain_id=evm_tx.chain_id,
            timestamp=evm_tx.timestamp,
            block_number=evm_tx.block_number,
            from_address=evm_tx.from_address,
            to_address=evm_tx.to_address,
            value=evm_tx.value,
            gas=evm_tx.gas,
            gas_price=evm_tx.gas_price,
            gas_used=evm_tx.gas_used,
            input_data=evm_tx.input_data,
            nonce=evm_tx.nonce,
            l1_fee=l1_fee,
            tx_type=tx_receipt.tx_type,
            db_id=tx_id,
            authorization_list=evm_tx.authorization_list,
        ), tx_receipt
