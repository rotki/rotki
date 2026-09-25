from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import ChainID, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('data_migration_version', [27])
def test_migration_28_marks_legacy_zero_fees_unresolved(database: DBHandler) -> None:
    transactions = [
        L2WithL1FeesTransaction(
            tx_hash=make_evm_tx_hash(),
            chain_id=ChainID.OPTIMISM,
            timestamp=Timestamp(1),
            block_number=1,
            from_address=make_evm_address(),
            to_address=None,
            value=0,
            gas=21000,
            gas_price=1,
            gas_used=21000,
            input_data=b'',
            nonce=0,
            l1_fee=fee,
        ) for fee in (0, 123, None)
    ]
    with database.user_write() as write_cursor:
        DBL2WithL1FeesTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=transactions,
            relevant_address=None,
        )

    run_single_migration(database=database, migration=28)

    with database.conn.read_ctx() as cursor:
        for tx, expected_fee in zip(transactions, (None, '123', None), strict=True):
            assert cursor.execute(
                'SELECT fees.l1_fee FROM optimism_transactions AS fees '
                'JOIN evm_transactions AS txs ON txs.identifier=fees.tx_id '
                'WHERE txs.tx_hash=?',
                (tx.tx_hash,),
            ).fetchone() == (expected_fee,)
