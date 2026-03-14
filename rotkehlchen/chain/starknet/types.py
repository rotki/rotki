from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.types import StarknetAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


@dataclass(frozen=True)
class StarknetTransaction:
    """Represent a Starknet transaction"""
    transaction_hash: str  # unique transaction hash
    block_number: int  # block number where transaction was included
    block_timestamp: Timestamp  # unix timestamp when block was created
    from_address: StarknetAddress  # sender address
    to_address: StarknetAddress | None  # receiver address (None for contract deployments)
    selector: str | None  # function selector (for invoke transactions)
    calldata: list[str]  # transaction calldata
    max_fee: int  # maximum fee in wei
    actual_fee: int  # actual fee paid in wei
    status: str  # transaction status (ACCEPTED_ON_L1, ACCEPTED_ON_L2, etc.)
    transaction_type: str  # transaction type (INVOKE, DEPLOY, etc.)
    db_id: int = -1

    def get_or_query_db_id(self, cursor: 'DBCursor') -> int:
        """Returns the DB identifier for the transaction. Assumes it exists in the DB"""
        if self.db_id == -1:
            db_id = cursor.execute(
                'SELECT identifier FROM starknet_transactions WHERE transaction_hash=?',
                (self.transaction_hash,),
            ).fetchone()[0]
            object.__setattr__(self, 'db_id', db_id)

        return self.db_id

    def __str__(self) -> str:
        return self.transaction_hash
