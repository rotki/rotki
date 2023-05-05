from typing import TYPE_CHECKING

import pytest

from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.tests.utils.ethereum import (
    TEST_ADDR1,
    TEST_ADDR2,
    setup_ethereum_transactions_test,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('transaction_already_queried', [True, False])
@pytest.mark.freeze_time('2023-01-24 22:45:45 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_transaction_receipt(
        database: 'DBHandler',
        eth_transactions: 'EthereumTransactions',
        transaction_already_queried: bool,
) -> None:
    """Test that getting a transaction receipt from the network and saving it in the DB works"""
    transactions, receipts = setup_ethereum_transactions_test(
        database=database,
        transaction_already_queried=transaction_already_queried,
        one_receipt_in_db=False,
    )
    receipt = eth_transactions.get_or_query_transaction_receipt(transactions[0].tx_hash)
    assert receipt == receipts[0]
    filter_query = EvmTransactionsFilterQuery.make(tx_hash=transactions[0].tx_hash)
    eth_transactions.query_chain(filter_query)
    dbevmtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        results, _ = dbevmtx.get_evm_transactions_and_limit_info(
            cursor=cursor,
            filter_=filter_query,
            has_premium=True,
        )
    assert len(results) == 1
    assert results[0] == transactions[0]
