from dataclasses import dataclass
from typing import TYPE_CHECKING

from solders.solders import Pubkey, Signature

from rotkehlchen.types import SolanaAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


@dataclass(frozen=True)
class SolanaInstruction:
    """Represent a Solana instruction (top-level or inner/cross-program invocation)"""
    execution_index: int  # sequential order of instruction execution within transaction
    parent_execution_index: int | None  # index of parent instruction (None for top-level instructions)  # noqa: E501
    program_id: SolanaAddress  # address of the program that will execute this instruction
    data: bytes  # instruction data/parameters
    accounts: list[SolanaAddress]  # list of account addresses this instruction will access


@dataclass(frozen=True)
class SolanaTransaction:
    """Represent a Solana transaction"""
    fee: int  # transaction fee paid in lamports (1 SOL = 1 billion lamports)
    slot: int  # solana blockchain slot number where transaction was included
    success: bool  # whether transaction executed successfully (false if any instruction failed)
    signature: Signature  # unique transaction signature (64 bytes, base58 encoded when displayed)
    block_time: Timestamp  # unix timestamp when block containing this transaction was created
    account_keys: list[SolanaAddress]  # all account addresses referenced in transaction
    instructions: list[SolanaInstruction]  # all instructions executed in this transaction
    db_id: int = -1

    def get_or_query_db_id(self, cursor: 'DBCursor') -> int:
        """Returns the DB identifier for the transaction. Assumes it exists in the DB"""
        if self.db_id == -1:
            db_id = cursor.execute(
                'SELECT identifier FROM solana_transactions WHERE signature=?',
                (self.signature.to_bytes(),),
            ).fetchone()[0]
            object.__setattr__(self, 'db_id', db_id)

        return self.db_id


def pubkey_to_solana_address(value: Pubkey) -> SolanaAddress:
    """Convert a public key to SolanaAddress. Only used for typing purposes."""
    return SolanaAddress(str(value))
