from typing import TYPE_CHECKING, Final

from solders.pubkey import Pubkey

from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.db.filtering import SolanaTransactionsFilterQuery
from rotkehlchen.types import SolanaAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


# Top-level instructions use -1 as parent_execution_index (instead of NULL)
# to avoid primary key issues with NULL values
TOP_LEVEL_PARENT: Final = -1


class DBSolanaTx:
    """Database handler for Solana transactions"""

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_solana_transactions(
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
                entry=(tx.slot, tx.fee, tx.block_time, int(tx.success), tx.signature),
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
    def get_solana_transactions(
            cursor: 'DBCursor',
            filter_: SolanaTransactionsFilterQuery,
    ) -> list[SolanaTransaction]:
        """Get solana transactions from the database with filtering

        improve the performance of fetching solana transactions
        TODO: https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=130292187
        """
        query, bindings = filter_.prepare()
        query = f'SELECT identifier, signature, slot, block_time, fee, success FROM solana_transactions {query}'  # noqa: E501

        transactions = []
        for result in cursor.execute(query, bindings).fetchall():
            tx_id = result[0]
            account_keys: list[SolanaAddress] = []
            account_keys.extend(SolanaAddress(str(Pubkey.from_bytes(ak_result[0]))) for ak_result in cursor.execute(  # noqa: E501
                'SELECT address FROM solana_tx_account_keys WHERE tx_id=? ORDER BY account_index',
                (tx_id,),
            ))

            # get instructions
            instructions = [SolanaInstruction(
                execution_index=inst_result[1],
                parent_execution_index=None if inst_result[2] == TOP_LEVEL_PARENT else inst_result[2],  # noqa: E501
                program_id=account_keys[inst_result[3]],  # convert index to address
                data=inst_result[4],
                accounts=[account_keys[acc_result[0]] for acc_result in cursor.execute(
                    'SELECT account_index FROM solana_tx_instruction_accounts WHERE instruction_id=? ORDER BY account_order',  # noqa: E501
                    (inst_result[0],),  # instruction identifier
                )],
                ) for inst_result in cursor.execute(
                    'SELECT identifier, execution_index, parent_execution_index, program_id_index, data '  # noqa: E501
                    'FROM solana_tx_instructions WHERE tx_id=? '
                    # Complex ordering ensures top-level instructions come first (ordered by execution_index),  # noqa: E501
                    # followed by sub-instructions grouped under their parent (ordered by parent_execution_index)  # noqa: E501
                    'ORDER BY CASE WHEN parent_execution_index = ? THEN execution_index ELSE parent_execution_index END, '  # noqa: E501
                    'parent_execution_index = ? DESC, execution_index',
                    (tx_id, TOP_LEVEL_PARENT, TOP_LEVEL_PARENT),
            ).fetchall()]

            transactions.append(SolanaTransaction(
                signature=result[1],
                slot=result[2],
                block_time=result[3],
                fee=result[4],
                success=bool(result[5]),
                account_keys=account_keys,
                instructions=instructions,
                db_id=result[0],
            ))

        return transactions
