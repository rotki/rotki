from typing import Any, ClassVar

from rotkehlchen.chain.arbitrum_one.types import ArbitrumOneTransaction
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransactionAuthorization,
    deserialize_evm_tx_hash,
)


class DBArbitrumOneTx(DBEvmTx):
    # receipt type is included at index 13, shifting auth fields to start at 14
    AUTHORIZATION_DATA_START_INDEX: ClassVar[int] = 14

    def _form_evm_transaction_dbquery(self, query: str, bindings: list[Any]) -> tuple[str, list]:
        """Constructs SQL query and bindings for Arbitrum transactions with receipt type and
        authorization data. Joins evmtx_receipts to include tx_type at index 13 in the result,
        avoiding a separate per-row receipt lookup."""
        base_select = (
            'SELECT evm_transactions.tx_hash, evm_transactions.chain_id, '
            'timestamp, block_number, from_address, to_address, value, evm_transactions.gas, '
            'gas_price, evm_transactions.gas_used, input_data, evm_transactions.nonce, '
            'evm_transactions.identifier, r.type, '
            'auth.nonce AS auth_nonce, auth.delegated_address '
            'FROM evm_transactions '
            'LEFT JOIN evmtx_receipts AS r ON evm_transactions.identifier = r.tx_id '
            'LEFT JOIN evm_transactions_authorizations AS auth '
            'ON evm_transactions.identifier = auth.tx_id '
        )
        return f'{base_select} {query}', bindings

    def _build_evm_transaction(self, result: tuple[Any, ...], authorization_list_result: list[tuple[int, 'ChecksumEvmAddress']]) -> ArbitrumOneTransaction:  # noqa: E501
        """Builds an arbitrum transaction

        May raise:
        - DeserializationError
        """
        tx_hash = deserialize_evm_tx_hash(result[0])
        chain_id = ChainID.deserialize_from_db(result[1])
        if (tx_type := result[13]) is None:
            raise DeserializationError(f'tx receipt for arbitrum one tx {tx_hash!s} does not exist in the database')  # noqa: E501

        return ArbitrumOneTransaction(
            tx_hash=tx_hash,
            chain_id=chain_id,
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
            tx_type=tx_type,
            db_id=result[12],
            authorization_list=None if len(authorization_list_result) == 0 else [
                EvmTransactionAuthorization(nonce=entry[0], delegated_address=entry[1])
                for entry in authorization_list_result
            ],
        )
