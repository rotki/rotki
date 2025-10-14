from collections import defaultdict
from typing import TYPE_CHECKING, Final

from solders.pubkey import Pubkey
from solders.solders import Signature

from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.dbtx import DBCommonTx
from rotkehlchen.db.filtering import (
    SolanaTransactionsFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.types import SolanaAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


# Top-level instructions use -1 as parent_execution_index (instead of NULL)
# to avoid primary key issues with NULL values
TOP_LEVEL_PARENT: Final = -1


class DBSolanaTx(DBCommonTx[SolanaAddress, SolanaTransaction, Signature, SolanaTransactionsFilterQuery, SolanaTransactionsNotDecodedFilterQuery]):  # noqa: E501
    """Database handler for Solana transactions"""

    def add_transactions(
            self,
            write_cursor: 'DBCursor',
            solana_transactions: list[SolanaTransaction],
            relevant_address: SolanaAddress | None,
    ) -> None:
        """Add solana transactions to the database"""
        query = """INSERT OR IGNORE INTO solana_transactions(slot, fee, block_time, success, signature) VALUES (?, ?, ?, ?, ?)"""  # noqa: E501
        for tx in solana_transactions:
            if (tx_id := self.db.write_single_tuple(
                write_cursor=write_cursor,
                tuple_type='solana_transaction',
                query=query,
                entry=(tx.slot, tx.fee, tx.block_time, int(tx.success), tx.signature.to_bytes()),
                relevant_address=relevant_address,
            )) is None:
                continue

            self.db.write_tuples(
                write_cursor=write_cursor,
                tuple_type='solana_account_key',
                query='INSERT OR IGNORE INTO solana_tx_account_keys(tx_id, account_index, address) VALUES (?, ?, ?)',  # noqa: E501
                tuples=[  # insert account keys
                    (tx_id, account_index, bytes(Pubkey.from_string(address)))
                    for account_index, address in enumerate(tx.account_keys)
                ],
            )
            for instruction in tx.instructions:  # insert instructions
                if (instruction_id := self.db.write_single_tuple(
                    write_cursor=write_cursor,
                    tuple_type='solana_instruction',
                    query='INSERT OR IGNORE INTO solana_tx_instructions(tx_id, execution_index, parent_execution_index, program_id_index, data) VALUES (?, ?, ?, ?, ?)',  # noqa: E501
                    entry=(
                        tx_id,
                        instruction.execution_index,
                        TOP_LEVEL_PARENT if instruction.parent_execution_index is None else instruction.parent_execution_index,  # noqa: E501
                        tx.account_keys.index(instruction.program_id),
                        instruction.data,
                    ),
                    relevant_address=None,
                )) is not None:
                    self.db.write_tuples(
                        write_cursor=write_cursor,
                        tuple_type='solana_instruction_account',
                        query='INSERT OR IGNORE INTO solana_tx_instruction_accounts(instruction_id, account_order, account_index, tx_id) VALUES (?, ?, ?, ?)',  # noqa: E501
                        tuples=[  # insert instruction accounts
                            (instruction_id, order, tx.account_keys.index(account_address), tx_id)
                            for order, account_address in enumerate(instruction.accounts)
                        ],
                    )

    @staticmethod
    def add_token_account_mappings(
            write_cursor: 'DBCursor',
            token_accounts_mappings: dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]],
    ) -> None:
        """Save Solana token account to (owner, mint) mappings in the database cache."""
        token_cache_data = []
        for token_account, owner_mint_data in token_accounts_mappings.items():
            token_cache_data.append((
                DBCacheDynamic.SOLANA_TOKEN_ACCOUNT.get_db_key(address=token_account),
                ','.join(owner_mint_data),
            ))

        write_cursor.executemany(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            token_cache_data,
        )

    @staticmethod
    def get_transactions(
            cursor: 'DBCursor',
            filter_: SolanaTransactionsFilterQuery,
    ) -> list[SolanaTransaction]:
        """Get solana transactions from the database with filtering"""
        query, bindings = filter_.prepare()
        # account keys by tx for fast lookups when building instructions
        ak_by_tx: defaultdict[int, list[SolanaAddress]] = defaultdict(list)
        for tx_id, address_bytes in cursor.execute(
                'SELECT tx_id, address FROM solana_tx_account_keys '
                f'WHERE tx_id IN (SELECT identifier FROM solana_transactions {query}) ORDER BY tx_id, account_index',  # noqa: E501
                bindings,
        ):
            ak_by_tx[tx_id].append(SolanaAddress(str(Pubkey.from_bytes(address_bytes))))

        # split instruction data for easier processing:
        # inst_meta holds core fields, inst_order_by_tx preserves execution order,
        # inst_acc_indices maps instructions to their account references
        inst_meta: dict[int, tuple[int, int | None, int, bytes]] = {}
        inst_order_by_tx: defaultdict[int, list[int]] = defaultdict(list)
        inst_acc_indices: defaultdict[int, list[int]] = defaultdict(list)

        # ordering handles nested instructions: top-level first, then inner by parent
        for (inst_id, tx_id, execution_index, parent_execution_index, program_id_index, inst_data, acc_index) in cursor.execute(  # noqa: E501
                'SELECT i.identifier, i.tx_id, i.execution_index, i.parent_execution_index, i.program_id_index, i.data, ia.account_index '  # noqa: E501
                'FROM solana_tx_instructions i LEFT JOIN solana_tx_instruction_accounts ia ON ia.instruction_id = i.identifier '  # noqa: E501
                f'WHERE i.tx_id IN (SELECT identifier FROM solana_transactions {query}) ORDER BY i.tx_id, '  # noqa: E501
                'CASE WHEN i.parent_execution_index = ? THEN i.execution_index ELSE i.parent_execution_index END, '  # noqa: E501
                '(i.parent_execution_index = ?) DESC, i.execution_index, ia.account_order',
                (*bindings, TOP_LEVEL_PARENT, TOP_LEVEL_PARENT),
        ):  # save instruction data once per instruction
            if inst_id not in inst_meta:
                parent_value = None if parent_execution_index == TOP_LEVEL_PARENT else parent_execution_index  # noqa: E501
                inst_meta[inst_id] = (execution_index, parent_value, program_id_index, inst_data)
                inst_order_by_tx[tx_id].append(inst_id)
            if acc_index is not None:  # each row in the join adds one account reference to this instruction  # noqa: E501
                inst_acc_indices[inst_id].append(acc_index)

        # build final transactions in original order
        transactions: list[SolanaTransaction] = []
        for tx_id, signature, slot, block_time, fee, success_int in cursor.execute(
                f'SELECT identifier, signature, slot, block_time, fee, success FROM solana_transactions {query}',  # noqa: E501
                bindings,
        ):
            account_keys = ak_by_tx[tx_id]
            built_instructions: list[SolanaInstruction] = []
            for inst_id in inst_order_by_tx[tx_id]:
                exec_idx, parent_exec_idx, prog_idx, data = inst_meta[inst_id]
                built_instructions.append(SolanaInstruction(
                    execution_index=exec_idx,
                    parent_execution_index=parent_exec_idx,
                    program_id=account_keys[prog_idx],
                    data=data,
                    accounts=[account_keys[i] for i in inst_acc_indices[inst_id]],  # convert indices to actual addresses  # noqa: E501
                ))

            transactions.append(SolanaTransaction(
                signature=Signature(signature),
                slot=slot,
                block_time=Timestamp(block_time),
                fee=fee,
                success=bool(success_int),
                account_keys=account_keys,
                instructions=built_instructions,
                db_id=tx_id,
            ))

        return transactions

    def deserialize_tx_hash_from_db(self, raw_tx_hash: bytes) -> Signature:
        return Signature(raw_tx_hash)

    def _get_txs_not_decoded_column_and_query(self) -> tuple[str, str]:
        return (
            'signature',
            'solana_transactions AS A LEFT JOIN solana_tx_mappings AS B ON A.identifier = B.tx_id ',  # noqa: E501
        )

    def delete_transaction_data(
            self,
            write_cursor: 'DBCursor',
            signature: Signature | None = None,
    ) -> None:
        """Deletes solana transactions from the DB. If signature is given, only deletes the
        transaction with that signature.
        """
        query = 'DELETE FROM solana_transactions'
        bindings = []
        if signature is not None:
            query += ' WHERE signature = ?'
            bindings.append(signature.to_bytes())

        write_cursor.execute(query, bindings)
