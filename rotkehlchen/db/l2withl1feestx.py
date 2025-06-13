import logging
from typing import TYPE_CHECKING, Any, ClassVar

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransactionAuthorization,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.client import DBWriterClient

from rotkehlchen.constants.limits import FREE_ETH_TX_LIMIT

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBL2WithL1FeesTx(DBEvmTx):
    AUTHORIZATION_DATA_START_INDEX: ClassVar[int] = 14

    def add_evm_transactions(
            self,
            write_cursor: 'DBWriterClient',
            evm_transactions: list[L2WithL1FeesTransaction],  # type: ignore[override]
            relevant_address: ChecksumEvmAddress | None,
    ) -> None:
        """Adds L2WithL1Fees transactions to the database

        These transactions are used by all L2 chains with an extra L1 fee structure
        """
        super().add_evm_transactions(
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

    def _form_evm_transaction_dbquery(self, query: str, bindings: list[Any], has_premium: bool) -> tuple[str, list[tuple]]:  # noqa: E501
        base_select = (
            'SELECT evm_transactions.tx_hash, evm_transactions.chain_id, evm_transactions.timestamp, '  # noqa: E501
            'evm_transactions.block_number, evm_transactions.from_address, evm_transactions.to_address, '  # noqa: E501
            'evm_transactions.value, evm_transactions.gas, evm_transactions.gas_price, evm_transactions.gas_used, '  # noqa: E501
            'evm_transactions.input_data, evm_transactions.nonce, evm_transactions.identifier, OP.l1_fee, auth.nonce AS auth_nonce, auth.delegated_address'  # noqa: E501
        )
        join_clause = (
            'LEFT JOIN optimism_transactions AS OP ON evm_transactions.identifier=OP.tx_id '
            'LEFT JOIN evm_transactions_authorizations AS auth ON evm_transactions.identifier = auth.tx_id'  # noqa: E501
        )

        if has_premium:
            sql = f'{base_select} FROM evm_transactions {join_clause} {query}'
        else:
            sql = (
                f'{base_select} FROM (SELECT * FROM evm_transactions ORDER BY timestamp DESC LIMIT ?) AS evm_transactions '  # noqa: E501
                f'{join_clause} {query}'
            )
            bindings = [FREE_ETH_TX_LIMIT] + bindings

        return sql, bindings

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
