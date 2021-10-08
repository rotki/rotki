import pytest

from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.tests.utils.ethereum import (
    ETHERSCAN_AND_INFURA_PARAMS,
    setup_ethereum_transactions_test,
)


@pytest.mark.parametrize(*ETHERSCAN_AND_INFURA_PARAMS)
@pytest.mark.parametrize('transaction_already_queried', [True, False])
def test_get_transaction_receipt(database, ethereum_manager, call_order, transaction_already_queried):  # pylint: disable=unused-argument  # noqa: E501
    """Test that getting a transaction receipt from the network and saving it in the DB works"""
    transactions, receipts = setup_ethereum_transactions_test(
        database=database,
        transaction_already_queried=transaction_already_queried,
        one_receipt_in_db=False,
    )
    tx_hash = '0x' + transactions[0].tx_hash.hex()
    txmodule = EthTransactions(ethereum=ethereum_manager, database=database)
    receipt = txmodule.get_or_query_transaction_receipt(tx_hash)
    assert receipt == receipts[0]
    results, _ = txmodule.query(ETHTransactionsFilterQuery.make(tx_hash=tx_hash), only_cache=True)
    assert len(results) == 1
    assert results[0] == transactions[0]
