import logging
from typing import TYPE_CHECKING, Any, ClassVar

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.utils import maybe_read_integer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransactionAuthorization,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBL2WithL1FeesTx(DBEvmTx):
    AUTHORIZATION_DATA_START_INDEX: ClassVar[int] = 14

    def add_transactions(
            self,
            write_cursor: 'DBCursor',
            evm_transactions: list[L2WithL1FeesTransaction],  # type: ignore[override]
            relevant_address: ChecksumEvmAddress | None,
    ) -> None:
        """Adds L2WithL1Fees transactions to the database

        These transactions are used by all L2 chains with an extra L1 fee structure
        """
        super().add_transactions(
            write_cursor,
            evm_transactions,  # type: ignore[arg-type]
            relevant_address,
        )

        tx_tuples = [(tx.l1_fee, tx.tx_hash, tx.chain_id.serialize_for_db()) for tx in evm_transactions]  # noqa: E501
        query = """
            INSERT OR IGNORE INTO optimism_transactions(tx_id, l1_fee)
            SELECT evm_transactions.identifier, ? FROM
            evm_transactions WHERE tx_hash=? and chain_id=?
        """
        write_cursor.executemany(query, tx_tuples)

    def _form_evm_transaction_dbquery(self, query: str, bindings: list[Any]) -> tuple[str, list[tuple]]:  # noqa: E501
        base_select = (
            'SELECT evm_transactions.tx_hash, evm_transactions.chain_id, evm_transactions.timestamp, '  # noqa: E501
            'evm_transactions.block_number, evm_transactions.from_address, evm_transactions.to_address, '  # noqa: E501
            'evm_transactions.value, evm_transactions.gas, evm_transactions.gas_price, evm_transactions.gas_used, '  # noqa: E501
            'evm_transactions.input_data, evm_transactions.nonce, evm_transactions.identifier, OP.l1_fee, auth.nonce AS auth_nonce, auth.delegated_address '  # noqa: E501
            'FROM evm_transactions '
            'LEFT JOIN optimism_transactions AS OP ON evm_transactions.identifier=OP.tx_id '
            'LEFT JOIN evm_transactions_authorizations AS auth ON evm_transactions.identifier = auth.tx_id'  # noqa: E501
        )

        return f'{base_select} {query}', bindings

    def _build_evm_transaction(self, result: tuple[Any, ...], authorization_list_result: list[tuple[int, ChecksumEvmAddress]]) -> L2WithL1FeesTransaction:  # noqa: E501
        return L2WithL1FeesTransaction(
            tx_hash=deserialize_evm_tx_hash(result[0]),
            chain_id=ChainID.deserialize_from_db(result[1]),
            timestamp=deserialize_timestamp(result[2]),
            block_number=result[3],
            from_address=result[4],
            to_address=result[5],
            value=int(result[6]),
            gas=int(result[7]),
            gas_price=int(result[8]),
            gas_used=int(result[9]),
            input_data=result[10],
            nonce=result[11],
            db_id=result[12],
            l1_fee=0 if result[13] is None else int(result[13]),  # this check is only needed when _build_evm_transaction is called from a code path that does not call assert_tx_data_is_pulled().  # noqa: E501
            authorization_list=None if len(authorization_list_result) == 0 else [
                EvmTransactionAuthorization(nonce=entry[0], delegated_address=entry[1])
                for entry in authorization_list_result
            ],
        )

    def add_or_ignore_receipt_data(
            self,
            write_cursor: 'DBCursor',
            chain_id: ChainID,
            data: dict[str, Any],
    ) -> int:
        """Adds L2WithL1Fees tx receipt data to the database, and also saves the L1 fee data
        from the receipt if its not zero. Updates any existing l1 fee value since it may have
        already been added with a value of 0 if it wasn't present in the indexer's txlist data.
        Returns the db identifier of the transaction corresponding to this receipt.
        """
        tx_id = super().add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=chain_id,
            data=data,
        )

        try:
            l1_fee = maybe_read_integer(data, 'l1Fee')
        except DeserializationError as e:
            log.warning(f'Failed to get L1 fee from receipt while adding receipt to the DB due to {e!s}.')  # noqa: E501
            return tx_id

        if l1_fee != 0:
            write_cursor.execute(  # Ensure l1_fee is in the db. Updates any existing entry using `excluded` to reference the incoming row which was excluded from the insert due to conflict  # noqa: E501
                'INSERT INTO optimism_transactions(tx_id, l1_fee) VALUES (?, ?)'
                ' ON CONFLICT(tx_id) DO UPDATE SET l1_fee=excluded.l1_fee',
                (tx_id, l1_fee),
            )

        return tx_id
