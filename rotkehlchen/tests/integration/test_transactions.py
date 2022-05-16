import pytest

from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.tests.utils.ethereum import (
    ETHERSCAN_AND_INFURA_PARAMS,
    setup_ethereum_transactions_test,
)


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
    receipt = eth_transactions.get_or_query_transaction_receipt(transactions[0].tx_hash)
    assert receipt == receipts[0]
    results, _ = eth_transactions.query(ETHTransactionsFilterQuery.make(tx_hash=transactions[0].tx_hash), only_cache=True, has_premium=True)  # noqa: E501
    assert len(results) == 1
    assert results[0] == transactions[0]
