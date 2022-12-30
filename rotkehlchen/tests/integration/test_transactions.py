import pytest
from flaky import flaky

from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.tests.utils.ethereum import (
    ETHERSCAN_AND_INFURA_PARAMS,
    setup_ethereum_transactions_test,
)


@flaky(max_runs=3, min_passes=1)  # failed in a flaky way sometimes in the CI due to etherscan
@pytest.mark.parametrize(*ETHERSCAN_AND_INFURA_PARAMS)
@pytest.mark.parametrize('transaction_already_queried', [True, False])
def test_get_transaction_receipt(
        database,
        eth_transactions,
        call_order,  # pylint: disable=unused-argument
        transaction_already_queried,
):
    """Test that getting a transaction receipt from the network and saving it in the DB works"""
    transactions, receipts = setup_ethereum_transactions_test(
        database=database,
        transaction_already_queried=transaction_already_queried,
        one_receipt_in_db=False,
    )
    with database.user_write() as cursor:
        receipt = eth_transactions.get_or_query_transaction_receipt(cursor, transactions[0].tx_hash)  # noqa: E501
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
